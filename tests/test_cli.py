from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from repolens.cli import app

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[1]


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


def test_unimplemented_command_fails_explicitly() -> None:
    result = runner.invoke(app, ["index", "."])
    assert result.exit_code == 2
    assert "not implemented in Milestone 0" in result.output
    assert "target: Milestone 1" in result.output
