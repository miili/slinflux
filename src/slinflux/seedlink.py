import asyncio
import logging
import subprocess
from io import BytesIO
from typing import TYPE_CHECKING, AsyncGenerator

from obspy import read
from pydantic import BaseModel, PositiveInt

from slinflux.models.stations import SeedlinkStream

if TYPE_CHECKING:
    from obspy import Stream

logger = logging.getLogger(__name__)
RECORD_LENGTH = 512


def call_slinktool(cmd_args: list[str]) -> bytes:
    cmd = ["slinktool", *cmd_args]
    logger.debug(f"Running command: {cmd}")
    proc = subprocess.run(cmd, capture_output=True)
    proc.check_returncode()
    return proc.stdout


class Seedlink(BaseModel):
    host: str = "127.0.0.1"
    port: PositiveInt = 18000

    stations: list[str] = ["2D_BEMS", "2D_DREA"]

    @property
    def _slink_host(self) -> str:
        return f"{self.host}:{self.port}"

    def list_stations(self) -> list[SeedlinkStream]:
        logger.info("requesting station list")
        ret = call_slinktool(["-Q", self._slink_host])

        return [SeedlinkStream.from_line(line.decode()) for line in ret.splitlines()]

    async def stream(self):
        selector = ",".join(self.stations)

        logger.info(f"streaming: {selector}")
        proc = await asyncio.subprocess.create_subprocess_exec(
            "slinktool",
            "-o",
            "-",
            "-S",
            selector,
            self._slink_host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        while True:
            print("waiting for data")
            data = await proc.stdout.read(RECORD_LENGTH)
            trace_data = BytesIO(data)
            st = read(trace_data, format="mseed")
            print(st)
            for tr in st:
                print(tr.stats.mseed)

    async def iter_stream(self) -> AsyncGenerator[Stream]: ...
