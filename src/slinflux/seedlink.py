import asyncio
import logging
import subprocess
from collections.abc import AsyncGenerator
from datetime import timedelta
from io import BytesIO
from typing import TYPE_CHECKING

from obspy import read
from pydantic import BaseModel, PositiveInt, PrivateAttr

from slinflux.models.stations import SeedLinkData, SeedlinkStream, StationSelection

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

    station_selection: list[StationSelection] = [
        StationSelection(network="1D", station="SYRAU", lat=50.45693, lon=12.083366),
        StationSelection(network="1D", station="WBERG", lat=50.364212, lon=11.999245),
    ]

    _station_data: dict[tuple[str, str, str], SeedLinkData] = PrivateAttr(
        default_factory=dict
    )

    @property
    def _slink_host(self) -> str:
        return f"{self.host}:{self.port}"

    def list_stations(self) -> list[SeedlinkStream]:
        logger.info("requesting station list")
        ret = call_slinktool(["-Q", self._slink_host])

        return [SeedlinkStream.from_line(line.decode()) for line in ret.splitlines()]

    def get_station(
        self, network: str, station: str, location: str
    ) -> StationSelection:
        key = (network, station, location)
        for sta in self.station_selection:
            if key == sta.nsl():
                return sta
        raise KeyError("Cannot find station selection %s", ".".join(key))

    def get_station_data(
        self, network: str, station: str, location: str
    ) -> SeedLinkData:
        key = (network, station, location)
        if key not in self._station_data:
            self._station_data[key] = SeedLinkData(station_meta=self.get_station(*key))
        return self._station_data[key]

    async def start(
        self,
        queue: asyncio.Queue,
        chunk_length_seconds: float = 20.0,
    ) -> AsyncGenerator[SeedLinkData]:
        selectors = ",".join(sta.seedlink_str() for sta in self.station_selection)

        logger.info("streaming stations %s from %s", selectors, self._slink_host)
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

                try:
                    station_data = self.get_station_data(
                        stats.network, stats.station, stats.location
                    )
                except KeyError:
                    logger.error(
                        "Cannot get station %s.%s.%s",
                        stats.network,
                        stats.station,
                        stats.location,
                    )
                station_data.add_trace(trace, mseed=data)
                station_data.station_meta.set_last_seen(station_data.end_time)

                try:
                    st = station_data.get_tail(
                        length=timedelta(seconds=chunk_length_seconds)
                    )
                    logger.info("New stream: %s", st)
                    await queue.put(st)
                except ValueError:
                    continue
        except asyncio.CancelledError:
            proc.terminate()
            raise

    # async def iter_stream(self) -> AsyncGenerator[Stream]: ...
