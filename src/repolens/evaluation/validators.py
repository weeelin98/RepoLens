"""Network-free validation for fixture manifests and gold files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from repolens.evaluation.schemas import DiffCase, GoldData, GoldQuestion, HarnessManifest

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True)
class HarnessValidationReport:
    fixture_count: int
    question_count: int
    diff_case_count: int
    errors: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _read_model(path: Path, model_type: type[ModelT]) -> ModelT:
    return model_type.model_validate_json(path.read_text(encoding="utf-8"))


def _safe_child(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError(f"fixture reference escapes its directory: {relative}")
    return candidate


def validate_harness(harness_root: Path) -> HarnessValidationReport:
    fixtures_root = harness_root / "fixtures"
    errors: list[str] = []
    question_count = 0
    diff_case_count = 0
    fixture_ids: set[str] = set()
    manifests = sorted(fixtures_root.glob("*/manifest.json")) if fixtures_root.is_dir() else []
    if not manifests:
        errors.append(f"no fixture manifests found under {fixtures_root}")

    for manifest_path in manifests:
        fixture_root = manifest_path.parent
        try:
            manifest = _read_model(manifest_path, HarnessManifest)
            assert isinstance(manifest, HarnessManifest)
            if manifest.fixture_id in fixture_ids:
                errors.append(f"{manifest_path}: duplicate fixture_id {manifest.fixture_id}")
            fixture_ids.add(manifest.fixture_id)

            repository = _safe_child(fixture_root, manifest.repository)
            if not repository.is_dir() or not any(path.is_file() for path in repository.rglob("*")):
                errors.append(f"{manifest_path}: repository must contain at least one file")

            gold_path = _safe_child(fixture_root, manifest.gold)
            gold = _read_model(gold_path, GoldData)
            assert isinstance(gold, GoldData)
            gold_ids = {node.id for node in gold.expected_nodes}

            questions_path = _safe_child(fixture_root, manifest.questions)
            question_ids: set[str] = set()
            for line_number, line in enumerate(
                questions_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not line.strip():
                    continue
                question = GoldQuestion.model_validate_json(line)
                question_count += 1
                if question.id in question_ids:
                    errors.append(f"{questions_path}:{line_number}: duplicate question id")
                question_ids.add(question.id)
                unknown = sorted(set(question.expected_node_ids) - gold_ids)
                if unknown:
                    errors.append(
                        f"{questions_path}:{line_number}: unknown expected node IDs: "
                        + ", ".join(unknown)
                    )

            for relative_diff in manifest.diff_cases:
                diff_path = _safe_child(fixture_root, relative_diff)
                diff_case = _read_model(diff_path, DiffCase)
                assert isinstance(diff_case, DiffCase)
                diff_case_count += 1
                patch_path = _safe_child(diff_path.parent, diff_case.patch_file)
                if not patch_path.is_file() or not patch_path.read_text(encoding="utf-8").strip():
                    errors.append(f"{diff_path}: patch_file must exist and be non-empty")
                expected_ids = set(diff_case.expected_changed_symbol_ids) | set(
                    diff_case.expected_affected_symbol_ids
                )
                unknown = sorted(expected_ids - gold_ids)
                if unknown:
                    errors.append(
                        f"{diff_path}: impact symbols absent from gold nodes: " + ", ".join(unknown)
                    )
        except (OSError, ValueError, ValidationError, json.JSONDecodeError) as error:
            errors.append(f"{manifest_path}: {error}")

    return HarnessValidationReport(
        fixture_count=len(manifests),
        question_count=question_count,
        diff_case_count=diff_case_count,
        errors=tuple(errors),
    )
