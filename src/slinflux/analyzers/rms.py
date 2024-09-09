import numpy as np

from slinflux.analyzers.base import Analyzer
from slinflux.models.stations import SeedlinkData


class RMSAnalyzer(Analyzer):
    def analyze(self, station: SeedlinkData) -> list[str]:
        line_protocol = []
        for channel, trace in station._traces.items():
            rms = np.sqrt(np.abs(trace.data)).mean() ** 2
            peak = np.abs(trace.data).max()
            line_protocol.append(
                f"seedlink_rms,"
                f"network={station.network},host={station.station},channel={channel}"
                f" counts={rms},peak={peak}"
                f" {station.influx_end_time()}"
            )
        return line_protocol
