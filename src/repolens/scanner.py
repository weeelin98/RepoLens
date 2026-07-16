"""Repository discovery contracts and basic deterministic traversal."""

from __future__ import annotations

import os
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
    """Discover source-file metadata without reading or parsing contents."""

    if not repository_root.exists():
        diagnostic = ScanDiagnostic(
            code=ScanDiagnosticCode.REPOSITORY_NOT_FOUND,
            message="repository root does not exist",
        )
        return ScanResult(diagnostics=(diagnostic,))

    if not repository_root.is_dir():
        diagnostic = ScanDiagnostic(
            code=ScanDiagnosticCode.REPOSITORY_NOT_DIRECTORY,
            message="repository root is not a directory",
        )
        return ScanResult(diagnostics=(diagnostic,))

    resolved_root = repository_root.resolve()
    normalized_suffixes = frozenset(
        suffix.casefold() if suffix.startswith(".") else f".{suffix.casefold()}"
        for suffix in supported_suffixes
    )
    files: list[SourceFile] = []
    total_bytes = 0

    for current_directory, dirnames, filenames in os.walk(
        resolved_root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current_directory)
        dirnames[:] = sorted(
            dirname
            for dirname in dirnames
            if dirname not in DEFAULT_IGNORED_DIRECTORIES
            and not (current_path / dirname).is_symlink()
        )

        for filename in sorted(filenames):
            path = current_path / filename
            suffix = path.suffix.casefold()
            if suffix not in normalized_suffixes:
                continue

            size_bytes = path.stat().st_size
            files.append(
                SourceFile(
                    relative_path=path.relative_to(resolved_root).as_posix(),
                    suffix=suffix,
                    size_bytes=size_bytes,
                )
            )
            total_bytes += size_bytes

    return ScanResult(
        files=tuple(sorted(files, key=lambda source_file: source_file.relative_path)),
        total_bytes=total_bytes,
    )
