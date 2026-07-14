"""Baseline contracts; execution begins after query evaluation exists."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RipgrepBaseline:
    """A reproducible baseline query definition, not an unmeasured performance claim."""

    question_id: str
    patterns: tuple[str, ...]
    explanation: str
