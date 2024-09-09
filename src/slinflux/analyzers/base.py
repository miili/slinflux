from slinflux.models.stations import SeedlinkData


class Analyzer:
    def analyze(self, station: SeedlinkData) -> str:
        raise NotImplementedError
