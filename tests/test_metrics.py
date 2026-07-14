from __future__ import annotations

import pytest

from repolens.evaluation.metrics import accuracy, precision_recall_f1, set_metrics


def test_evaluation_metric_calculations() -> None:
    result = precision_recall_f1(true_positives=2, false_positives=1, false_negatives=2)
    assert result.precision == pytest.approx(2 / 3)
    assert result.recall == pytest.approx(1 / 2)
    assert result.f1 == pytest.approx(4 / 7)


def test_set_metrics_deduplicates_inputs() -> None:
    result = set_metrics(["a", "a", "b"], ["a", "c"])
    assert (result.true_positives, result.false_positives, result.false_negatives) == (1, 1, 1)


def test_empty_metric_semantics_and_invalid_counts() -> None:
    assert set_metrics([], []).f1 == 1.0
    assert accuracy(correct=0, total=0) == 1.0
    with pytest.raises(ValueError, match="cannot be negative"):
        precision_recall_f1(true_positives=-1, false_positives=0, false_negatives=0)
    with pytest.raises(ValueError, match="0 <= correct <= total"):
        accuracy(correct=2, total=1)
