"""Normalized graph models shared by every RepoLens layer."""

from __future__ import annotations

import json
import math
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NodeKind(StrEnum):
    REPOSITORY = "repository"
    DIRECTORY = "directory"
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    REACT_COMPONENT = "react_component"
    API_ENDPOINT = "api_endpoint"
    DATA_MODEL = "data_model"
    TEST = "test"
    MARKDOWN_DOCUMENT = "markdown_document"
    MARKDOWN_SECTION = "markdown_section"
    EXTERNAL_DEPENDENCY = "external_dependency"


class EdgeKind(StrEnum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    EXPORTS = "exports"
    CALLS = "calls"
    INHERITS = "inherits"
    DEFINES_ENDPOINT = "defines_endpoint"
    INVOKES_ENDPOINT = "invokes_endpoint"
    DOCUMENTS = "documents"
    REFERENCES = "references"
    TESTS = "tests"
    READS_MODEL = "reads_model"
    WRITES_MODEL = "writes_model"


class EvidenceKind(StrEnum):
    SYNTAX_DIRECT = "syntax_direct"
    RESOLVER_DERIVED = "resolver_derived"
    HEURISTIC = "heuristic"
    AMBIGUOUS_UNRESOLVED = "ambiguous_unresolved"


class SourceSpan(BaseModel):
    """A 1-based, inclusive source span."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    start_column: int | None = Field(default=None, ge=0)
    end_column: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        if (
            self.start_line == self.end_line
            and self.start_column is not None
            and self.end_column is not None
            and self.end_column < self.start_column
        ):
            raise ValueError("end_column must not precede start_column on one line")
        return self


def _validate_json_object(value: dict[str, Any]) -> dict[str, Any]:
    """Reject non-JSON and non-finite metadata at the model boundary."""

    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("metadata must contain finite JSON-compatible values") from error
    return value


class GraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    kind: NodeKind
    label: str = Field(min_length=1)
    language: str | None = None
    source_path: str | None = None
    span: SourceSpan | None = None
    qualified_name: str | None = None
    signature: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    _metadata_is_json = field_validator("metadata")(_validate_json_object)


class GraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    relation: EdgeKind
    evidence_kind: EvidenceKind
    confidence: float = Field(ge=0.0, le=1.0)
    source_path: str | None = None
    span: SourceSpan | None = None
    resolver_notes: str | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if not math.isfinite(self.confidence):
            raise ValueError("confidence must be finite")
        if self.evidence_kind is EvidenceKind.SYNTAX_DIRECT and self.confidence != 1.0:
            raise ValueError("syntax_direct evidence must have confidence 1.0")
        if self.evidence_kind is EvidenceKind.HEURISTIC and self.confidence >= 1.0:
            raise ValueError("heuristic evidence must not be represented as certain")
        if self.evidence_kind is EvidenceKind.AMBIGUOUS_UNRESOLVED:
            if self.confidence > 0.5:
                raise ValueError("ambiguous evidence confidence must be at most 0.5")
            if not self.resolver_notes:
                raise ValueError("ambiguous evidence requires resolver_notes")
        return self

    def sort_key(self) -> tuple[object, ...]:
        span = self.span
        return (
            self.source_id,
            self.target_id,
            self.relation.value,
            self.evidence_kind.value,
            self.source_path or "",
            span.start_line if span else 0,
            span.start_column if span and span.start_column is not None else -1,
            self.resolver_notes or "",
        )


class GraphSnapshot(BaseModel):
    """A validated graph whose collections are normalized into stable order."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(default=1, ge=1)
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    _metadata_is_json = field_validator("metadata")(_validate_json_object)

    @model_validator(mode="after")
    def normalize_and_validate(self) -> Self:
        nodes = tuple(sorted(self.nodes, key=lambda node: node.id))
        node_ids = [node.id for node in nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("graph node IDs must be unique")

        edges = tuple(sorted(self.edges, key=GraphEdge.sort_key))
        known = set(node_ids)
        missing = sorted(
            {edge_id for edge in edges for edge_id in (edge.source_id, edge.target_id)} - known
        )
        if missing:
            raise ValueError(f"edge endpoints are missing from graph nodes: {', '.join(missing)}")
        if len({edge.sort_key() for edge in edges}) != len(edges):
            raise ValueError("duplicate graph edges are not allowed")

        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        return self
