"""Deterministic in-memory assembly of scanned and extracted repository facts."""

from __future__ import annotations

import tokenize
from pathlib import Path, PurePosixPath
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from repolens.config import RuntimeConfig
from repolens.extractors.base import UnresolvedImportFact
from repolens.extractors.python import PythonExtractor
from repolens.extractors.registry import ExtractorRegistry
from repolens.ids import stable_node_id
from repolens.models import (
    EdgeKind,
    EvidenceKind,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    NodeKind,
)
from repolens.scanner import ScanDiagnostic, SourceFile, scan_repository

_REPOSITORY_SENTINEL = "<repository>"
_LANGUAGES_BY_SUFFIX = {".md": "markdown", ".py": "python"}


class RepositoryIndexResult(BaseModel):
    """One normalized graph plus unresolved and diagnostic indexing facts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    graph: GraphSnapshot
    imports: tuple[UnresolvedImportFact, ...] = ()
    scanner_diagnostics: tuple[ScanDiagnostic, ...] = ()
    extractor_diagnostics: tuple[str, ...] = ()

    @model_validator(mode="after")
    def normalize_collections(self) -> Self:
        object.__setattr__(
            self,
            "imports",
            tuple(sorted(self.imports, key=UnresolvedImportFact.sort_key)),
        )
        object.__setattr__(
            self,
            "scanner_diagnostics",
            tuple(
                sorted(
                    self.scanner_diagnostics,
                    key=lambda diagnostic: (
                        diagnostic.path or "",
                        diagnostic.code.value,
                        diagnostic.message,
                    ),
                )
            ),
        )
        object.__setattr__(
            self,
            "extractor_diagnostics",
            tuple(sorted(self.extractor_diagnostics)),
        )
        return self


def _default_registry() -> ExtractorRegistry:
    registry = ExtractorRegistry()
    registry.register(PythonExtractor())
    return registry


def _repository_node() -> GraphNode:
    return GraphNode(
        id=stable_node_id(
            NodeKind.REPOSITORY,
            source_path=".",
            qualified_name=_REPOSITORY_SENTINEL,
        ),
        kind=NodeKind.REPOSITORY,
        label=_REPOSITORY_SENTINEL,
        source_path=".",
        qualified_name=_REPOSITORY_SENTINEL,
    )


def _directory_paths(files: tuple[SourceFile, ...]) -> tuple[str, ...]:
    paths: set[str] = set()
    for source_file in files:
        parent = PurePosixPath(source_file.relative_path).parent
        while parent.as_posix() != ".":
            paths.add(parent.as_posix())
            parent = parent.parent
    return tuple(sorted(paths, key=lambda path: (len(PurePosixPath(path).parts), path)))


def _contains_edge(parent: GraphNode, child: GraphNode) -> GraphEdge:
    return GraphEdge(
        source_id=parent.id,
        target_id=child.id,
        relation=EdgeKind.CONTAINS,
        evidence_kind=EvidenceKind.SYNTAX_DIRECT,
        confidence=1.0,
        source_path=child.source_path,
        span=child.span,
    )


def _load_source(resolved_root: Path, source_file: SourceFile) -> tuple[str | None, str | None]:
    relative_path = source_file.relative_path
    candidate = resolved_root.joinpath(*PurePosixPath(relative_path).parts)
    try:
        resolved_candidate = candidate.resolve(strict=True)
    except PermissionError:
        return None, f"source_load_error:{relative_path}:permission_denied"
    except OSError:
        return None, f"source_load_error:{relative_path}:filesystem_error"

    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return None, f"source_load_error:{relative_path}:outside_repository"

    try:
        with tokenize.open(resolved_candidate) as stream:
            return stream.read(), None
    except PermissionError:
        return None, f"source_load_error:{relative_path}:permission_denied"
    except UnicodeDecodeError:
        return None, f"source_load_error:{relative_path}:decode_failed"
    except (SyntaxError, LookupError):
        return None, f"source_load_error:{relative_path}:encoding_error"
    except OSError:
        return None, f"source_load_error:{relative_path}:filesystem_error"


def index_repository(
    repository_root: Path,
    config: RuntimeConfig,
    registry: ExtractorRegistry | None = None,
) -> RepositoryIndexResult:
    """Scan, extract, and assemble one deterministic in-memory repository index."""

    scan_result = scan_repository(repository_root, config)
    resolved_root = repository_root.resolve()
    active_registry = registry if registry is not None else _default_registry()

    repository_node = _repository_node()
    nodes: list[GraphNode] = [repository_node]
    edges: list[GraphEdge] = []
    imports: list[UnresolvedImportFact] = []
    extractor_diagnostics: list[str] = []
    directory_nodes: dict[str, GraphNode] = {}
    file_nodes: dict[str, GraphNode] = {}

    for directory_path in _directory_paths(scan_result.files):
        node = GraphNode(
            id=stable_node_id(NodeKind.DIRECTORY, source_path=directory_path),
            kind=NodeKind.DIRECTORY,
            label=PurePosixPath(directory_path).name,
            source_path=directory_path,
        )
        directory_nodes[directory_path] = node
        nodes.append(node)
        parent_path = PurePosixPath(directory_path).parent.as_posix()
        parent = repository_node if parent_path == "." else directory_nodes[parent_path]
        edges.append(_contains_edge(parent, node))

    for source_file in scan_result.files:
        source_path = source_file.relative_path
        node = GraphNode(
            id=stable_node_id(NodeKind.FILE, source_path=source_path),
            kind=NodeKind.FILE,
            label=PurePosixPath(source_path).name,
            language=_LANGUAGES_BY_SUFFIX.get(source_file.suffix),
            source_path=source_path,
            metadata={
                "size_bytes": source_file.size_bytes,
                "suffix": source_file.suffix,
            },
        )
        file_nodes[source_path] = node
        nodes.append(node)
        parent_path = PurePosixPath(source_path).parent.as_posix()
        parent = repository_node if parent_path == "." else directory_nodes[parent_path]
        edges.append(_contains_edge(parent, node))

    for source_file in scan_result.files:
        source_path = source_file.relative_path
        extractor = active_registry.for_path(Path(source_path))
        if extractor is None:
            continue

        source, diagnostic = _load_source(resolved_root, source_file)
        if diagnostic is not None:
            extractor_diagnostics.append(diagnostic)
            continue
        if source is None:
            raise ValueError("source loader returned neither source nor diagnostic")

        extraction = extractor.extract(Path(source_path), source)
        nodes.extend(extraction.nodes)
        edges.extend(extraction.edges)
        imports.extend(extraction.imports)
        extractor_diagnostics.extend(extraction.diagnostics)
        file_node = file_nodes[source_path]
        edges.extend(
            _contains_edge(file_node, node)
            for node in extraction.nodes
            if node.kind is NodeKind.MODULE
        )

    return RepositoryIndexResult(
        graph=GraphSnapshot(nodes=tuple(nodes), edges=tuple(edges)),
        imports=tuple(imports),
        scanner_diagnostics=scan_result.diagnostics,
        extractor_diagnostics=tuple(extractor_diagnostics),
    )
