import asyncio

import pytest

from slinflux.models.stations import SeedlinkStream
from slinflux.seedlink import Seedlink


def test_station_list():
    sl = Seedlink(host="geofon.gfz-potsdam.de")
    ret = sl.list_stations()
    print(ret)
    assert ret


def test_station():
    return
    line = "1D SYRAU    HHE D 2024/09/04 08:55:30.5050  -  2024/09/04 14:31:54.6000"
    sls = SeedlinkStream.from_line(line)
    print(sls)


def test_stream():
    sl = Seedlink(host="geofon.gfz-potsdam.de")
    asyncio.run(sl.stream())


@pytest.mark.asyncio
async def test_stream_traces():
    sl = Seedlink(host="geofon.gfz-potsdam.de")
    async for st in sl.iter_stream():
        print(st)
        assert st
