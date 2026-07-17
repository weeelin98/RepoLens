"""Deterministic extension-to-extractor registration."""

from __future__ import annotations

from pathlib import Path

from repolens.extractors.base import Extractor


def _normalize_extension(extension: str) -> str:
    extension = extension.strip().lower()
    if not extension:
        raise ValueError("extractor extensions cannot be empty")
    return extension if extension.startswith(".") else f".{extension}"


def _validate_filename(filename: str) -> str:
    filename = filename.strip()
    if not filename:
        raise ValueError("extractor filenames cannot be empty")
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValueError("extractor filenames must be basenames")
    return filename


class ExtractorRegistry:
    def __init__(self) -> None:
        self._by_extension: dict[str, Extractor] = {}
        self._by_filename: dict[str, Extractor] = {}

    def register(self, extractor: Extractor) -> None:
        extensions = sorted(_normalize_extension(item) for item in extractor.extensions)
        filenames = sorted(_validate_filename(item) for item in extractor.filenames)
        if not extensions and not filenames:
            raise ValueError("an extractor must declare at least one extension or filename")
        extension_conflicts = [item for item in extensions if item in self._by_extension]
        if extension_conflicts:
            raise ValueError(
                f"extractor extensions already registered: {', '.join(extension_conflicts)}"
            )
        filename_conflicts = [item for item in filenames if item in self._by_filename]
        if filename_conflicts:
            raise ValueError(
                f"extractor filenames already registered: {', '.join(filename_conflicts)}"
            )
        for extension in extensions:
            self._by_extension[extension] = extractor
        for filename in filenames:
            self._by_filename[filename] = extractor

    def for_path(self, path: Path) -> Extractor | None:
        return self._by_filename.get(path.name) or self._by_extension.get(path.suffix.lower())

    @property
    def extensions(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_extension))

    @property
    def filenames(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_filename))
