"""Side-effect-free extractor protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from repolens.models import GraphEdge, GraphNode


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    diagnostics: tuple[str, ...] = ()


@runtime_checkable
class Extractor(Protocol):
    """Language adapter contract; implementations must not resolve cross-file facts."""

    @property
    def extensions(self) -> frozenset[str]: ...

    def extract(self, path: Path, source: str) -> ExtractionResult: ...
