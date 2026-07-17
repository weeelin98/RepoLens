"""Canonical graph serialization available before graph construction exists."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from repolens.indexer import RepositoryIndexResult
from repolens.models import GraphSnapshot


def _ordered_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _ordered_json(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_ordered_json(item) for item in value]
    return value


def _canonical_model_json(model: BaseModel) -> str:
    payload = model.model_dump(mode="json", exclude_none=True)
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


def canonical_graph_json(graph: GraphSnapshot) -> str:
    """Serialize a normalized graph to byte-stable JSON plus a final newline."""

    return _canonical_model_json(graph)


def parse_graph_json(value: str) -> GraphSnapshot:
    """Validate a serialized graph snapshot."""

    return GraphSnapshot.model_validate_json(value)


def canonical_index_json(result: RepositoryIndexResult) -> str:
    """Serialize a complete repository index to canonical graph.json text."""

    return _canonical_model_json(result)


def parse_index_json(value: str) -> RepositoryIndexResult:
    """Validate a serialized complete repository index."""

    return RepositoryIndexResult.model_validate_json(value)
