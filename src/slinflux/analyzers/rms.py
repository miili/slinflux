import numpy as np

from slinflux.analyzers.base import Analyzer
from slinflux.models.stations import SeedlinkStation


class RMSAnalyzer(Analyzer):
    def analyze(self, station: SeedlinkStation) -> list[str]:
        line_protocol = []
        for channel, trace in station._traces.items():
            rms = np.sqrt(np.abs(trace.data)).mean() ** 2
            line_protocol.append(
                f"seedlink_rms,"
                f"network={station.network},host={station.station},channel={channel}"
                f" counts={rms}"
                f" {station.influx_end_time()}"
            )
        return line_protocol
