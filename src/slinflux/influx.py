import aiohttp
from pydantic import BaseModel


class InfluxDB(BaseModel):
    host: str = "localhost"
    port: int = 8086

    username: str = ""
    password: str = ""

    database: str = "telegraf"

    async def write(self, data: str):
        url = f"http://{self.host}:{self.port}/write?db={self.database}"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=data,
            ) as response:
                response.raise_for_status()
