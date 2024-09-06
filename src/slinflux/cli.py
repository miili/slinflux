import asyncio
import logging
from pathlib import Path

import typer
from rich import print_json

from slinflux.slininflux import SLInflux

app = typer.Typer()


logging.basicConfig(level=logging.INFO)


@app.command()
def config() -> None:
    """Print the default configuration."""
    sl = SLInflux()
    print_json(sl.model_dump_json(indent=2))


@app.command()
def run(config_file: Path) -> None:
    """Run the SeedLink analysis."""
    sl = SLInflux.model_validate_json(config_file.read_text())
    asyncio.run(sl.run())


def main() -> None:
    app()
