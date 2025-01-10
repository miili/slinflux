from slinflux.analyzers.base import Analyzer
from slinflux.models.stations import SeedLinkData


class TimingAnalyzer(Analyzer):
    def analyze(self, data: SeedLinkData) -> list[str]:
        timing_quality = max([data.get_timing_quality(cha) for cha in data.channels])

        return [
            f"seedlink_timing_quality,network={data.network},host={data.station} "
            f"timing_quality={timing_quality} {data.influx_end_time()}"
        ]
