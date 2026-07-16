"""Repository discovery contracts for Milestone 1.1.

The developer-owned traversal and resource-limit behavior is intentionally unfinished.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path, PureWindowsPath

from pydantic import BaseModel, ConfigDict, Field, field_validator

from repolens.config import RuntimeConfig
from repolens.ids import normalize_repo_path

DEFAULT_IGNORED_DIRECTORIES = frozenset({".git", ".venv", "venv", "__pycache__"})
DEFAULT_SUPPORTED_SUFFIXES = frozenset({".md", ".py"})


class ScanDiagnosticCode(StrEnum):
    """Stable machine-readable reasons for an incomplete or rejected scan."""

    REPOSITORY_NOT_FOUND = "repository_not_found"
    REPOSITORY_NOT_DIRECTORY = "repository_not_directory"
    FILE_TOO_LARGE = "file_too_large"
    FILE_COUNT_LIMIT_REACHED = "file_count_limit_reached"
    REPOSITORY_SIZE_LIMIT_REACHED = "repository_size_limit_reached"
    OUTSIDE_REPOSITORY_SYMLINK = "outside_repository_symlink"
    STAT_FAILED = "stat_failed"
    PERMISSION_DENIED = "permission_denied"


class SourceFile(BaseModel):
    """Serializable metadata for one eligible repository file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str = Field(min_length=1)
    suffix: str = Field(min_length=2)
    size_bytes: int = Field(ge=0)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        if PureWindowsPath(value).is_absolute():
            raise ValueError("source file path must be repository-relative")
        normalized = normalize_repo_path(value)
        if normalized == ".":
            raise ValueError("source file path must name a file")
        return normalized

    @field_validator("suffix")
    @classmethod
    def normalize_suffix(cls, value: str) -> str:
        normalized = value.casefold()
        if not normalized.startswith("."):
            raise ValueError("suffix must start with '.'")
        return normalized


class ScanDiagnostic(BaseModel):
    """Stable diagnostic without machine-specific exception or absolute-path text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str | None = None
    code: ScanDiagnosticCode
    message: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if PureWindowsPath(value).is_absolute():
            raise ValueError("diagnostic path must be repository-relative")
        return normalize_repo_path(value)


class ScanResult(BaseModel):
    """Deterministic repository metadata and explicit partial-result diagnostics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    files: tuple[SourceFile, ...] = ()
    diagnostics: tuple[ScanDiagnostic, ...] = ()
    total_bytes: int = Field(default=0, ge=0)


def scan_repository(
    repository_root: Path,
    config: RuntimeConfig,
    *,
    supported_suffixes: frozenset[str] = DEFAULT_SUPPORTED_SUFFIXES,
) -> ScanResult:
    """Discover bounded source-file metadata without reading or parsing contents."""

    raise NotImplementedError("Milestone 1.1 repository scanner is developer-owned")
