import asyncio
import logging
import subprocess
from collections.abc import AsyncGenerator
from datetime import timedelta
from io import BytesIO
from typing import TYPE_CHECKING

from obspy import read
from pydantic import BaseModel, PositiveInt, PrivateAttr

from slinflux.models.stations import SeedlinkData, SeedlinkStream, StationSelection

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
RECORD_LENGTH = 512
BLACKLISTED_CHANNELS = ("LOG",)


def call_slinktool(cmd_args: list[str]) -> bytes:
    cmd = ["slinktool", *cmd_args]
    logger.debug(f"Running command: {cmd}")
    proc = subprocess.run(cmd, capture_output=True)
    proc.check_returncode()
    return proc.stdout


class Seedlink(BaseModel):
    host: str = "geofon.gfz-potsdam.de"
    port: PositiveInt = 18000

    _stations: dict[tuple[str, str, str], SeedlinkData] = PrivateAttr(
        default_factory=dict
    )

    @property
    def _slink_host(self) -> str:
        return f"{self.host}:{self.port}"

    def list_stations(self) -> list[SeedlinkStream]:
        logger.info("requesting station list")
        ret = call_slinktool(["-Q", self._slink_host])

        return [SeedlinkStream.from_line(line.decode()) for line in ret.splitlines()]

    def get_station(self, network: str, station: str, location: str) -> SeedlinkData:
        key = (network, station, location)
        if key not in self._stations:
            self._stations[key] = SeedlinkData(
                network=network,
                station=station,
                location=location,
            )

        return self._stations[key]

    async def iter_streams(
        self,
        stations: list[StationSelection],
        chunk_length: float = 20.0,
    ) -> AsyncGenerator[SeedlinkData]:
        selectors = ",".join(sta.seedlink_str() for sta in stations)

        logger.info(f"streaming: {selectors}")
        proc = await asyncio.subprocess.create_subprocess_exec(
            "slinktool",
            "-o",
            "-",
            "-S",
            selectors,
            self._slink_host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            while True:
                logger.debug("waiting for data")
                data = await proc.stdout.read(RECORD_LENGTH)
                trace_data = BytesIO(data)
                st = read(trace_data, format="mseed")

                if len(st) != 1:
                    raise ValueError(f"Expected 1 trace, got {len(st)}")

                trace = st[0]
                stats = trace.stats
                if stats.channel in BLACKLISTED_CHANNELS:
                    continue

                station = self.get_station(stats.network, stats.station, stats.location)
                station.add_trace(trace, mseed=data)

                try:
                    st = station.get_tail(length=timedelta(seconds=chunk_length))
                    print(st)
                    yield st
                except ValueError:
                    continue
        except asyncio.CancelledError:
            proc.terminate()
            raise

    # async def iter_stream(self) -> AsyncGenerator[Stream]: ...
