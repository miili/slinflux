from __future__ import annotations

from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile
from typing import Any

from obspy import Trace, UTCDateTime
from obspy.io.mseed.util import get_flags
from pydantic import BaseModel, PrivateAttr


class SeedlinkStream(BaseModel):
    network: str
    station: str
    location: str
    channel: str
    dataquality: str

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
            dataquality=line[16],
            starttime=datetime.strptime(line[18:42], "%Y/%m/%d %H:%M:%S.%f"),
            endtime=datetime.strptime(line[47:71], "%Y/%m/%d %H:%M:%S.%f"),
        )


class SeedlinkStation(BaseModel):
    network: str
    station: str
    location: str

    _traces: dict[str, Trace] = PrivateAttr(default_factory=dict)
    _mseed_bytes: dict[str, bytes] = PrivateAttr(default_factory=dict)

    def add_trace(self, trace: Trace, mseed: bytes):
        channel = trace.stats.channel

        if channel not in self._traces:
            self._traces[channel] = trace
            return

        merged_traces = self._traces[channel].__add__(trace, fill_value=0.0)
        self._traces[channel] = merged_traces
        self._mseed_bytes[channel] = mseed

    @property
    def start_time(self) -> datetime:
        return max([trace.stats.starttime.datetime for trace in self._traces.values()])

    @property
    def end_time(self) -> datetime:
        return min([trace.stats.endtime.datetime for trace in self._traces.values()])

    @property
    def length(self) -> timedelta:
        return self.end_time - self.start_time

    @property
    def channels(self) -> tuple:
        return tuple(self._traces.keys())

    def get_tail(self, length: timedelta) -> SeedlinkStation:
        if self.length < length:
            raise ValueError("Requested length is longer than available data")

        tail = self.model_copy(deep=True)
        start_time = UTCDateTime(self.start_time)
        for channel in tail._traces.keys():
            tail._traces[channel] = tail._traces[channel].slice(
                starttime=start_time,
                endtime=start_time + length,
            )
            self._traces[channel].trim(starttime=start_time + length)
        return tail

    def _get_flags(self, channel: str) -> dict[Any, Any]:
        data = self._mseed_bytes[channel]
        with NamedTemporaryFile() as f:
            f.write(data)
            f.seek(0)
            return get_flags(
                f,
                io_flags=False,
                activity_flags=False,
                data_quality_flags=False,
                timing_quality=True,
            )

    def get_timing_quality(self, channel: str) -> float:
        return float(self._get_flags(channel)["timing_quality"]["max"])

    def influx_end_time(self) -> int:
        return int(self.end_time.timestamp() * 1e9)
