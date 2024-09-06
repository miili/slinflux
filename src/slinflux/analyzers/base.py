from slinflux.models.stations import SeedlinkStation


class Analyzer:
    def analyze(self, station: SeedlinkStation) -> str:
        raise NotImplementedError
