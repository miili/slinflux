import asyncio
import logging
from pathlib import Path

import typer
from rich import print_json
from rich.logging import RichHandler

from slinflux.slinflux import SLInflux

app = typer.Typer()


FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO, format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)


@app.command()
def init() -> None:
    """Print the default configuration."""
    sl = SLInflux()
    print_json(sl.model_dump_json(indent=2))


@app.command()
def config() -> None:
    sl = SLInflux()


@app.command()
def run(config_file: Path) -> None:
    """Run the SeedLink Influx."""
    sl = SLInflux.model_validate_json(config_file.read_text())
    asyncio.run(sl.run())


def main() -> None:
    app()
