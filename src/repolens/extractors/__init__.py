"""Extractor interfaces; language implementations begin in later milestones."""

from repolens.extractors.base import ExtractionResult, Extractor
from repolens.extractors.registry import ExtractorRegistry

__all__ = ["ExtractionResult", "Extractor", "ExtractorRegistry"]
