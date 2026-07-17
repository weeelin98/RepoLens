"""Side-effect-free extractor protocol."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Protocol, Self, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from repolens.models import GraphEdge, GraphNode, SourceSpan


class ImportFactKind(StrEnum):
    """Syntactic import forms that remain unresolved during extraction."""

    IMPORT = "import"
    FROM_IMPORT = "from_import"


class MarkdownFactKind(StrEnum):
    """Direct Markdown syntax forms that remain unresolved during extraction."""

    LINK = "link"
    FENCED_CODE = "fenced_code"
    INLINE_CODE = "inline_code"


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


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    imports: tuple[UnresolvedImportFact, ...] = ()
    markdown_facts: tuple[UnresolvedMarkdownFact, ...] = ()
    diagnostics: tuple[str, ...] = ()


@runtime_checkable
class Extractor(Protocol):
    """Language adapter contract; implementations must not resolve cross-file facts."""

    @property
    def extensions(self) -> frozenset[str]: ...

    def extract(self, path: Path, source: str) -> ExtractionResult: ...
