"""Pure, dependency-free evaluation metric functions."""

from __future__ import annotations

from collections.abc import Collection, Hashable
from dataclasses import dataclass
from typing import TypeVar

Item = TypeVar("Item", bound=Hashable)


@dataclass(frozen=True)
class MetricResult:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


def precision_recall_f1(
    *, true_positives: int, false_positives: int, false_negatives: int
) -> MetricResult:
    """Calculate precision/recall/F1 with explicit empty-set semantics.

    If both predicted and expected sets are empty, all three scores are 1.0. If only the
    prediction or expectation is empty, the affected ratio is 0.0.
    """

    if min(true_positives, false_positives, false_negatives) < 0:
        raise ValueError("metric counts cannot be negative")
    predicted = true_positives + false_positives
    expected = true_positives + false_negatives
    precision = true_positives / predicted if predicted else (1.0 if expected == 0 else 0.0)
    recall = true_positives / expected if expected else (1.0 if predicted == 0 else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return MetricResult(
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def set_metrics(predicted: Collection[Item], expected: Collection[Item]) -> MetricResult:
    predicted_set = set(predicted)
    expected_set = set(expected)
    return precision_recall_f1(
        true_positives=len(predicted_set & expected_set),
        false_positives=len(predicted_set - expected_set),
        false_negatives=len(expected_set - predicted_set),
    )


def accuracy(*, correct: int, total: int) -> float:
    if correct < 0 or total < 0 or correct > total:
        raise ValueError("accuracy counts must satisfy 0 <= correct <= total")
    return correct / total if total else 1.0


def recall_at_least_one(predicted: Collection[Item], expected: Collection[Item]) -> float:
    """Return 1 when any expected item is found, with empty/empty treated as correct."""

    predicted_set = set(predicted)
    expected_set = set(expected)
    if not expected_set:
        return 1.0 if not predicted_set else 0.0
    return float(bool(predicted_set & expected_set))
