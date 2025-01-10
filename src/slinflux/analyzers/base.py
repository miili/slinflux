from typing import TYPE_CHECKING

from slinflux.models.stations import SeedLinkData

if TYPE_CHECKING:
    pass


class Analyzer:
    def analyze(self, data: SeedLinkData) -> str:
        raise NotImplementedError
