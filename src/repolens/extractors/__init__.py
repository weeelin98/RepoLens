"""Extractor interfaces and implemented language adapters."""

from repolens.extractors.base import (
    EsmExportKind,
    EsmImportKind,
    ExtractionResult,
    Extractor,
    ImportFactKind,
    MarkdownFactKind,
    MetadataEcosystem,
    ProjectMetadataFact,
    UnresolvedEsmExportFact,
    UnresolvedEsmImportFact,
    UnresolvedImportFact,
    UnresolvedMarkdownFact,
)
from repolens.extractors.javascript_typescript import JavaScriptTypeScriptExtractor
from repolens.extractors.markdown import MarkdownExtractor
from repolens.extractors.metadata import ProjectMetadataExtractor
from repolens.extractors.python import PythonExtractor
from repolens.extractors.registry import ExtractorRegistry

__all__ = [
    "EsmExportKind",
    "EsmImportKind",
    "ExtractionResult",
    "Extractor",
    "ExtractorRegistry",
    "ImportFactKind",
    "JavaScriptTypeScriptExtractor",
    "MarkdownExtractor",
    "MarkdownFactKind",
    "MetadataEcosystem",
    "ProjectMetadataExtractor",
    "ProjectMetadataFact",
    "PythonExtractor",
    "UnresolvedEsmExportFact",
    "UnresolvedEsmImportFact",
    "UnresolvedImportFact",
    "UnresolvedMarkdownFact",
]
