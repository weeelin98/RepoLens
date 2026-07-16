"""Direct Python definition facts from the standard-library AST."""

from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath, PureWindowsPath

from repolens.extractors.base import ExtractionResult
from repolens.ids import normalize_repo_path, stable_node_id
from repolens.models import (
    EdgeKind,
    EvidenceKind,
    GraphEdge,
    GraphNode,
    NodeKind,
    SourceSpan,
)

_DefinitionNode = ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


def _normalized_source_path(path: Path) -> str:
    rendered = path.as_posix()
    if path.is_absolute() or PureWindowsPath(rendered).is_absolute():
        raise ValueError("extractor paths must be repository-relative")
    normalized = normalize_repo_path(rendered)
    if normalized == ".":
        raise ValueError("extractor path must name a file")
    return normalized


def _module_name(source_path: str) -> str:
    parts = list(PurePosixPath(source_path).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else "<root>"


def _module_span(source: str) -> SourceSpan:
    lines = source.splitlines()
    if not lines:
        return SourceSpan(start_line=1, end_line=1, start_column=0, end_column=0)
    return SourceSpan(
        start_line=1,
        end_line=len(lines),
        start_column=0,
        end_column=len(lines[-1].encode("utf-8")),
    )


def _definition_span(node: _DefinitionNode) -> SourceSpan:
    return SourceSpan(
        start_line=node.lineno,
        end_line=node.end_lineno if node.end_lineno is not None else node.lineno,
        start_column=node.col_offset,
        end_column=node.end_col_offset if node.end_col_offset is not None else node.col_offset,
    )


def _node_sort_key(node: GraphNode) -> tuple[object, ...]:
    span = node.span
    return (
        span.start_line if span else 0,
        span.start_column if span and span.start_column is not None else -1,
        node.qualified_name or "",
        node.kind.value,
        node.id,
    )


class _DefinitionVisitor(ast.NodeVisitor):
    def __init__(self, source_path: str, module_node: GraphNode) -> None:
        self._source_path = source_path
        self._scopes = [module_node]
        self.nodes: list[GraphNode] = [module_node]
        self.edges: list[GraphEdge] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_definition(node, NodeKind.CLASS)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        kind = NodeKind.METHOD if self._scopes[-1].kind is NodeKind.CLASS else NodeKind.FUNCTION
        self._visit_definition(node, kind)

    def _visit_definition(self, syntax_node: _DefinitionNode, kind: NodeKind) -> None:
        parent = self._scopes[-1]
        parent_qualified_name = parent.qualified_name
        if parent_qualified_name is None:
            raise ValueError("definition parent must have a qualified name")
        qualified_name = f"{parent_qualified_name}.{syntax_node.name}"
        span = _definition_span(syntax_node)
        node = GraphNode(
            id=stable_node_id(
                kind,
                source_path=self._source_path,
                qualified_name=qualified_name,
                start_line=span.start_line,
            ),
            kind=kind,
            label=syntax_node.name,
            language="python",
            source_path=self._source_path,
            span=span,
            qualified_name=qualified_name,
        )
        self.nodes.append(node)
        self.edges.append(
            GraphEdge(
                source_id=parent.id,
                target_id=node.id,
                relation=EdgeKind.CONTAINS,
                evidence_kind=EvidenceKind.SYNTAX_DIRECT,
                confidence=1.0,
                source_path=self._source_path,
                span=span,
            )
        )
        self._scopes.append(node)
        self.generic_visit(syntax_node)
        self._scopes.pop()


class PythonExtractor:
    """Extract Python definition structure without importing or executing source."""

    @property
    def extensions(self) -> frozenset[str]:
        return frozenset({".py"})

    def extract(self, path: Path, source: str) -> ExtractionResult:
        source_path = _normalized_source_path(path)
        try:
            tree = ast.parse(source, filename=source_path)
        except SyntaxError as error:
            line = error.lineno if error.lineno is not None else 1
            column = max((error.offset if error.offset is not None else 1) - 1, 0)
            return ExtractionResult(
                diagnostics=(f"python_syntax_error:{source_path}:{line}:{column}",)
            )

        module_name = _module_name(source_path)
        span = _module_span(source)
        module_node = GraphNode(
            id=stable_node_id(
                NodeKind.MODULE,
                source_path=source_path,
                qualified_name=module_name,
                start_line=span.start_line,
            ),
            kind=NodeKind.MODULE,
            label=module_name,
            language="python",
            source_path=source_path,
            span=span,
            qualified_name=module_name,
        )
        visitor = _DefinitionVisitor(source_path, module_node)
        visitor.visit(tree)
        return ExtractionResult(
            nodes=tuple(sorted(visitor.nodes, key=_node_sort_key)),
            edges=tuple(sorted(visitor.edges, key=GraphEdge.sort_key)),
        )
