from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from repolens.evaluation.schemas import DiffCase, GoldQuestion, HarnessManifest
from repolens.evaluation.validators import validate_harness

PROJECT_ROOT = Path(__file__).parents[1]


def test_harness_manifest_validation() -> None:
    manifest = HarnessManifest.model_validate_json(
        (PROJECT_ROOT / "harness/fixtures/python_service/manifest.json").read_text()
    )
    assert manifest.fixture_id == "python_service"
    with pytest.raises(ValidationError, match="safe relative"):
        HarnessManifest(
            fixture_id="bad",
            description="bad path",
            languages=("python",),
            repository="../escape",
            gold="gold.json",
            questions="questions.jsonl",
            diff_cases=("diff.json",),
        )


def test_gold_question_validation() -> None:
    question_line = (
        (PROJECT_ROOT / "harness/fixtures/python_service/questions.jsonl").read_text().strip()
    )
    question = GoldQuestion.model_validate_json(question_line)
    assert question.maximum_context_tokens == 500
    with pytest.raises(ValidationError, match="greater than 0"):
        GoldQuestion(
            id="bad",
            category="test",
            question="bad budget",
            maximum_context_tokens=0,
        )


def test_diff_case_validation() -> None:
    path = PROJECT_ROOT / "harness/fixtures/python_service/diffs/service_change.json"
    case = DiffCase.model_validate_json(path.read_text())
    assert case.expected_affected_symbol_ids[-1] == "py:test:test_describe_item"
    with pytest.raises(ValidationError):
        DiffCase(
            id="bad",
            git_range="a..b",
            patch_file="change.patch",
            changed_paths=(),
            expected_changed_symbol_ids=("node",),
            expected_affected_symbol_ids=("node",),
        )


def test_all_harness_fixtures_validate() -> None:
    report = validate_harness(PROJECT_ROOT / "harness")
    assert report.errors == ()
    assert report.fixture_count == 5
    assert report.question_count == 5
    assert report.diff_case_count == 5
