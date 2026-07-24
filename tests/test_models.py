from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from repolens.extractors import JavaScriptCallKind, UnresolvedJavaScriptCallFact
from repolens.graph.serialization import (
    canonical_graph_json,
    canonical_index_json,
    parse_graph_json,
    parse_index_json,
)
from repolens.indexer import RepositoryIndexResult
from repolens.models import (
    EdgeKind,
    EvidenceKind,
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    NodeKind,
    SourceSpan,
)


def node(node_id: str) -> GraphNode:
    return GraphNode(id=node_id, kind=NodeKind.FUNCTION, label=node_id)


def test_graph_model_validation_rejects_missing_edge_endpoint() -> None:
    edge = GraphEdge(
        source_id="a",
        target_id="missing",
        relation=EdgeKind.CALLS,
        evidence_kind=EvidenceKind.SYNTAX_DIRECT,
        confidence=1.0,
    )
    with pytest.raises(ValidationError, match="missing"):
        GraphSnapshot(nodes=(node("a"),), edges=(edge,))


def test_graph_json_compatible_round_trip() -> None:
    graph = GraphSnapshot(
        nodes=(node("b"), node("a")),
        edges=(
            GraphEdge(
                source_id="a",
                target_id="b",
                relation=EdgeKind.CALLS,
                evidence_kind=EvidenceKind.RESOLVER_DERIVED,
                confidence=0.9,
                resolver_notes="resolved local name",
            ),
        ),
        metadata={"languages": ["python"], "counts": {"files": 1}},
    )
    serialized = canonical_graph_json(graph)
    parsed = parse_graph_json(serialized)

    assert parsed == graph
    assert json.loads(serialized)["nodes"][0]["id"] == "a"
    assert serialized.endswith("\n")


def test_deterministic_sorting_and_normalization() -> None:
    forward = GraphSnapshot(nodes=(node("b"), node("a")), metadata={"z": 1, "a": 2})
    reverse = GraphSnapshot(nodes=(node("a"), node("b")), metadata={"a": 2, "z": 1})
    assert canonical_graph_json(forward) == canonical_graph_json(reverse)


def test_complete_index_json_round_trip_is_canonical() -> None:
    result = RepositoryIndexResult(
        graph=GraphSnapshot(nodes=(node("b"), node("a"))),
        extractor_diagnostics=("z-warning", "a-warning"),
    )

    serialized = canonical_index_json(result)
    parsed = parse_index_json(serialized)

    assert parsed == result
    assert serialized.startswith('{"extractor_diagnostics"')
    assert json.loads(serialized)["graph"]["nodes"][0]["id"] == "a"
    assert json.loads(serialized)["extractor_diagnostics"] == ["a-warning", "z-warning"]
    assert serialized.endswith("\n")


def test_edge_evidence_validation() -> None:
    with pytest.raises(ValidationError, match=r"confidence 1\.0"):
        GraphEdge(
            source_id="a",
            target_id="b",
            relation=EdgeKind.CALLS,
            evidence_kind=EvidenceKind.SYNTAX_DIRECT,
            confidence=0.9,
        )
    with pytest.raises(ValidationError, match="resolver_notes"):
        GraphEdge(
            source_id="a",
            target_id="b",
            relation=EdgeKind.CALLS,
            evidence_kind=EvidenceKind.AMBIGUOUS_UNRESOLVED,
            confidence=0.2,
        )
    with pytest.raises(ValidationError, match="must not be represented as certain"):
        GraphEdge(
            source_id="a",
            target_id="b",
            relation=EdgeKind.CALLS,
            evidence_kind=EvidenceKind.HEURISTIC,
            confidence=1.0,
        )


def test_source_span_validation() -> None:
    with pytest.raises(ValidationError, match="end_line"):
        SourceSpan(start_line=4, end_line=3)


def test_metadata_rejects_non_json_values() -> None:
    with pytest.raises(ValidationError, match="JSON-compatible"):
        GraphNode(id="a", kind=NodeKind.FILE, label="a", metadata={"bad": {1, 2}})


def test_m21b_node_kinds_are_additive_without_graph_schema_change() -> None:
    graph = GraphSnapshot(
        nodes=(
            GraphNode(id="interface", kind=NodeKind.INTERFACE, label="Interface"),
            GraphNode(id="type", kind=NodeKind.TYPE_ALIAS, label="Alias"),
            GraphNode(id="enum", kind=NodeKind.ENUM, label="Enum"),
        )
    )

    payload = json.loads(canonical_graph_json(graph))

    assert graph.schema_version == 1
    assert {item["kind"] for item in payload["nodes"]} == {
        "interface",
        "type_alias",
        "enum",
    }


def test_m22b_call_facts_round_trip_outside_the_unchanged_graph_schema() -> None:
    owner = GraphNode(
        id="module:owner",
        kind=NodeKind.MODULE,
        label="module",
        source_path="module.ts",
        qualified_name="module",
    )
    fact = UnresolvedJavaScriptCallFact(
        kind=JavaScriptCallKind.MEMBER,
        callee="client.load",
        enclosing_id=owner.id,
        source_path="module.ts",
        span=SourceSpan(
            start_line=2,
            end_line=2,
            start_column=0,
            end_column=13,
        ),
    )
    result = RepositoryIndexResult(
        graph=GraphSnapshot(nodes=(owner,)),
        javascript_calls=(fact,),
    )
    rendered = canonical_index_json(result)

    assert parse_index_json(rendered) == result
    assert result.graph.schema_version == 1
    assert json.loads(rendered)["javascript_calls"][0]["callee"] == "client.load"
    assert all(edge.relation is not EdgeKind.CALLS for edge in result.graph.edges)
