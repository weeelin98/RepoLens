"""Extractor interfaces and implemented language adapters."""

from repolens.extractors.base import (
    ExtractionResult,
    Extractor,
    ImportFactKind,
    UnresolvedImportFact,
)
from repolens.extractors.python import PythonExtractor
from repolens.extractors.registry import ExtractorRegistry

__all__ = [
    "ExtractionResult",
    "Extractor",
    "ExtractorRegistry",
    "ImportFactKind",
    "PythonExtractor",
    "UnresolvedImportFact",
]
