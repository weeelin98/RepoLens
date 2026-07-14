"""Canonical graph serialization available before graph construction exists."""

from __future__ import annotations

import json
from typing import Any

from repolens.models import GraphSnapshot


def _ordered_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _ordered_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_ordered_json(item) for item in value]
    return value


def canonical_graph_json(graph: GraphSnapshot) -> str:
    """Serialize a normalized graph to byte-stable JSON plus a final newline."""

    payload = graph.model_dump(mode="json", exclude_none=True)
    return (
        json.dumps(
            _ordered_json(payload),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


def parse_graph_json(value: str) -> GraphSnapshot:
    """Validate a serialized graph snapshot."""

    return GraphSnapshot.model_validate_json(value)
