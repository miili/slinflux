import asyncio
import logging
from datetime import datetime, timezone
from typing import NoReturn

from pydantic import BaseModel, PrivateAttr

from slinflux.analyzers.base import Analyzer
from slinflux.analyzers.rms import RMSAnalyzer
from slinflux.analyzers.timing import TimingAnalyzer
from slinflux.influx import InfluxDB
from slinflux.seedlink import Seedlink, SeedLinkData

logger = logging.getLogger(__name__)


def get_now_influx() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp() * 1e9)


class SLInflux(BaseModel):
    seedlink_sources: list[Seedlink] = [Seedlink()]
    influx: InfluxDB = InfluxDB()

    analysis_interval: float = 20.0

    _analyzers: list[Analyzer] = [
        RMSAnalyzer(),
        TimingAnalyzer(),
    ]

    _monitor_task: asyncio.Task = PrivateAttr()
    _data_queue: asyncio.Queue[SeedLinkData] = asyncio.Queue()

    async def run(self) -> None:
        # asyncio.create_task(self.monitor_station_seedlink())

        tasks = []
        for seedlink in self.seedlink_sources:
            task = asyncio.create_task(
                seedlink.start(
                    self._data_queue,
                    chunk_length_seconds=self.analysis_interval,
                )
            )
            tasks.append(task)
        logger.info("started %d SeedLink tasks", len(tasks))

        tasks.append(asyncio.create_task(self.monitor_seedlink_delay()))
        logger.info("started SeedLink delay monitor")

        while True:
            station_data = await self._data_queue.get()
            lines = []
            for analyzer in self._analyzers:
                analyzer_result = analyzer.analyze(station_data)
                lines.extend(analyzer_result)

            data = "\n".join(lines)
            logger.info(data)
            await self.influx.write(data)

    async def monitor_seedlink_delay(self) -> NoReturn:
        station_selection = [
            station
            for seedlink in self.seedlink_sources
            for station in seedlink.station_selection
        ]

        while True:
            await asyncio.sleep(self.analysis_interval)

            line_protocol = []
            for station in station_selection:
                delay = datetime.now(tz=timezone.utc) - station.last_data
                line = (
                    f"seedlink_delay,"
                    f"network={station.network},host={station.station}"
                    f" delay={delay.total_seconds()},lat={station.lat},lon={station.lon}"
                    f" {get_now_influx()}"
                )
                line_protocol.append(line)

            data = "\n".join(line_protocol)
            logger.info(data)
            await self.influx.write(data)
