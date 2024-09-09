import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel

from slinflux.analyzers.base import Analyzer
from slinflux.analyzers.rms import RMSAnalyzer
from slinflux.analyzers.timing import TimingAnalyzer
from slinflux.influx import InfluxDB
from slinflux.models.stations import StationSelection
from slinflux.seedlink import Seedlink

logger = logging.getLogger(__name__)


def get_now_influx() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp() * 1e9)


class SLInflux(BaseModel):
    station_selection: list[StationSelection] = [
        StationSelection(network="1D", station="SYRAU", lat=50.45693, lon=12.083366),
        StationSelection(network="1D", station="WBERG", lat=50.364212, lon=11.999245),
    ]
    seedlink: Seedlink = Seedlink()
    influx: InfluxDB = InfluxDB()

    analysis_interval: float = 20.0

    _analyzers: list[Analyzer] = [
        RMSAnalyzer(),
        TimingAnalyzer(),
    ]

    _monitor_task: asyncio.Task

    async def run(self):
        asyncio.create_task(self.monitor_station_seedlink())

        async for station in self.seedlink.iter_streams(
            stations=self.station_selection,
            chunk_length=self.analysis_interval,
        ):
            lines = []
            for analyzer in self._analyzers:
                analyzer_out = analyzer.analyze(station)
                lines.extend(analyzer_out)

            data = "\n".join(lines)
            print(data)
            await self.influx.write(data)

    async def monitor_station_seedlink(self):
        logger.info("Starting Monitoring SeedLink delay task")
        while True:
            await asyncio.sleep(self.analysis_interval)

            line_protocol = []
            for station in self.station_selection:
                try:
                    seedlink_data = self.seedlink.get_station(
                        station.network, station.station, station.location
                    )
                    delay = datetime.now(tz=timezone.utc) - seedlink_data.end_time
                except KeyError:
                    delay = timedelta(days=365)

                line = (
                    f"seedlink_delay,"
                    f"network={station.network},host={station.station}"
                    f" delay={delay.total_seconds()},lat={station.lat},lon={station.lon}"
                    f" {get_now_influx()}"
                )
                line_protocol.append(line)

            data = "\n".join(line_protocol)
            print(data)
            await self.influx.write(data)
