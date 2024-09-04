from datetime import datetime

from pydantic import BaseModel


class SeedlinkStream(BaseModel):
    network: str
    station: str
    location: str
    channel: str

    starttime: datetime
    endtime: datetime

    @classmethod
    def from_line(cls, line: str):
        # ZB VOSXX 00 HHZ D 2021/10/08 04:20:36.4200  -  2021/10/08 11:31:00.220
        return cls(
            network=line[0:2].strip(),
            station=line[3:8].strip(),
            location=line[9:12].strip(),
            channel=line[12:15].strip(),
            starttime=datetime.strptime(line[18:42], "%Y/%m/%d %H:%M:%S.%f"),
            endtime=datetime.strptime(line[47:71], "%Y/%m/%d %H:%M:%S.%f"),
        )
