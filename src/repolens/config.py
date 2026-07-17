"""Runtime configuration and logging foundations."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

PROJECT_METADATA_FILENAMES = frozenset({"package.json", "pyproject.toml", "tsconfig.json"})


class RuntimeConfig(BaseModel):
    """Safe local defaults; scanner enforcement begins in Milestone 1."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    output_directory: Path = Path("repolens-out")
    maximum_file_bytes: int = Field(default=1_000_000, gt=0)
    maximum_repository_bytes: int = Field(default=100_000_000, gt=0)
    maximum_file_count: int = Field(default=25_000, gt=0)
    overview_token_budget: int = Field(default=8_000, gt=0)


def configure_logging(*, verbose: bool = False) -> None:
    """Install a compact deterministic log format for CLI applications."""

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
