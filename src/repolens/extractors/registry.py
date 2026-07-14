"""Deterministic extension-to-extractor registration."""

from __future__ import annotations

from pathlib import Path

from repolens.extractors.base import Extractor


def _normalize_extension(extension: str) -> str:
    extension = extension.strip().lower()
    if not extension:
        raise ValueError("extractor extensions cannot be empty")
    return extension if extension.startswith(".") else f".{extension}"


class ExtractorRegistry:
    def __init__(self) -> None:
        self._by_extension: dict[str, Extractor] = {}

    def register(self, extractor: Extractor) -> None:
        extensions = sorted(_normalize_extension(item) for item in extractor.extensions)
        if not extensions:
            raise ValueError("an extractor must declare at least one extension")
        conflicts = [item for item in extensions if item in self._by_extension]
        if conflicts:
            raise ValueError(f"extractor extensions already registered: {', '.join(conflicts)}")
        for extension in extensions:
            self._by_extension[extension] = extractor

    def for_path(self, path: Path) -> Extractor | None:
        return self._by_extension.get(path.suffix.lower())

    @property
    def extensions(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_extension))
