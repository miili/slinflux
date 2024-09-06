import asyncio
import logging
import subprocess
from collections.abc import AsyncGenerator
from datetime import timedelta
from io import BytesIO
from typing import TYPE_CHECKING

from obspy import read
from pydantic import BaseModel, PositiveInt

from slinflux.models.stations import SeedlinkStation, SeedlinkStream

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
RECORD_LENGTH = 512


def call_slinktool(cmd_args: list[str]) -> bytes:
    cmd = ["slinktool", *cmd_args]
    logger.debug(f"Running command: {cmd}")
    proc = subprocess.run(cmd, capture_output=True)
    proc.check_returncode()
    return proc.stdout


class Seedlink(BaseModel):
    host: str = "127.0.0.1"
    port: PositiveInt = 18000

    station_selection: list[str] = ["1D_SYRAU"]

    stations: dict[tuple[str, str, str], SeedlinkStation] = {}

    @property
    def _slink_host(self) -> str:
        return f"{self.host}:{self.port}"

    def list_stations(self) -> list[SeedlinkStream]:
        logger.info("requesting station list")
        ret = call_slinktool(["-Q", self._slink_host])

        return [SeedlinkStream.from_line(line.decode()) for line in ret.splitlines()]

    def get_station(self, network: str, station: str, location: str) -> SeedlinkStation:
        key = (network, station, location)
        if key not in self.stations:
            self.stations[key] = SeedlinkStation(
                network=network,
                station=station,
                location=location,
            )

        return self.stations[key]

    async def iter_streams(
        self, length: float = 20.0
    ) -> AsyncGenerator[SeedlinkStation]:
        selector = ",".join(self.station_selection)

        logger.info(f"streaming: {selector}")
        proc = await asyncio.subprocess.create_subprocess_exec(
            "slinktool",
            "-o",
            "-",
            "-S",
            selector,
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

                station = self.get_station(stats.network, stats.station, stats.location)
                station.add_trace(trace, mseed=data)

                try:
                    st = station.get_tail(length=timedelta(seconds=length))
                    print(st)
                    yield st
                except ValueError:
                    continue
        except asyncio.CancelledError:
            proc.terminate()
            raise

    # async def iter_stream(self) -> AsyncGenerator[Stream]: ...
