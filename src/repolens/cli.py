"""RepoLens command-line scaffold."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from repolens import __version__
from repolens.evaluation.validators import validate_harness

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
def index(path: Path) -> None:
    """Index a repository (Milestone 1+)."""

    _unfinished("index", 1)


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
