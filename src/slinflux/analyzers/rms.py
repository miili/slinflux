import numpy as np

from slinflux.analyzers.base import Analyzer
from slinflux.models.stations import SeedLinkData, StationSelection


class RMSAnalyzer(Analyzer):
    def analyze(self, station: StationSelection, data: SeedLinkData) -> list[str]:
        line_protocol = []
        for channel, trace in data._traces.items():
            rms_counts = np.sqrt(np.abs(trace.data)).mean() ** 2
            peak_counts = np.abs(trace.data).max()

            rms_velocity = rms_counts / station.amplification
            peak_velocity = peak_counts / station.amplification

            line_protocol.append(
                f"seedlink_rms,"
                f"network={data.network},host={data.station},channel={channel}"
                f" counts={rms_counts},peak={peak_counts},"
                f"rms_velocity={rms_velocity},peak_velocity={peak_velocity}"
                f" {data.influx_end_time()}"
            )
        return line_protocol
