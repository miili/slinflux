from pydantic import BaseModel

from slinflux.analyzers.base import Analyzer
from slinflux.analyzers.rms import RMSAnalyzer
from slinflux.analyzers.timing import TimingAnalyzer
from slinflux.influx import InfluxDB
from slinflux.seedlink import Seedlink


class SLInflux(BaseModel):
    seedlink: Seedlink = Seedlink()
    influx: InfluxDB = InfluxDB()

    analysis_interval: float = 20.0

    _analyzers: list[Analyzer] = [
        RMSAnalyzer(),
        TimingAnalyzer(),
    ]

    async def run(self):
        async for station in self.seedlink.iter_streams(self.analysis_interval):
            lines = []
            for analyzer in self._analyzers:
                analyzer_out = analyzer.analyze(station)
                lines.extend(analyzer_out)

            data = "\n".join(lines)
            print(data)
            await self.influx.write(data)
