from __future__ import annotations

import difflib
import json
import os
import shutil
import socket
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from repolens.cli import app
from repolens.config import RuntimeConfig
from repolens.graph.serialization import canonical_index_json, parse_index_json
from repolens.indexer import RepositoryIndexResult, index_repository
from repolens.models import NodeKind, SourceSpan

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURES_ROOT = PROJECT_ROOT / "harness" / "fixtures"
SELECTED_FIXTURES = (
    "python_service",
    "markdown_documented_project",
    "fullstack_fastapi_react",
    "typescript_frontend",
)
FIXTURE_TEXT_SUFFIXES = frozenset({".js", ".json", ".jsx", ".md", ".py", ".toml", ".ts", ".tsx"})
EXPECTED_COUNTS = {
    "python_service": (14, 13, 2, 0),
    "markdown_documented_project": (10, 9, 0, 0),
    "fullstack_fastapi_react": (26, 25, 9, 0),
    "typescript_frontend": (2, 1, 0, 0),
}
runner = CliRunner()
M1_POST_MILESTONE_IGNORE = "*.js\n*.ts\n*.jsx\n*.tsx\n"


def _copy_fixture_repository(tmp_path: Path, fixture_id: str) -> Path:
    source = FIXTURES_ROOT / fixture_id / "repo"
    repository = tmp_path / fixture_id
    shutil.copytree(source, repository)
    (repository / ".gitignore").write_text(
        M1_POST_MILESTONE_IGNORE,
        encoding="utf-8",
        newline="\n",
    )
    return repository


def _gold_bytes(fixture_id: str) -> bytes:
    return (FIXTURES_ROOT / fixture_id / "m1-graph.json").read_bytes()


def _graph_bytes(repository: Path) -> bytes:
    return (repository / "repolens-out" / "graph.json").read_bytes()


@pytest.mark.parametrize("fixture_id", SELECTED_FIXTURES)
def test_selected_fixture_sources_and_gold_use_lf(fixture_id: str) -> None:
    fixture_root = FIXTURES_ROOT / fixture_id
    source_files = tuple(
        path
        for path in (fixture_root / "repo").rglob("*")
        if path.is_file() and path.suffix in FIXTURE_TEXT_SUFFIXES
    )

    assert source_files
    for path in (*source_files, fixture_root / "m1-graph.json"):
        assert b"\r" not in path.read_bytes(), f"CR line ending found in {path}"


def _assert_matches_gold(fixture_id: str, expected: bytes, actual: bytes) -> None:
    if expected == actual:
        return
    difference = "".join(
        difflib.unified_diff(
            expected.decode("utf-8").splitlines(keepends=True),
            actual.decode("utf-8").splitlines(keepends=True),
            fromfile=f"{fixture_id}/m1-graph.json",
            tofile=f"{fixture_id}/generated-graph.json",
        )
    )
    raise AssertionError(f"Milestone 1 gold mismatch for {fixture_id}:\n{difference}")


def _assert_graph_integrity(
    result: RepositoryIndexResult,
    rendered: bytes,
    repository: Path,
) -> None:
    nodes = result.graph.nodes
    edges = result.graph.edges
    node_ids = [node.id for node in nodes]
    known_ids = set(node_ids)
    assert result.graph.schema_version == 1
    assert len(node_ids) == len(known_ids)
    assert len({edge.sort_key() for edge in edges}) == len(edges)
    assert all(edge.source_id in known_ids and edge.target_id in known_ids for edge in edges)
    assert nodes == tuple(sorted(nodes, key=lambda node: node.id))
    assert edges == tuple(sorted(edges, key=lambda edge: edge.sort_key()))
    assert result == parse_index_json(rendered.decode("utf-8"))
    assert canonical_index_json(result).encode("utf-8") == rendered
    assert result.esm_imports == ()
    assert result.esm_exports == ()
    assert result.commonjs_requires == ()
    assert result.commonjs_exports == ()
    assert result.esm_reexports == ()
    assert b'"esm_imports"' not in rendered
    assert b'"esm_exports"' not in rendered
    assert b'"commonjs_requires"' not in rendered
    assert b'"commonjs_exports"' not in rendered
    assert b'"esm_reexports"' not in rendered
    assert str(repository).encode("utf-8") not in rendered
    assert b"timestamp" not in rendered.lower()
    for node in nodes:
        if node.source_path is None:
            continue
        assert "\\" not in node.source_path
        assert not Path(node.source_path).is_absolute()
        assert ".." not in Path(node.source_path).parts


@pytest.mark.parametrize("fixture_id", SELECTED_FIXTURES)
def test_selected_fixture_matches_committed_gold_and_repeated_cli_bytes(
    tmp_path: Path,
    fixture_id: str,
) -> None:
    repository = _copy_fixture_repository(tmp_path, fixture_id)

    first_result = runner.invoke(app, ["index", str(repository)])
    first = _graph_bytes(repository)
    second_result = runner.invoke(app, ["index", str(repository)])
    second = _graph_bytes(repository)
    parsed = parse_index_json(second.decode("utf-8"))

    assert first_result.exit_code == second_result.exit_code == 0
    assert first == second
    _assert_matches_gold(fixture_id, _gold_bytes(fixture_id), second)
    _assert_graph_integrity(parsed, second, repository)
    expected_nodes, expected_edges, expected_imports, expected_diagnostics = EXPECTED_COUNTS[
        fixture_id
    ]
    assert len(parsed.graph.nodes) == expected_nodes
    assert len(parsed.graph.edges) == expected_edges
    assert len(parsed.imports) == expected_imports
    assert len(parsed.scanner_diagnostics) + len(parsed.extractor_diagnostics) == (
        expected_diagnostics
    )
    assert all(
        node.source_path is None or not node.source_path.startswith("repolens-out/")
        for node in parsed.graph.nodes
    )


def test_gold_mismatch_reports_fixture_and_unified_difference() -> None:
    with pytest.raises(AssertionError, match="Milestone 1 gold mismatch") as error:
        _assert_matches_gold("example", b'{"value":1}\n', b'{"value":2}\n')
    assert "--- example/m1-graph.json" in str(error.value)
    assert "+++ example/generated-graph.json" in str(error.value)


def test_python_fixture_matches_independently_authored_semantic_gold() -> None:
    result = parse_index_json(_gold_bytes("python_service").decode("utf-8"))
    nodes = {node.qualified_name: node for node in result.graph.nodes if node.qualified_name}

    assert {
        (node.kind, node.qualified_name, node.id, node.span)
        for node in result.graph.nodes
        if node.kind in {NodeKind.FUNCTION, NodeKind.METHOD}
    } == {
        (
            NodeKind.FUNCTION,
            "catalog.repository.get_item",
            "function:c665dfd833521467d47f",
            SourceSpan(start_line=4, end_line=5, start_column=0, end_column=25),
        ),
        (
            NodeKind.FUNCTION,
            "catalog.service.describe_item",
            "function:d0325ff43bc2acfcfa86",
            SourceSpan(start_line=4, end_line=6, start_column=0, end_column=28),
        ),
        (
            NodeKind.FUNCTION,
            "tests.test_service.test_describe_item",
            "function:f03422772f3febd343fe",
            SourceSpan(start_line=4, end_line=5, start_column=0, end_column=47),
        ),
    }
    assert [(fact.module, fact.imported_member, fact.source_path) for fact in result.imports] == [
        ("catalog.repository", "get_item", "catalog/service.py"),
        ("catalog.service", "describe_item", "tests/test_service.py"),
    ]
    contains = {(edge.source_id, edge.target_id) for edge in result.graph.edges}
    assert (nodes["catalog.service"].id, nodes["catalog.service.describe_item"].id) in contains


def test_markdown_fixture_matches_independently_authored_semantic_gold() -> None:
    result = parse_index_json(_gold_bytes("markdown_documented_project").decode("utf-8"))
    sections = {
        node.label: node for node in result.graph.nodes if node.kind is NodeKind.MARKDOWN_SECTION
    }
    documents = [node for node in result.graph.nodes if node.kind is NodeKind.MARKDOWN_DOCUMENT]

    assert len(documents) == 1
    assert documents[0].source_path == "docs/architecture.md"
    assert {
        (label, section.metadata["level"], section.span) for label, section in sections.items()
    } == {
        ("Architecture", 1, SourceSpan(start_line=1, end_line=1)),
        ("Rendering", 2, SourceSpan(start_line=5, end_line=5)),
        ("Limitations", 2, SourceSpan(start_line=13, end_line=13)),
    }
    assert [
        (fact.kind.value, fact.text, fact.target, fact.language, fact.span)
        for fact in result.markdown_facts
    ] == [
        ("inline_code", "build_report", None, None, SourceSpan(start_line=3, end_line=3)),
        ("link", "report.py", "../report.py", None, SourceSpan(start_line=3, end_line=3)),
        ("fenced_code", None, None, "python", SourceSpan(start_line=9, end_line=11)),
    ]
    parents = {edge.target_id: edge.source_id for edge in result.graph.edges}
    assert parents[sections["Rendering"].id] == sections["Architecture"].id
    assert parents[sections["Limitations"].id] == sections["Architecture"].id


def test_metadata_fixtures_match_independently_authored_semantic_gold() -> None:
    fullstack = parse_index_json(_gold_bytes("fullstack_fastapi_react").decode("utf-8"))
    typescript = parse_index_json(_gold_bytes("typescript_frontend").decode("utf-8"))

    assert [
        (fact.ecosystem.value, fact.field, fact.value) for fact in fullstack.metadata_facts
    ] == [
        ("node_package", "dependencies", json.loads('{"react":"fixture"}')),
        ("node_package", "name", "repolens-fullstack-fixture"),
        ("node_package", "private", True),
        ("python_project", "project.dependencies", ["fastapi"]),
        ("python_project", "project.name", "repolens-fullstack-fixture"),
        ("python_project", "project.version", "0.0.0"),
    ]
    assert [(fact.field, fact.value, fact.span) for fact in typescript.metadata_facts] == [
        ("compilerOptions.jsx", "react-jsx", None),
        ("compilerOptions.strict", True, None),
        ("include", ["src"], None),
    ]
    assert {node.source_path for node in typescript.graph.nodes if node.kind is NodeKind.FILE} == {
        "tsconfig.json"
    }


def test_controlled_filesystem_enumeration_order_does_not_change_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _copy_fixture_repository(tmp_path, "fullstack_fastapi_react")
    expected = canonical_index_json(index_repository(repository, RuntimeConfig()))
    original_walk = os.walk

    def reversed_walk(
        top: str | Path,
        topdown: bool = True,
        onerror: Callable[[OSError], None] | None = None,
        followlinks: bool = False,
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        for current, directories, filenames in original_walk(
            top,
            topdown=topdown,
            onerror=onerror,
            followlinks=followlinks,
        ):
            directories.reverse()
            filenames.reverse()
            yield current, directories, filenames

    monkeypatch.setattr(os, "walk", reversed_walk)
    actual = canonical_index_json(index_repository(repository, RuntimeConfig()))

    assert actual == expected


def test_indexing_declarations_and_code_never_executes_or_accesses_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    sentinel = repository / "executed.txt"
    (repository / "danger.py").write_text(
        f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('python executed')\n",
        encoding="utf-8",
    )
    (repository / "README.md").write_text(
        f"```python\nPath({str(sentinel)!r}).write_text('fence executed')\n```\n",
        encoding="utf-8",
    )
    (repository / "package.json").write_text(
        json.dumps({"scripts": {"build": f"echo script > {sentinel}"}}),
        encoding="utf-8",
    )
    (repository / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="danger:backend"\n',
        encoding="utf-8",
    )

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"external execution/network attempted: {args!r} {kwargs!r}")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)

    result = index_repository(repository, RuntimeConfig())

    assert not sentinel.exists()
    assert result.extractor_diagnostics == ()
    assert {fact.field for fact in result.metadata_facts} == {
        "build-system.build-backend",
        "build-system.requires",
        "scripts",
    }
    assert len(result.markdown_facts) == 1


def test_nonfatal_diagnostics_preserve_partial_graph_and_cli_success(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "broken.py").write_text(")", encoding="utf-8")
    (repository / "package.json").write_text("{", encoding="utf-8")
    (repository / "valid.py").write_text("def kept():\n    pass\n", encoding="utf-8")

    first = runner.invoke(app, ["index", str(repository)])
    first_bytes = _graph_bytes(repository)
    second = runner.invoke(app, ["index", str(repository)])
    second_bytes = _graph_bytes(repository)
    parsed = parse_index_json(second_bytes.decode("utf-8"))

    assert first.exit_code == second.exit_code == 0
    assert first_bytes == second_bytes
    assert parsed.extractor_diagnostics == (
        "metadata_parse_error:package.json:json",
        "python_syntax_error:broken.py:1:0",
    )
    assert any(node.qualified_name == "valid.kept" for node in parsed.graph.nodes)
    assert any(node.source_path == "broken.py" for node in parsed.graph.nodes)
    assert "warnings=2" in second.output


def test_fatal_invalid_root_remains_nonzero_without_output(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    result = runner.invoke(app, ["index", str(missing)])

    assert result.exit_code == 2
    assert not (missing / "repolens-out" / "graph.json").exists()
