from slinflux.models.stations import SeedLinkData, StationSelection


class Analyzer:
    def analyze(self, station: StationSelection, data: SeedLinkData) -> str:
        raise NotImplementedError
