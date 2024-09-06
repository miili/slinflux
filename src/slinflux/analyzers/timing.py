from slinflux.analyzers.base import Analyzer
from slinflux.models.stations import SeedlinkStation


class TimingAnalyzer(Analyzer):
    def analyze(self, station: SeedlinkStation) -> list[str]:
        timing_quality = max(
            [station.get_timing_quality(cha) for cha in station.channels]
        )

        return [
            f"seedlink_timing_quality,network={station.network},host={station.station} "
            f"timing_quality={timing_quality} {station.influx_end_time()}"
        ]
