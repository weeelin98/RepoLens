"""Extractor interfaces and implemented language adapters."""

from repolens.extractors.base import (
    ExtractionResult,
    Extractor,
    ImportFactKind,
    MarkdownFactKind,
    MetadataEcosystem,
    ProjectMetadataFact,
    UnresolvedImportFact,
    UnresolvedMarkdownFact,
)
from repolens.extractors.markdown import MarkdownExtractor
from repolens.extractors.metadata import ProjectMetadataExtractor
from repolens.extractors.python import PythonExtractor
from repolens.extractors.registry import ExtractorRegistry

__all__ = [
    "ExtractionResult",
    "Extractor",
    "ExtractorRegistry",
    "ImportFactKind",
    "MarkdownExtractor",
    "MarkdownFactKind",
    "MetadataEcosystem",
    "ProjectMetadataExtractor",
    "ProjectMetadataFact",
    "PythonExtractor",
    "UnresolvedImportFact",
    "UnresolvedMarkdownFact",
]
