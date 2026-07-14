from __future__ import annotations

from pathlib import Path

import pytest

from repolens.extractors import ExtractionResult, ExtractorRegistry


class FakeExtractor:
    def __init__(self, *extensions: str) -> None:
        self._extensions = frozenset(extensions)

    @property
    def extensions(self) -> frozenset[str]:
        return self._extensions

    def extract(self, path: Path, source: str) -> ExtractionResult:
        return ExtractionResult(diagnostics=(f"{path}:{len(source)}",))


def test_extractor_registry_behavior() -> None:
    registry = ExtractorRegistry()
    extractor = FakeExtractor("PY", ".pyi")
    registry.register(extractor)

    assert registry.for_path(Path("service.PY")) is extractor
    assert registry.for_path(Path("types.pyi")) is extractor
    assert registry.for_path(Path("README.md")) is None
    assert registry.extensions == (".py", ".pyi")


def test_extractor_registry_rejects_conflicts() -> None:
    registry = ExtractorRegistry()
    registry.register(FakeExtractor(".py"))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeExtractor("py"))


def test_extractor_registry_rejects_empty_extensions() -> None:
    with pytest.raises(ValueError, match="at least one"):
        ExtractorRegistry().register(FakeExtractor())
