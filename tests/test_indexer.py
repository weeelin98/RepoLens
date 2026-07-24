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
from repolens.extractors.base import (
    CommonJsExportKind,
    CommonJsRequireKind,
    EsmExportKind,
    EsmImportKind,
    EsmReExportKind,
    ImportFactKind,
    MetadataEcosystem,
)
from repolens.graph.serialization import canonical_index_json
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


def test_markdown_file_builds_file_document_and_heading_hierarchy(tmp_path: Path) -> None:
    markdown_path = write_file(tmp_path, "docs/README.md", "# Guide\n\n### Install\n")

    result = index_repository(tmp_path, RuntimeConfig())

    file_node = node_for_path(result, NodeKind.FILE, "docs/README.md")
    document = node_for_path(result, NodeKind.MARKDOWN_DOCUMENT, "docs/README.md")
    sections = nodes_of_kind(result, NodeKind.MARKDOWN_SECTION)
    by_label = {node.label: node for node in sections}
    edge_pairs = {(edge.source_id, edge.target_id) for edge in result.graph.edges}

    assert file_node.language == "markdown"
    assert file_node.metadata == {"size_bytes": markdown_path.stat().st_size, "suffix": ".md"}
    assert document.language == "markdown"
    assert (file_node.id, document.id) in edge_pairs
    assert (document.id, by_label["Guide"].id) in edge_pairs
    assert (by_label["Guide"].id, by_label["Install"].id) in edge_pairs
    assert nodes_of_kind(result, NodeKind.MODULE) == ()


def test_project_metadata_files_preserve_structural_nodes_and_direct_facts(
    tmp_path: Path,
) -> None:
    write_file(tmp_path, "pyproject.toml", '[project]\nname = "python-app"\n')
    write_file(tmp_path, "web/package.json", '{"name":"web-app"}')
    write_file(tmp_path, "web/tsconfig.json", '{"compilerOptions":{"strict":true}}')

    result = index_repository(tmp_path, RuntimeConfig())

    assert {node.source_path for node in nodes_of_kind(result, NodeKind.FILE)} == {
        "pyproject.toml",
        "web/package.json",
        "web/tsconfig.json",
    }
    assert {
        (fact.ecosystem, fact.field, fact.value, fact.source_path) for fact in result.metadata_facts
    } == {
        (
            MetadataEcosystem.PYTHON_PROJECT,
            "project.name",
            "python-app",
            "pyproject.toml",
        ),
        (MetadataEcosystem.NODE_PACKAGE, "name", "web-app", "web/package.json"),
        (
            MetadataEcosystem.TYPESCRIPT_CONFIG,
            "compilerOptions.strict",
            True,
            "web/tsconfig.json",
        ),
    }


def test_arbitrary_json_and_toml_do_not_appear_or_get_decoded(tmp_path: Path) -> None:
    write_file(tmp_path, "secret.json", '{"token":"secret"}')
    write_file(tmp_path, "config.toml", 'token = "secret"')
    write_file(tmp_path, "module.py", "")

    result = index_repository(tmp_path, RuntimeConfig())

    assert {node.source_path for node in nodes_of_kind(result, NodeKind.FILE)} == {"module.py"}
    assert result.metadata_facts == ()


def test_malformed_metadata_preserves_file_and_does_not_block_later_manifest(
    tmp_path: Path,
) -> None:
    write_file(tmp_path, "package.json", "{")
    write_file(tmp_path, "pyproject.toml", '[project]\nname = "valid"\n')

    result = index_repository(tmp_path, RuntimeConfig())

    assert node_for_path(result, NodeKind.FILE, "package.json")
    assert node_for_path(result, NodeKind.FILE, "pyproject.toml")
    assert [(fact.field, fact.value) for fact in result.metadata_facts] == [
        ("project.name", "valid")
    ]
    assert result.extractor_diagnostics == ("metadata_parse_error:package.json:json",)


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
    write_file(tmp_path, ".gitignore", "ignored.py\nignored.md\n")
    write_file(tmp_path, "ignored.py", "def hidden():\n    pass\n")
    write_file(tmp_path, "ignored.md", "# Hidden\n")
    write_file(tmp_path, "visible.py", "")

    result = index_repository(tmp_path, RuntimeConfig())

    assert "ignored.py" not in {node.source_path for node in result.graph.nodes}
    assert "ignored.md" not in {node.source_path for node in result.graph.nodes}
    assert all(fact.source_path != "ignored.md" for fact in result.markdown_facts)
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

    @property
    def filenames(self) -> frozenset[str]:
        return frozenset()

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


def test_javascript_and_typescript_facts_integrate_without_import_export_edges(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path,
        "web/app.js",
        "import client, { request as send } from './client.js';\n"
        "export const load = () => send();\n",
    )
    write_file(
        tmp_path,
        "web/service.ts",
        "export default class Service { async run(): Promise<void> {} }\n",
    )

    result = index_repository(tmp_path, RuntimeConfig())
    app_file = node_for_path(result, NodeKind.FILE, "web/app.js")
    service_file = node_for_path(result, NodeKind.FILE, "web/service.ts")
    names = {node.qualified_name: node.kind for node in result.graph.nodes}

    assert app_file.language == "javascript"
    assert service_file.language == "typescript"
    assert (
        names.items()
        >= {
            "web.app": NodeKind.MODULE,
            "web.app.load": NodeKind.FUNCTION,
            "web.service": NodeKind.MODULE,
            "web.service.Service": NodeKind.CLASS,
            "web.service.Service.run": NodeKind.METHOD,
        }.items()
    )
    assert [
        (fact.kind, fact.module, fact.imported_name, fact.local_name) for fact in result.esm_imports
    ] == [
        (EsmImportKind.DEFAULT, "./client.js", "default", "client"),
        (EsmImportKind.NAMED, "./client.js", "request", "send"),
    ]
    assert [
        (fact.kind, fact.exported_name, fact.local_name, fact.is_default)
        for fact in result.esm_exports
    ] == [
        (EsmExportKind.DECLARATION, "load", "load", False),
        (EsmExportKind.DECLARATION, "default", "Service", True),
    ]
    load = next(node for node in result.graph.nodes if node.qualified_name == "web.app.load")
    assert [(fact.callee, fact.enclosing_id) for fact in result.javascript_calls] == [
        ("send", load.id)
    ]
    assert all(
        edge.relation not in {EdgeKind.IMPORTS, EdgeKind.EXPORTS, EdgeKind.CALLS}
        for edge in result.graph.edges
    )


def test_javascript_typescript_index_is_repeatable_and_path_private(tmp_path: Path) -> None:
    write_file(
        tmp_path,
        "src/api.ts",
        "import { value } from './value.js';\nexport function load(): void {}\n",
    )

    first = canonical_index_json(index_repository(tmp_path, RuntimeConfig()))
    second = canonical_index_json(index_repository(tmp_path, RuntimeConfig()))

    assert first == second
    assert str(tmp_path) not in second
    assert str(tmp_path.resolve()) not in second
    assert '"esm_imports"' in second
    assert '"esm_exports"' in second


def test_malformed_javascript_preserves_module_and_error_free_siblings(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path,
        "broken.js",
        "function before() {}\n}\nfunction after() {}\n",
    )

    result = index_repository(tmp_path, RuntimeConfig())

    assert {node.qualified_name for node in result.graph.nodes if node.qualified_name} >= {
        "broken",
        "broken.before",
        "broken.after",
    }
    assert result.extractor_diagnostics == ("tree_sitter_syntax_error:broken.js:2:0",)


def test_jsx_and_tsx_are_discovered_with_honest_language_labels(tmp_path: Path) -> None:
    write_file(tmp_path, "src/component.jsx", "export function Component() {}")
    write_file(tmp_path, "src/component.tsx", "export function Component() {}")
    write_file(tmp_path, "src/visible.js", "export function visible() {}")

    result = index_repository(tmp_path, RuntimeConfig())

    source_paths = {node.source_path for node in result.graph.nodes}
    assert "src/visible.js" in source_paths
    assert "src/component.jsx" in source_paths
    assert "src/component.tsx" in source_paths
    assert node_for_path(result, NodeKind.FILE, "src/component.jsx").language == "jsx"
    assert node_for_path(result, NodeKind.FILE, "src/component.tsx").language == "tsx"
    assert node_for_path(result, NodeKind.MODULE, "src/component.jsx").language == "jsx"
    assert node_for_path(result, NodeKind.MODULE, "src/component.tsx").language == "tsx"


def test_javascript_source_is_parsed_but_never_executed(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed.txt"
    write_file(
        tmp_path,
        "danger.js",
        "import { writeFileSync } from 'node:fs';\n"
        f"writeFileSync({str(sentinel)!r}, 'executed');\n",
    )

    result = index_repository(tmp_path, RuntimeConfig())

    assert node_for_path(result, NodeKind.MODULE, "danger.js")
    assert not sentinel.exists()


def test_m21b_facts_and_typescript_declarations_merge_without_target_edges(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path,
        "a.js",
        "const value = require('pkg');\nexports.value = value;\n",
    )
    write_file(
        tmp_path,
        "b.ts",
        "export { value as renamed } from 'pkg';\n"
        "export interface Shape {}\n"
        "export type Name = string;\n"
        "export enum State { Ready }\n",
    )

    result = index_repository(tmp_path, RuntimeConfig())

    assert [(fact.kind, fact.module, fact.local_name) for fact in result.commonjs_requires] == [
        (CommonJsRequireKind.BINDING, "pkg", "value")
    ]
    assert [
        (fact.kind, fact.exported_name, fact.local_name) for fact in result.commonjs_exports
    ] == [(CommonJsExportKind.NAMED, "value", "value")]
    assert [
        (fact.kind, fact.module, fact.imported_name, fact.exported_name)
        for fact in result.esm_reexports
    ] == [(EsmReExportKind.NAMED, "pkg", "value", "renamed")]
    assert {node.kind for node in result.graph.nodes} >= {
        NodeKind.INTERFACE,
        NodeKind.TYPE_ALIAS,
        NodeKind.ENUM,
    }
    assert all(
        edge.relation not in {EdgeKind.IMPORTS, EdgeKind.EXPORTS} for edge in result.graph.edges
    )
