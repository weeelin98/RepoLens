from __future__ import annotations

import json
import tokenize
from collections.abc import Callable
from pathlib import Path
from typing import IO

import pytest
from pydantic import ValidationError

from repolens.config import RuntimeConfig
from repolens.extractors import ExtractionResult, ExtractorRegistry
from repolens.extractors.base import ImportFactKind
from repolens.ids import stable_node_id
from repolens.indexer import RepositoryIndexResult, index_repository
from repolens.models import EdgeKind, GraphNode, NodeKind
from repolens.scanner import ScanDiagnosticCode


def write_file(root: Path, relative_path: str, content: str = "") -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def nodes_of_kind(result: RepositoryIndexResult, kind: NodeKind) -> tuple[GraphNode, ...]:
    return tuple(node for node in result.graph.nodes if node.kind is kind)


def node_for_path(
    result: RepositoryIndexResult,
    kind: NodeKind,
    source_path: str,
) -> GraphNode:
    return next(
        node for node in result.graph.nodes if node.kind is kind and node.source_path == source_path
    )


def test_empty_repository_produces_one_repository_node(tmp_path: Path) -> None:
    result = index_repository(tmp_path, RuntimeConfig())

    assert result == RepositoryIndexResult(
        graph=result.graph,
    )
    assert len(result.graph.nodes) == 1
    repository = result.graph.nodes[0]
    assert repository == GraphNode(
        id=stable_node_id(
            NodeKind.REPOSITORY,
            source_path=".",
            qualified_name="<repository>",
        ),
        kind=NodeKind.REPOSITORY,
        label="<repository>",
        source_path=".",
        qualified_name="<repository>",
    )
    assert result.graph.edges == ()


def test_root_python_file_builds_repository_file_module_and_edges(tmp_path: Path) -> None:
    write_file(tmp_path, "app.py", "")

    result = index_repository(tmp_path, RuntimeConfig())

    assert tuple(node.kind for node in result.graph.nodes).count(NodeKind.REPOSITORY) == 1
    assert len(nodes_of_kind(result, NodeKind.FILE)) == 1
    assert len(nodes_of_kind(result, NodeKind.MODULE)) == 1
    repository = nodes_of_kind(result, NodeKind.REPOSITORY)[0]
    file_node = node_for_path(result, NodeKind.FILE, "app.py")
    module = node_for_path(result, NodeKind.MODULE, "app.py")
    assert {(edge.source_id, edge.target_id) for edge in result.graph.edges} == {
        (repository.id, file_node.id),
        (file_node.id, module.id),
    }


def test_nested_python_file_creates_deterministic_directory_hierarchy(tmp_path: Path) -> None:
    write_file(tmp_path, "services/api/user.py", "")

    result = index_repository(tmp_path, RuntimeConfig())

    repository = nodes_of_kind(result, NodeKind.REPOSITORY)[0]
    services = node_for_path(result, NodeKind.DIRECTORY, "services")
    api = node_for_path(result, NodeKind.DIRECTORY, "services/api")
    file_node = node_for_path(result, NodeKind.FILE, "services/api/user.py")
    assert services.id == stable_node_id(NodeKind.DIRECTORY, source_path="services")
    assert api.id == stable_node_id(NodeKind.DIRECTORY, source_path="services/api")
    assert {(edge.source_id, edge.target_id) for edge in result.graph.edges} >= {
        (repository.id, services.id),
        (services.id, api.id),
        (api.id, file_node.id),
    }


def test_markdown_file_has_structure_without_module_or_content_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_file(tmp_path, "README.md", "# Guide")

    def unexpected_open(filename: str | Path) -> IO[str]:
        raise AssertionError(f"Markdown must not be read: {filename}")

    monkeypatch.setattr(tokenize, "open", unexpected_open)
    result = index_repository(tmp_path, RuntimeConfig())

    file_node = node_for_path(result, NodeKind.FILE, "README.md")
    assert file_node.language == "markdown"
    assert file_node.metadata == {"size_bytes": 7, "suffix": ".md"}
    assert nodes_of_kind(result, NodeKind.MODULE) == ()


def test_python_definitions_are_merged_into_graph(tmp_path: Path) -> None:
    write_file(
        tmp_path,
        "service.py",
        "class Service:\n    def load(self):\n        return 1\n",
    )

    result = index_repository(tmp_path, RuntimeConfig())

    by_name = {node.qualified_name: node for node in result.graph.nodes}
    assert by_name["service.Service"].kind is NodeKind.CLASS
    assert by_name["service.Service.load"].kind is NodeKind.METHOD


def test_extractor_contains_edges_keep_nearest_parents(tmp_path: Path) -> None:
    write_file(
        tmp_path,
        "service.py",
        "class Service:\n    def load(self):\n        def validate():\n            return True\n",
    )

    result = index_repository(tmp_path, RuntimeConfig())
    by_name = {node.qualified_name: node for node in result.graph.nodes}
    edge_pairs = {(edge.source_id, edge.target_id) for edge in result.graph.edges}

    assert (by_name["service"].id, by_name["service.Service"].id) in edge_pairs
    assert (by_name["service.Service"].id, by_name["service.Service.load"].id) in edge_pairs
    assert (
        by_name["service.Service.load"].id,
        by_name["service.Service.load.validate"].id,
    ) in edge_pairs


def test_python_file_to_module_edge_is_created(tmp_path: Path) -> None:
    write_file(tmp_path, "pkg/module.py", "")

    result = index_repository(tmp_path, RuntimeConfig())
    file_node = node_for_path(result, NodeKind.FILE, "pkg/module.py")
    module = node_for_path(result, NodeKind.MODULE, "pkg/module.py")
    matching = [
        edge
        for edge in result.graph.edges
        if edge.source_id == file_node.id and edge.target_id == module.id
    ]

    assert len(matching) == 1
    assert matching[0].relation is EdgeKind.CONTAINS
    assert matching[0].span == module.span


def test_unresolved_import_facts_are_preserved_without_import_edges(tmp_path: Path) -> None:
    write_file(tmp_path, "module.py", "import os\nfrom . import local\n")

    result = index_repository(tmp_path, RuntimeConfig())

    assert [
        (fact.kind, fact.module, fact.imported_member, fact.relative_level)
        for fact in result.imports
    ] == [
        (ImportFactKind.IMPORT, "os", None, 0),
        (ImportFactKind.FROM_IMPORT, None, "local", 1),
    ]
    assert all(edge.relation is not EdgeKind.IMPORTS for edge in result.graph.edges)


def test_ignored_files_never_appear(tmp_path: Path) -> None:
    write_file(tmp_path, ".gitignore", "ignored.py\n")
    write_file(tmp_path, "ignored.py", "def hidden():\n    pass\n")
    write_file(tmp_path, "visible.py", "")

    result = index_repository(tmp_path, RuntimeConfig())

    assert "ignored.py" not in {node.source_path for node in result.graph.nodes}
    assert node_for_path(result, NodeKind.FILE, "visible.py")


def test_files_excluded_by_scanner_limits_never_appear(tmp_path: Path) -> None:
    write_file(tmp_path, "a.py", "")
    write_file(tmp_path, "b.py", "")

    result = index_repository(tmp_path, RuntimeConfig(maximum_file_count=1))

    assert {node.source_path for node in nodes_of_kind(result, NodeKind.FILE)} == {"a.py"}
    assert tuple(diagnostic.code for diagnostic in result.scanner_diagnostics) == (
        ScanDiagnosticCode.FILE_COUNT_LIMIT_REACHED,
    )
    assert result.scanner_diagnostics[0].path == "b.py"


def test_all_source_paths_are_repository_relative_posix(tmp_path: Path) -> None:
    write_file(tmp_path, "services/api/user.py", "def load():\n    pass\n")

    result = index_repository(tmp_path, RuntimeConfig())

    paths = [node.source_path for node in result.graph.nodes if node.source_path is not None]
    assert "services/api/user.py" in paths
    assert all("\\" not in path for path in paths)
    assert all(not Path(path).is_absolute() for path in paths)


def test_absolute_repository_path_does_not_leak_into_models(tmp_path: Path) -> None:
    write_file(tmp_path, "nested/module.py", "import os\n")

    result = index_repository(tmp_path, RuntimeConfig())
    rendered = json.dumps(result.model_dump(mode="json"), sort_keys=True)

    assert str(tmp_path) not in rendered
    assert str(tmp_path.resolve()) not in rendered


def test_python_encoding_cookie_is_respected(tmp_path: Path) -> None:
    path = tmp_path / "encoded.py"
    path.write_bytes(b"# coding: cp1252\nname = 'caf\xe9'\n")

    result = index_repository(tmp_path, RuntimeConfig())

    assert len(nodes_of_kind(result, NodeKind.MODULE)) == 1
    assert result.extractor_diagnostics == ()


def test_invalid_python_preserves_file_node_and_extractor_diagnostic(tmp_path: Path) -> None:
    write_file(tmp_path, "broken.py", ")")

    result = index_repository(tmp_path, RuntimeConfig())

    assert node_for_path(result, NodeKind.FILE, "broken.py")
    assert nodes_of_kind(result, NodeKind.MODULE) == ()
    assert result.extractor_diagnostics == ("python_syntax_error:broken.py:1:0",)


def test_source_read_failure_preserves_file_node_and_emits_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_file(tmp_path, "denied.py", "")

    def denied_open(filename: str | Path) -> IO[str]:
        raise PermissionError(filename)

    monkeypatch.setattr(tokenize, "open", denied_open)
    result = index_repository(tmp_path, RuntimeConfig())

    assert node_for_path(result, NodeKind.FILE, "denied.py")
    assert nodes_of_kind(result, NodeKind.MODULE) == ()
    assert result.extractor_diagnostics == ("source_load_error:denied.py:permission_denied",)


def test_one_read_failure_does_not_block_later_valid_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_file(tmp_path, "a_failed.py", "")
    write_file(tmp_path, "z_valid.py", "def load():\n    pass\n")
    original_open: Callable[[str | Path], IO[str]] = tokenize.open

    def selective_open(filename: str | Path) -> IO[str]:
        if Path(filename).name == "a_failed.py":
            raise OSError(filename)
        return original_open(filename)

    monkeypatch.setattr(tokenize, "open", selective_open)
    result = index_repository(tmp_path, RuntimeConfig())

    assert {node.source_path for node in nodes_of_kind(result, NodeKind.FILE)} == {
        "a_failed.py",
        "z_valid.py",
    }
    assert node_for_path(result, NodeKind.MODULE, "z_valid.py")
    assert result.extractor_diagnostics == ("source_load_error:a_failed.py:filesystem_error",)


def test_every_edge_references_existing_nodes(tmp_path: Path) -> None:
    write_file(
        tmp_path,
        "pkg/service.py",
        "class Service:\n    def load(self):\n        pass\n",
    )

    result = index_repository(tmp_path, RuntimeConfig())
    node_ids = {node.id for node in result.graph.nodes}

    assert all(
        edge.source_id in node_ids and edge.target_id in node_ids for edge in result.graph.edges
    )


class DuplicateNodeExtractor:
    @property
    def extensions(self) -> frozenset[str]:
        return frozenset({".py"})

    def extract(self, path: Path, source: str) -> ExtractionResult:
        duplicate = GraphNode(id="duplicate", kind=NodeKind.MODULE, label="duplicate")
        return ExtractionResult(nodes=(duplicate, duplicate))


def test_duplicate_extractor_node_ids_are_rejected(tmp_path: Path) -> None:
    write_file(tmp_path, "module.py", "")
    registry = ExtractorRegistry()
    registry.register(DuplicateNodeExtractor())

    with pytest.raises(ValidationError, match="graph node IDs must be unique"):
        index_repository(tmp_path, RuntimeConfig(), registry)


def test_repeated_indexing_returns_equal_results(tmp_path: Path) -> None:
    write_file(tmp_path, "pkg/module.py", "import os\n\ndef load():\n    pass\n")

    first = index_repository(tmp_path, RuntimeConfig())
    second = index_repository(tmp_path, RuntimeConfig())

    assert first == second


def test_python_source_is_parsed_but_never_imported_or_executed(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed.txt"
    write_file(
        tmp_path,
        "danger.py",
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('executed', encoding='utf-8')\n",
    )

    result = index_repository(tmp_path, RuntimeConfig())

    assert len(nodes_of_kind(result, NodeKind.MODULE)) == 1
    assert not sentinel.exists()


def test_injected_registry_is_authoritative_and_not_mutated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_file(tmp_path, "module.py", "def load():\n    pass\n")
    registry = ExtractorRegistry()

    def unexpected_open(filename: str | Path) -> IO[str]:
        raise AssertionError(f"An empty registry must not read source: {filename}")

    monkeypatch.setattr(tokenize, "open", unexpected_open)
    result = index_repository(tmp_path, RuntimeConfig(), registry)

    assert registry.extensions == ()
    assert len(nodes_of_kind(result, NodeKind.FILE)) == 1
    assert nodes_of_kind(result, NodeKind.MODULE) == ()
