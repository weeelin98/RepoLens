from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import repolens.cli as cli_module
from repolens.cli import app
from repolens.config import RuntimeConfig
from repolens.graph.serialization import parse_index_json

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[1]


def write_file(root: Path, relative_path: str, content: str = "") -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def graph_path(repository: Path) -> Path:
    return repository / "repolens-out" / "graph.json"


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "repolens 0.1.0" in result.output


def test_cli_doctor_behavior() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Package 0.1.0: ok" in result.output
    assert "Network required: no" in result.output


def test_cli_harness_smoke() -> None:
    result = runner.invoke(app, ["harness-smoke", str(PROJECT_ROOT / "harness")])
    assert result.exit_code == 0
    assert "5 fixtures, 5 questions, 5 diff cases" in result.output


def test_index_empty_repository_creates_default_graph_and_reports_counts(tmp_path: Path) -> None:
    result = runner.invoke(app, ["index", str(tmp_path)])

    output = graph_path(tmp_path)
    assert result.exit_code == 0
    assert output.is_file()
    parsed = parse_index_json(output.read_text(encoding="utf-8"))
    assert len(parsed.graph.nodes) == 1
    assert parsed.graph.edges == ()
    assert "files=0, nodes=1, edges=0, imports=0, warnings=0" in result.output
    assert str(output) in result.output


def test_index_serializes_python_imports_markdown_facts_and_ignores(tmp_path: Path) -> None:
    write_file(tmp_path, ".gitignore", "ignored.py\n")
    write_file(tmp_path, "app.py", "import os\n\ndef load():\n    pass\n")
    write_file(
        tmp_path,
        "README.md",
        "# Guide\n\nUse [`load`](app.py).\n\n```python\nload()\n```\n",
    )
    write_file(tmp_path, "ignored.py", "def hidden():\n    pass\n")

    result = runner.invoke(app, ["index", str(tmp_path)])
    serialized = graph_path(tmp_path).read_text(encoding="utf-8")
    payload = json.loads(serialized)
    source_paths = {node.get("source_path") for node in payload["graph"]["nodes"]}
    qualified_names = {node.get("qualified_name") for node in payload["graph"]["nodes"]}

    assert result.exit_code == 0
    assert "app.load" in qualified_names
    assert payload["imports"][0]["module"] == "os"
    assert "README.md" in source_paths
    assert "README.md/Guide" in qualified_names
    assert "ignored.py" not in source_paths
    assert [fact["kind"] for fact in payload["markdown_facts"]] == [
        "link",
        "inline_code",
        "fenced_code",
    ]
    assert payload["markdown_facts"][0]["target"] == "app.py"
    assert payload["markdown_facts"][2]["language"] == "python"
    assert str(tmp_path) not in serialized
    assert "def load" not in serialized
    assert serialized.endswith("\n")
    assert "files=2, nodes=7, edges=6, imports=1, warnings=0" in result.output


def test_repeated_markdown_index_is_byte_identical_without_absolute_paths(tmp_path: Path) -> None:
    write_file(tmp_path, "docs/guide.md", "# Guide\n\nSee [API](../api.md). Use `load`.\n")

    first_result = runner.invoke(app, ["index", str(tmp_path)])
    first = graph_path(tmp_path).read_bytes()
    second_result = runner.invoke(app, ["index", str(tmp_path)])
    second = graph_path(tmp_path).read_bytes()

    assert first_result.exit_code == second_result.exit_code == 0
    assert first == second
    assert str(tmp_path).encode() not in second
    assert b'"markdown_facts"' in second


def test_index_serializes_metadata_deterministically_without_executing_scripts(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "executed.txt"
    inert_script = "echo executed > executed.txt"
    write_file(tmp_path, "pyproject.toml", '[project]\nname = "python-app"\n')
    write_file(
        tmp_path,
        "package.json",
        json.dumps(
            {
                "name": "web-app",
                "scripts": {"build": inert_script},
                "dependencies": {"react": "^19"},
            }
        ),
    )
    write_file(
        tmp_path,
        "tsconfig.json",
        '{// comment\n"extends":"./base.json","compilerOptions":{"strict":true,},}',
    )
    write_file(tmp_path, "secret.json", '{"token":"not-indexed"}')
    write_file(tmp_path, "config.toml", 'token = "not-indexed"')

    first_result = runner.invoke(app, ["index", str(tmp_path)])
    first = graph_path(tmp_path).read_bytes()
    second_result = runner.invoke(app, ["index", str(tmp_path)])
    second = graph_path(tmp_path).read_bytes()
    payload = json.loads(second)

    assert first_result.exit_code == second_result.exit_code == 0
    assert first == second
    assert not sentinel.exists()
    assert next(
        fact["value"]
        for fact in payload["metadata_facts"]
        if fact["source_path"] == "package.json" and fact["field"] == "scripts"
    ) == {"build": inert_script}
    assert {fact["source_path"] for fact in payload["metadata_facts"]} == {
        "package.json",
        "pyproject.toml",
        "tsconfig.json",
    }
    assert "secret.json" not in second.decode()
    assert "config.toml" not in second.decode()
    assert str(tmp_path).encode() not in second


def test_malformed_metadata_is_a_nonfatal_serialized_warning(tmp_path: Path) -> None:
    write_file(tmp_path, "package.json", "{")

    result = runner.invoke(app, ["index", str(tmp_path)])
    parsed = parse_index_json(graph_path(tmp_path).read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert parsed.extractor_diagnostics == ("metadata_parse_error:package.json:json",)
    assert parsed.metadata_facts == ()
    assert "warnings=1" in result.output


def test_index_nonfatal_syntax_diagnostic_writes_graph_and_succeeds(tmp_path: Path) -> None:
    write_file(tmp_path, "broken.py", ")")

    result = runner.invoke(app, ["index", str(tmp_path)])
    parsed = parse_index_json(graph_path(tmp_path).read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert parsed.extractor_diagnostics == ("python_syntax_error:broken.py:1:0",)
    assert any(node.source_path == "broken.py" for node in parsed.graph.nodes)
    assert "warnings=1" in result.output


def test_index_nonfatal_scanner_diagnostic_is_serialized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_file(tmp_path, "large.py", "too large")
    monkeypatch.setattr(
        cli_module,
        "RuntimeConfig",
        lambda: RuntimeConfig(maximum_file_bytes=1),
    )

    result = runner.invoke(app, ["index", str(tmp_path)])
    parsed = parse_index_json(graph_path(tmp_path).read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert parsed.scanner_diagnostics[0].path == "large.py"
    assert parsed.scanner_diagnostics[0].code.value == "file_too_large"
    assert "warnings=1" in result.output


def test_repeated_index_is_byte_identical_and_prunes_preserved_output_files(
    tmp_path: Path,
) -> None:
    write_file(tmp_path, "module.py", "def load():\n    pass\n")

    first_result = runner.invoke(app, ["index", str(tmp_path)])
    first = graph_path(tmp_path).read_bytes()
    preserved = write_file(tmp_path, "repolens-out/preserved.py", "def output_only():\n    pass\n")
    second_result = runner.invoke(app, ["index", str(tmp_path)])
    second = graph_path(tmp_path).read_bytes()
    parsed = parse_index_json(second.decode("utf-8"))

    assert first_result.exit_code == second_result.exit_code == 0
    assert first == second
    assert preserved.is_file()
    assert all(node.source_path != "repolens-out/preserved.py" for node in parsed.graph.nodes)


@pytest.mark.parametrize("root_kind", ["missing", "file"])
def test_index_invalid_repository_argument_exits_nonzero(
    tmp_path: Path,
    root_kind: str,
) -> None:
    repository = tmp_path / root_kind
    if root_kind == "file":
        repository.write_text("not a directory", encoding="utf-8")

    result = runner.invoke(app, ["index", str(repository)])

    assert result.exit_code == 2
    assert not graph_path(repository).exists()


def test_index_output_directory_creation_failure_is_fatal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_mkdir = Path.mkdir

    def selective_mkdir(
        path: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        if path.name == "repolens-out":
            raise PermissionError
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", selective_mkdir)
    result = runner.invoke(app, ["index", str(tmp_path)])

    assert result.exit_code == 1
    assert "Error: could not create output directory" in result.output
    assert "Indexed" not in result.output


def test_index_atomic_replace_failure_is_fatal_and_cleans_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_replace = Path.replace

    def selective_replace(path: Path, target: Path) -> Path:
        if path.name == ".graph.json.tmp":
            raise PermissionError
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", selective_replace)
    result = runner.invoke(app, ["index", str(tmp_path)])

    assert result.exit_code == 1
    assert "Error: could not write graph.json" in result.output
    assert "Indexed" not in result.output
    assert not graph_path(tmp_path).exists()
    assert not (tmp_path / "repolens-out" / ".graph.json.tmp").exists()


def test_index_unexpected_pipeline_failure_is_concise_and_fatal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_index(path: Path, config: RuntimeConfig) -> None:
        raise RuntimeError("internal detail")

    monkeypatch.setattr(cli_module, "index_repository", failed_index)
    result = runner.invoke(app, ["index", str(tmp_path)])

    assert result.exit_code == 1
    assert "Error: repository indexing failed" in result.output
    assert "internal detail" not in result.output
    assert "Indexed" not in result.output


def test_index_never_executes_target_python(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed.txt"
    write_file(
        tmp_path,
        "danger.py",
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('executed', encoding='utf-8')\n",
    )

    result = runner.invoke(app, ["index", str(tmp_path)])

    assert result.exit_code == 0
    assert not sentinel.exists()


def test_index_accepts_relative_path_without_changing_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    write_file(repository, "module.py", "")
    monkeypatch.chdir(tmp_path)
    starting_directory = Path.cwd()

    result = runner.invoke(app, ["index", "repository"])

    assert result.exit_code == 0
    assert Path.cwd() == starting_directory
    assert graph_path(repository).is_file()
    display_path = Path("repository") / "repolens-out" / "graph.json"
    assert f"graph.json={display_path}" in result.output


def test_output_directory_resolution_supports_relative_and_absolute_paths(tmp_path: Path) -> None:
    relative = cli_module._output_directory(
        tmp_path,
        RuntimeConfig(output_directory=Path("custom/output")),
    )
    absolute_path = (tmp_path.parent / "absolute-output").resolve()
    absolute = cli_module._output_directory(
        tmp_path,
        RuntimeConfig(output_directory=absolute_path),
    )

    assert relative == tmp_path / "custom/output"
    assert absolute == absolute_path


def test_index_serializes_js_ts_facts_repeatedly_without_paths_or_execution(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "executed.txt"
    write_file(
        tmp_path,
        "src/app.js",
        "import primary, { request as send } from './client.js';\n"
        f"globalThis.writeFile?.({str(sentinel)!r}, 'executed');\n"
        "export const load = () => send();\n",
    )
    write_file(
        tmp_path,
        "src/service.ts",
        "export default class Service { async run(): Promise<void> {} }\n",
    )
    write_file(
        tmp_path,
        "src/ignored.tsx",
        "export const Component = () => <main />;\n",
    )

    first_result = runner.invoke(app, ["index", str(tmp_path)])
    first = graph_path(tmp_path).read_bytes()
    second_result = runner.invoke(app, ["index", str(tmp_path)])
    second = graph_path(tmp_path).read_bytes()
    payload = json.loads(second)
    parsed = parse_index_json(second.decode("utf-8"))

    assert first_result.exit_code == second_result.exit_code == 0
    assert first == second
    assert "imports=2" in second_result.output
    assert [fact["kind"] for fact in payload["esm_imports"]] == ["default", "named"]
    assert [fact["exported_name"] for fact in payload["esm_exports"]] == [
        "load",
        "default",
    ]
    assert {node.qualified_name for node in parsed.graph.nodes} >= {
        "src.app",
        "src.app.load",
        "src.service",
        "src.service.Service",
        "src.service.Service.run",
    }
    assert all(node.source_path != "src/ignored.tsx" for node in parsed.graph.nodes)
    assert str(tmp_path).encode() not in second
    assert not sentinel.exists()


def test_index_malformed_javascript_serializes_conservative_partial_result(
    tmp_path: Path,
) -> None:
    write_file(
        tmp_path,
        "broken.js",
        "function before() {}\n}\nfunction after() {}\n",
    )

    result = runner.invoke(app, ["index", str(tmp_path)])
    parsed = parse_index_json(graph_path(tmp_path).read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert parsed.extractor_diagnostics == ("tree_sitter_syntax_error:broken.js:2:0",)
    assert {node.qualified_name for node in parsed.graph.nodes} >= {
        "broken",
        "broken.before",
        "broken.after",
    }
    assert "warnings=1" in result.output


def test_index_serializes_m21b_channels_and_counts_commonjs_requires(tmp_path: Path) -> None:
    write_file(
        tmp_path,
        "module.js",
        "require('setup');\n"
        "const value = require('pkg');\n"
        "module.exports = value;\n"
        "export { named } from 'esm';\n",
    )

    first_result = runner.invoke(app, ["index", str(tmp_path)])
    first = graph_path(tmp_path).read_bytes()
    second_result = runner.invoke(app, ["index", str(tmp_path)])
    second = graph_path(tmp_path).read_bytes()
    payload = json.loads(second)

    assert first_result.exit_code == second_result.exit_code == 0
    assert first == second
    assert "imports=2" in second_result.output
    assert [fact["kind"] for fact in payload["commonjs_requires"]] == [
        "side_effect",
        "binding",
    ]
    assert payload["commonjs_exports"][0]["kind"] == "module_exports"
    assert payload["esm_reexports"][0]["exported_name"] == "named"
    assert str(tmp_path).encode() not in second
