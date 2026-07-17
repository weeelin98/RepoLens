"""RepoLens command-line scaffold."""

from __future__ import annotations

import os
import sys
from contextlib import suppress
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from repolens import __version__
from repolens.config import RuntimeConfig
from repolens.evaluation.validators import validate_harness
from repolens.graph.serialization import canonical_index_json
from repolens.indexer import index_repository
from repolens.models import NodeKind

app = typer.Typer(
    name="repolens",
    help="Compile repositories into evidence-backed context for coding agents.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the RepoLens version.",
        is_eager=True,
    ),
) -> None:
    if version:
        typer.echo(f"repolens {__version__}")
        raise typer.Exit()


def _unfinished(command: str, milestone: int) -> None:
    typer.echo(
        f"Error: '{command}' is not implemented in Milestone 0; target: Milestone {milestone}.",
        err=True,
    )
    raise typer.Exit(code=2)


def _fatal_error(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)


def _output_directory(repository_root: Path, config: RuntimeConfig) -> Path:
    if config.output_directory.is_absolute():
        return config.output_directory
    return repository_root / config.output_directory


def _atomic_write(path: Path, value: str) -> None:
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    except OSError:
        with suppress(OSError):
            temporary_path.unlink(missing_ok=True)
        raise


@app.command()
def doctor() -> None:
    """Check the current runtime without reading or changing a target repository."""

    python_ok = sys.version_info >= (3, 11)
    typer.echo("RepoLens doctor")
    typer.echo(
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}: "
        + ("ok" if python_ok else "requires 3.11+")
    )
    typer.echo(f"Package {__version__}: ok")
    typer.echo("Network required: no")
    if not python_ok:
        raise typer.Exit(code=1)


@app.command("harness-smoke")
def harness_smoke(
    harness: Annotated[Path, typer.Argument(exists=True, file_okay=False)] = Path("harness"),
) -> None:
    """Validate every synthetic corpus and gold-data schema."""

    report = validate_harness(harness)
    if report.errors:
        for error in report.errors:
            typer.echo(f"ERROR {error}", err=True)
        raise typer.Exit(code=1)
    typer.echo(
        "Harness valid: "
        f"{report.fixture_count} fixtures, {report.question_count} questions, "
        f"{report.diff_case_count} diff cases"
    )


@app.command()
def index(
    path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=False,
        ),
    ],
) -> None:
    """Index a repository and atomically write its deterministic graph.json."""

    config = RuntimeConfig()
    try:
        result = index_repository(path, config)
    except Exception:
        _fatal_error("repository indexing failed")

    fatal_diagnostic = next(
        (diagnostic for diagnostic in result.scanner_diagnostics if diagnostic.path is None),
        None,
    )
    if fatal_diagnostic is not None:
        _fatal_error(fatal_diagnostic.message)

    resolved_root = path.resolve()
    output_directory = _output_directory(resolved_root, config)
    try:
        output_directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        _fatal_error("could not create output directory")

    output_path = output_directory / "graph.json"
    try:
        serialized = canonical_index_json(result)
        _atomic_write(output_path, serialized)
    except OSError:
        _fatal_error("could not write graph.json")
    except Exception:
        _fatal_error("could not serialize graph.json")

    file_count = sum(node.kind is NodeKind.FILE for node in result.graph.nodes)
    diagnostic_count = len(result.scanner_diagnostics) + len(result.extractor_diagnostics)
    display_output = (
        output_path
        if config.output_directory.is_absolute()
        else path / config.output_directory / "graph.json"
    )
    typer.echo(
        f"Indexed {path}: files={file_count}, nodes={len(result.graph.nodes)}, "
        f"edges={len(result.graph.edges)}, "
        f"imports={len(result.imports) + len(result.esm_imports)}, "
        f"warnings={diagnostic_count}; graph.json={display_output}"
    )


@app.command()
def overview() -> None:
    _unfinished("overview", 3)


@app.command()
def find(symbol: str) -> None:
    _unfinished("find", 5)


@app.command()
def callers(symbol: str) -> None:
    _unfinished("callers", 5)


@app.command()
def callees(symbol: str) -> None:
    _unfinished("callees", 5)


@app.command("path")
def dependency_path(source: str, target: str) -> None:
    _unfinished("path", 5)


@app.command()
def query(
    question: str,
    budget: int = typer.Option(8_000, "--budget", min=1),
) -> None:
    _unfinished("query", 5)


@app.command()
def impact(git_range: str = typer.Option(..., "--diff")) -> None:
    _unfinished("impact", 5)


@app.command("eval")
def evaluate() -> None:
    _unfinished("eval", 6)


if __name__ == "__main__":
    app()
