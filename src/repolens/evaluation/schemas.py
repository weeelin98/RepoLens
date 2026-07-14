"""Versioned schemas for synthetic corpora and gold expectations."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from repolens.models import EdgeKind, EvidenceKind, NodeKind, SourceSpan


def _relative_path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or path.as_posix() in {"", "."}:
        raise ValueError("fixture references must be non-empty safe relative paths")
    return path.as_posix().removeprefix("./")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Citation(StrictModel):
    source_path: str
    span: SourceSpan

    _path_is_relative = field_validator("source_path")(_relative_path)


class ExpectedNode(StrictModel):
    id: str = Field(min_length=1)
    kind: NodeKind
    source_path: str | None = None
    span: SourceSpan | None = None

    @field_validator("source_path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        return None if value is None else _relative_path(value)


class ExpectedEdge(StrictModel):
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    relation: EdgeKind
    evidence_kind: EvidenceKind
    source_citation: Citation | None = None


class ExpectedQueryResult(StrictModel):
    query_id: str = Field(min_length=1)
    expected_node_ids: tuple[str, ...] = ()


class ExpectedDependencyPath(StrictModel):
    id: str = Field(min_length=1)
    node_ids: tuple[str, ...] = Field(min_length=2)
    edge_relations: tuple[EdgeKind, ...]

    @model_validator(mode="after")
    def validate_length(self) -> Self:
        if len(self.edge_relations) != len(self.node_ids) - 1:
            raise ValueError("a dependency path needs exactly one relation per hop")
        return self


class ExpectedChangeImpact(StrictModel):
    case_id: str = Field(min_length=1)
    expected_affected_symbol_ids: tuple[str, ...] = ()


class GoldData(StrictModel):
    schema_version: int = Field(default=1, ge=1)
    expected_nodes: tuple[ExpectedNode, ...] = ()
    expected_edges: tuple[ExpectedEdge, ...] = ()
    expected_ambiguous_relationships: tuple[ExpectedEdge, ...] = ()
    expected_query_results: tuple[ExpectedQueryResult, ...] = ()
    expected_dependency_paths: tuple[ExpectedDependencyPath, ...] = ()
    expected_change_impacts: tuple[ExpectedChangeImpact, ...] = ()

    @model_validator(mode="after")
    def validate_unique_nodes(self) -> Self:
        ids = [node.id for node in self.expected_nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("gold expected node IDs must be unique")
        return self


class GoldQuestion(StrictModel):
    id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    question: str = Field(min_length=1)
    expected_node_ids: tuple[str, ...] = ()
    expected_edge_relations: tuple[EdgeKind, ...] = ()
    expected_source_citations: tuple[Citation, ...] = ()
    maximum_context_tokens: int = Field(gt=0)


class DiffCase(StrictModel):
    schema_version: int = Field(default=1, ge=1)
    id: str = Field(min_length=1)
    git_range: str = Field(min_length=1)
    patch_file: str
    changed_paths: tuple[str, ...] = Field(min_length=1)
    expected_changed_symbol_ids: tuple[str, ...] = Field(min_length=1)
    expected_affected_symbol_ids: tuple[str, ...] = Field(min_length=1)

    _patch_is_relative = field_validator("patch_file")(_relative_path)
    _paths_are_relative = field_validator("changed_paths")(
        lambda values: tuple(_relative_path(value) for value in values)
    )


class HarnessManifest(StrictModel):
    schema_version: int = Field(default=1, ge=1)
    fixture_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    description: str = Field(min_length=1)
    languages: tuple[str, ...] = Field(min_length=1)
    repository: str
    gold: str
    questions: str
    diff_cases: tuple[str, ...] = Field(min_length=1)

    _repository_is_relative = field_validator("repository")(_relative_path)
    _gold_is_relative = field_validator("gold")(_relative_path)
    _questions_is_relative = field_validator("questions")(_relative_path)
    _diffs_are_relative = field_validator("diff_cases")(
        lambda values: tuple(_relative_path(value) for value in values)
    )
