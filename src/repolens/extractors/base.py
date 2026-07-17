"""Side-effect-free extractor protocol."""

from __future__ import annotations

import json
import math
from enum import StrEnum
from pathlib import Path, PureWindowsPath
from typing import Any, Protocol, Self, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from repolens.ids import normalize_repo_path
from repolens.models import GraphEdge, GraphNode, SourceSpan


class ImportFactKind(StrEnum):
    """Syntactic import forms that remain unresolved during extraction."""

    IMPORT = "import"
    FROM_IMPORT = "from_import"


class EsmImportKind(StrEnum):
    """ECMAScript import forms preserved before module resolution."""

    SIDE_EFFECT = "side_effect"
    DEFAULT = "default"
    NAMESPACE = "namespace"
    NAMED = "named"


class EsmExportKind(StrEnum):
    """Supported local ECMAScript export forms."""

    DECLARATION = "declaration"
    LIST = "list"


class MarkdownFactKind(StrEnum):
    """Direct Markdown syntax forms that remain unresolved during extraction."""

    LINK = "link"
    FENCED_CODE = "fenced_code"
    INLINE_CODE = "inline_code"


class MetadataEcosystem(StrEnum):
    """Supported project metadata ecosystems."""

    PYTHON_PROJECT = "python_project"
    NODE_PACKAGE = "node_package"
    TYPESCRIPT_CONFIG = "typescript_config"


def _normalize_json_value(value: Any) -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("metadata values must be finite")
        return value
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("metadata mapping keys must be strings")
        return {key: _normalize_json_value(value[key]) for key in sorted(value)}
    raise ValueError("metadata values must be JSON-compatible")


class UnresolvedImportFact(BaseModel):
    """One imported alias preserved as direct syntax without a target claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ImportFactKind
    module: str | None = Field(default=None, min_length=1)
    imported_member: str | None = Field(default=None, min_length=1)
    alias: str | None = Field(default=None, min_length=1)
    relative_level: int = Field(default=0, ge=0)
    is_star: bool = False
    source_path: str = Field(min_length=1)
    span: SourceSpan

    @model_validator(mode="after")
    def validate_import_form(self) -> Self:
        if self.kind is ImportFactKind.IMPORT:
            if self.module is None:
                raise ValueError("direct import requires module")
            if self.imported_member is not None:
                raise ValueError("direct import cannot have imported_member")
            if self.relative_level != 0:
                raise ValueError("direct import cannot be relative")
            if self.is_star:
                raise ValueError("direct import cannot be a star import")
            return self

        if self.imported_member is None:
            raise ValueError("from-import requires imported_member")
        if self.module is None and self.relative_level == 0:
            raise ValueError("module-less from-import must be relative")
        if self.is_star != (self.imported_member == "*"):
            raise ValueError("is_star must match an imported '*' member")
        if self.is_star and self.alias is not None:
            raise ValueError("star import cannot have an alias")
        return self

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.source_path,
            self.span.start_line,
            self.span.start_column if self.span.start_column is not None else -1,
            self.kind.value,
            self.module or "",
            self.imported_member or "",
            self.alias or "",
            self.relative_level,
            self.is_star,
        )


def _normalize_fact_source_path(value: str) -> str:
    if PureWindowsPath(value).is_absolute():
        raise ValueError("fact source path must be repository-relative")
    normalized = normalize_repo_path(value)
    if normalized == ".":
        raise ValueError("fact source path must name a file")
    return normalized


class UnresolvedEsmImportFact(BaseModel):
    """One direct ESM import binding without a resolved target."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: EsmImportKind
    module: str = Field(min_length=1)
    imported_name: str | None = Field(default=None, min_length=1)
    local_name: str | None = Field(default=None, min_length=1)
    source_path: str = Field(min_length=1)
    span: SourceSpan

    _source_path_is_relative = field_validator("source_path")(_normalize_fact_source_path)

    @model_validator(mode="after")
    def validate_import_form(self) -> Self:
        if self.kind is EsmImportKind.SIDE_EFFECT:
            if self.imported_name is not None or self.local_name is not None:
                raise ValueError("side-effect imports cannot contain binding names")
        elif self.kind is EsmImportKind.DEFAULT:
            if self.imported_name != "default" or self.local_name is None:
                raise ValueError("default imports require the default and local names")
        elif self.kind is EsmImportKind.NAMESPACE:
            if self.imported_name != "*" or self.local_name is None:
                raise ValueError("namespace imports require '*' and a local name")
        elif self.imported_name is None or self.local_name is None:
            raise ValueError("named imports require imported and local names")
        return self

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.source_path,
            self.span.start_line,
            self.span.start_column if self.span.start_column is not None else -1,
            self.kind.value,
            self.module,
            self.imported_name or "",
            self.local_name or "",
        )


class UnresolvedEsmExportFact(BaseModel):
    """One supported local ESM export without resolution or an export edge."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: EsmExportKind
    exported_name: str = Field(min_length=1)
    local_name: str = Field(min_length=1)
    is_default: bool = False
    source_path: str = Field(min_length=1)
    span: SourceSpan

    _source_path_is_relative = field_validator("source_path")(_normalize_fact_source_path)

    @model_validator(mode="after")
    def validate_export_form(self) -> Self:
        if self.is_default != (self.exported_name == "default"):
            raise ValueError("is_default must match the exported 'default' name")
        return self

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.source_path,
            self.span.start_line,
            self.span.start_column if self.span.start_column is not None else -1,
            self.kind.value,
            self.exported_name,
            self.local_name,
            self.is_default,
        )


class UnresolvedMarkdownFact(BaseModel):
    """One direct Markdown syntax fact without a resolved graph target."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: MarkdownFactKind
    source_path: str = Field(min_length=1)
    span: SourceSpan
    occurrence: int = Field(ge=0)
    section_id: str | None = Field(default=None, min_length=1)
    text: str | None = None
    target: str | None = None
    title: str | None = None
    info: str | None = None
    language: str | None = None
    fence_marker: str | None = None
    line_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_fact_form(self) -> Self:
        if self.kind is MarkdownFactKind.LINK:
            if self.text is None or self.target is None:
                raise ValueError("Markdown link facts require text and target")
            if any(
                value is not None
                for value in (self.info, self.language, self.fence_marker, self.line_count)
            ):
                raise ValueError("Markdown link facts cannot contain fenced-code fields")
            return self

        if self.kind is MarkdownFactKind.INLINE_CODE:
            if self.text is None:
                raise ValueError("inline-code facts require text")
            if any(
                value is not None
                for value in (
                    self.target,
                    self.title,
                    self.info,
                    self.language,
                    self.fence_marker,
                    self.line_count,
                )
            ):
                raise ValueError("inline-code facts cannot contain link or fence fields")
            return self

        if self.fence_marker is None or self.line_count is None:
            raise ValueError("fenced-code facts require fence_marker and line_count")
        if any(value is not None for value in (self.text, self.target, self.title)):
            raise ValueError("fenced-code facts cannot contain link or inline-code fields")
        return self

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.source_path,
            self.span.start_line,
            self.span.start_column if self.span.start_column is not None else -1,
            self.occurrence,
            self.kind.value,
            self.section_id or "",
            self.text or "",
            self.target or "",
            self.title or "",
            self.info or "",
            self.language or "",
            self.fence_marker or "",
            self.line_count if self.line_count is not None else -1,
        )


class ProjectMetadataFact(BaseModel):
    """One documented direct manifest field without resolution or execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ecosystem: MetadataEcosystem
    field: str = Field(min_length=1)
    value: JsonValue
    source_path: str = Field(min_length=1)
    span: SourceSpan | None = None

    @field_validator("value", mode="before")
    @classmethod
    def normalize_value(cls, value: Any) -> JsonValue:
        return _normalize_json_value(value)

    @field_validator("source_path")
    @classmethod
    def normalize_source_path(cls, value: str) -> str:
        if PureWindowsPath(value).is_absolute():
            raise ValueError("metadata source path must be repository-relative")
        normalized = normalize_repo_path(value)
        if normalized == ".":
            raise ValueError("metadata source path must name a file")
        return normalized

    def sort_key(self) -> tuple[object, ...]:
        return (
            self.source_path,
            self.ecosystem.value,
            self.field,
            json.dumps(
                self.value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    imports: tuple[UnresolvedImportFact, ...] = ()
    esm_imports: tuple[UnresolvedEsmImportFact, ...] = ()
    esm_exports: tuple[UnresolvedEsmExportFact, ...] = ()
    markdown_facts: tuple[UnresolvedMarkdownFact, ...] = ()
    metadata_facts: tuple[ProjectMetadataFact, ...] = ()
    diagnostics: tuple[str, ...] = ()


@runtime_checkable
class Extractor(Protocol):
    """Language adapter contract; implementations must not resolve cross-file facts."""

    @property
    def extensions(self) -> frozenset[str]: ...

    @property
    def filenames(self) -> frozenset[str]: ...

    def extract(self, path: Path, source: str) -> ExtractionResult: ...
