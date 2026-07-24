"""Extractor interfaces and implemented language adapters."""

from repolens.extractors.base import (
    CommonJsExportKind,
    CommonJsRequireKind,
    EsmExportKind,
    EsmImportKind,
    EsmReExportKind,
    ExtractionResult,
    Extractor,
    ImportFactKind,
    JavaScriptCallKind,
    MarkdownFactKind,
    MetadataEcosystem,
    ProjectMetadataFact,
    UnresolvedCommonJsExportFact,
    UnresolvedCommonJsRequireFact,
    UnresolvedEsmExportFact,
    UnresolvedEsmImportFact,
    UnresolvedEsmReExportFact,
    UnresolvedImportFact,
    UnresolvedJavaScriptCallFact,
    UnresolvedMarkdownFact,
)
from repolens.extractors.javascript_typescript import JavaScriptTypeScriptExtractor
from repolens.extractors.markdown import MarkdownExtractor
from repolens.extractors.metadata import ProjectMetadataExtractor
from repolens.extractors.python import PythonExtractor
from repolens.extractors.registry import ExtractorRegistry

__all__ = [
    "CommonJsExportKind",
    "CommonJsRequireKind",
    "EsmExportKind",
    "EsmImportKind",
    "EsmReExportKind",
    "ExtractionResult",
    "Extractor",
    "ExtractorRegistry",
    "ImportFactKind",
    "JavaScriptCallKind",
    "JavaScriptTypeScriptExtractor",
    "MarkdownExtractor",
    "MarkdownFactKind",
    "MetadataEcosystem",
    "ProjectMetadataExtractor",
    "ProjectMetadataFact",
    "PythonExtractor",
    "UnresolvedCommonJsExportFact",
    "UnresolvedCommonJsRequireFact",
    "UnresolvedEsmExportFact",
    "UnresolvedEsmImportFact",
    "UnresolvedEsmReExportFact",
    "UnresolvedImportFact",
    "UnresolvedJavaScriptCallFact",
    "UnresolvedMarkdownFact",
]
