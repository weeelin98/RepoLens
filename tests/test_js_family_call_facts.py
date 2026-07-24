from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from repolens.config import RuntimeConfig
from repolens.extractors import (
    ExtractionResult,
    JavaScriptCallKind,
    JavaScriptTypeScriptExtractor,
    UnresolvedJavaScriptCallFact,
)
from repolens.graph.serialization import canonical_index_json, parse_index_json
from repolens.indexer import RepositoryIndexResult, index_repository
from repolens.models import EdgeKind, GraphNode, GraphSnapshot, NodeKind, SourceSpan

PROJECT_ROOT = Path(__file__).parents[1]


def _extract(source: str, path: str = "src/calls.ts") -> ExtractionResult:
    return JavaScriptTypeScriptExtractor().extract(Path(path), source)


def _node(result: ExtractionResult, qualified_name: str) -> GraphNode:
    return next(node for node in result.nodes if node.qualified_name == qualified_name)


def _callees(result: ExtractionResult) -> list[tuple[JavaScriptCallKind, str, bool]]:
    return [(fact.kind, fact.callee, fact.is_optional) for fact in result.javascript_calls]


def test_call_fact_contract_validates_shape_path_and_complete_sort_key() -> None:
    span = SourceSpan(start_line=2, end_line=2, start_column=2, end_column=8)
    identifier = UnresolvedJavaScriptCallFact(
        kind=JavaScriptCallKind.IDENTIFIER,
        callee="load",
        enclosing_id="function:owner",
        source_path=r"src\calls.ts",
        span=span,
    )
    member = UnresolvedJavaScriptCallFact(
        kind=JavaScriptCallKind.MEMBER,
        callee="client.tasks.load",
        enclosing_id="function:owner",
        is_optional=True,
        source_path="src/calls.ts",
        span=SourceSpan(start_line=3, end_line=4, start_column=2, end_column=4),
    )

    assert identifier.source_path == "src/calls.ts"
    assert identifier.is_optional is False
    assert identifier.sort_key() != member.sort_key()
    with pytest.raises(ValidationError, match="undotted"):
        UnresolvedJavaScriptCallFact(
            kind=JavaScriptCallKind.IDENTIFIER,
            callee="client.load",
            enclosing_id="function:owner",
            source_path="src/calls.ts",
            span=span,
        )
    with pytest.raises(ValidationError, match="dotted"):
        UnresolvedJavaScriptCallFact(
            kind=JavaScriptCallKind.MEMBER,
            callee="load",
            enclosing_id="function:owner",
            source_path="src/calls.ts",
            span=span,
        )
    for callee in ("load?.", "load()", "load<Result>", "client..load", " client.load"):
        with pytest.raises(ValidationError):
            UnresolvedJavaScriptCallFact(
                kind=JavaScriptCallKind.MEMBER,
                callee=callee,
                enclosing_id="function:owner",
                source_path="src/calls.ts",
                span=span,
            )
    with pytest.raises(ValidationError, match="repository-relative"):
        UnresolvedJavaScriptCallFact(
            kind=JavaScriptCallKind.IDENTIFIER,
            callee="load",
            enclosing_id="function:owner",
            source_path="C:/private/calls.ts",
            span=span,
        )


@pytest.mark.parametrize(
    ("path", "source", "expected"),
    [
        (
            "calls.js",
            "load(); api.load(); api.client.save(); this.flush(); super.flush();",
            [
                (JavaScriptCallKind.IDENTIFIER, "load", False),
                (JavaScriptCallKind.MEMBER, "api.load", False),
                (JavaScriptCallKind.MEMBER, "api.client.save", False),
                (JavaScriptCallKind.MEMBER, "this.flush", False),
                (JavaScriptCallKind.MEMBER, "super.flush", False),
            ],
        ),
        (
            "calls.jsx",
            "load(); api.load();",
            [
                (JavaScriptCallKind.IDENTIFIER, "load", False),
                (JavaScriptCallKind.MEMBER, "api.load", False),
            ],
        ),
        (
            "calls.ts",
            "load<Result>(); api.load<Result>();",
            [
                (JavaScriptCallKind.IDENTIFIER, "load", False),
                (JavaScriptCallKind.MEMBER, "api.load", False),
            ],
        ),
        (
            "calls.tsx",
            "load<Result>(); api.load<Result>();",
            [
                (JavaScriptCallKind.IDENTIFIER, "load", False),
                (JavaScriptCallKind.MEMBER, "api.load", False),
            ],
        ),
    ],
)
def test_supported_identifier_member_and_type_argument_calls(
    path: str,
    source: str,
    expected: list[tuple[JavaScriptCallKind, str, bool]],
) -> None:
    result = _extract(source, path)

    assert _callees(result) == expected
    module = next(node for node in result.nodes if node.kind is NodeKind.MODULE)
    assert {fact.enclosing_id for fact in result.javascript_calls} == {module.id}


@pytest.mark.parametrize("path", ["calls.js", "calls.jsx", "calls.ts", "calls.tsx"])
def test_optional_call_shapes_are_normalized_from_both_pinned_grammars(path: str) -> None:
    result = _extract(
        "fn?.(); api?.load(); api.load?.(); api?.client.load?.(); ordinary();",
        path,
    )

    assert _callees(result) == [
        (JavaScriptCallKind.IDENTIFIER, "fn", True),
        (JavaScriptCallKind.MEMBER, "api.load", True),
        (JavaScriptCallKind.MEMBER, "api.load", True),
        (JavaScriptCallKind.MEMBER, "api.client.load", True),
        (JavaScriptCallKind.IDENTIFIER, "ordinary", False),
    ]


def test_calls_preserve_occurrences_exact_spans_unicode_and_nested_order() -> None:
    result = _extract("  café();\nouter(inner());\nouter(inner());\n", "unicode.js")

    assert [(fact.callee, fact.span) for fact in result.javascript_calls] == [
        (
            "café",
            SourceSpan(start_line=1, end_line=1, start_column=2, end_column=9),
        ),
        (
            "outer",
            SourceSpan(start_line=2, end_line=2, start_column=0, end_column=14),
        ),
        (
            "inner",
            SourceSpan(start_line=2, end_line=2, start_column=6, end_column=13),
        ),
        (
            "outer",
            SourceSpan(start_line=3, end_line=3, start_column=0, end_column=14),
        ),
        (
            "inner",
            SourceSpan(start_line=3, end_line=3, start_column=6, end_column=13),
        ),
    ]


def test_nearest_supported_owner_callbacks_and_scope_barriers_are_exact() -> None:
    source = """
moduleCall();
function Outer() {
  direct();
  function Nested() { nested(); }
  const Arrow = () => { arrowCall(); invoke(() => callbackCall()); };
  invoke(function () { expressionCallback(); });
  invoke(() => { const HiddenArrow = () => hiddenNestedArrow(); });
  const HiddenExpression = function () { hiddenNamedExpression(); };
  function* HiddenGenerator() { hiddenGenerator(); }
}
class Service {
  method() { this.save(); }
  constructor() { hiddenConstructor(); }
  get value() { hiddenAccessor(); }
  field = hiddenField();
  static { hiddenStatic(); }
}
const object = { method() { hiddenObjectMethod(); } };
const HiddenClass = class { method() { hiddenClassExpression(); } };
export default () => hiddenAnonymousDefault();
""".lstrip()
    result = _extract(source, "owners.ts")
    by_callee = {fact.callee: fact for fact in result.javascript_calls}
    module = _node(result, "owners")
    outer = _node(result, "owners.Outer")
    nested = _node(result, "owners.Outer.Nested")
    arrow = _node(result, "owners.Outer.Arrow")
    method = _node(result, "owners.Service.method")

    assert by_callee["moduleCall"].enclosing_id == module.id
    assert by_callee["direct"].enclosing_id == outer.id
    assert by_callee["nested"].enclosing_id == nested.id
    assert by_callee["arrowCall"].enclosing_id == arrow.id
    assert [fact.enclosing_id for fact in result.javascript_calls if fact.callee == "invoke"] == [
        arrow.id,
        outer.id,
        outer.id,
    ]
    assert by_callee["callbackCall"].enclosing_id == arrow.id
    assert by_callee["expressionCallback"].enclosing_id == outer.id
    assert by_callee["this.save"].enclosing_id == method.id
    assert {
        "hiddenGenerator",
        "hiddenNestedArrow",
        "hiddenNamedExpression",
        "hiddenConstructor",
        "hiddenAccessor",
        "hiddenField",
        "hiddenStatic",
        "hiddenObjectMethod",
        "hiddenClassExpression",
        "hiddenAnonymousDefault",
    }.isdisjoint(by_callee)


def test_function_arrow_and_react_component_owners_use_actual_selected_nodes() -> None:
    source = """
import React, { useEffect } from "react";
export function Card() {
  useEffect(() => { loadProfile(); });
  return <main />;
}
export const Panel = () => {
  loadPanel();
  return <section />;
};
""".lstrip()
    result = _extract(source, "src/components.tsx")
    card = _node(result, "src.components.Card")
    panel = _node(result, "src.components.Panel")

    assert card.kind is panel.kind is NodeKind.REACT_COMPONENT
    owners = {fact.callee: fact.enclosing_id for fact in result.javascript_calls}
    assert owners["useEffect"] == owners["loadProfile"] == card.id
    assert owners["loadPanel"] == panel.id


def test_default_parameter_calls_use_their_supported_callable_owner() -> None:
    source = """
function FunctionOwner(value = functionDefault()) {}
const ArrowOwner = (value = arrowDefault()) => {};
class Service { method(value = methodDefault()) {} }
invoke((value = callbackDefault()) => value);
""".lstrip()
    result = _extract(source, "parameters.ts")
    function_owner = _node(result, "parameters.FunctionOwner")
    arrow_owner = _node(result, "parameters.ArrowOwner")
    method_owner = _node(result, "parameters.Service.method")
    module = _node(result, "parameters")
    owners = {fact.callee: fact.enclosing_id for fact in result.javascript_calls}

    assert owners["functionDefault"] == function_owner.id
    assert owners["arrowDefault"] == arrow_owner.id
    assert owners["methodDefault"] == method_owner.id
    assert owners["invoke"] == owners["callbackDefault"] == module.id


def test_unsupported_callees_are_omitted_but_eligible_nested_calls_survive() -> None:
    source = """
require("pkg");
require?.("pkg");
import("pkg");
new Constructor(innerNew());
tag`value`;
api["load"]();
api[key()]();
(parenthesized)();
factory()();
factory().run();
(condition ? left : right)();
const asserted = (candidate as Callable)();
candidate!();
@decorate()
class Decorated {}
class Private { #load() {} method() { this.#load(); } }
""".lstrip()
    result = _extract(source, "unsupported.ts")

    assert [fact.callee for fact in result.javascript_calls] == [
        "innerNew",
        "key",
        "factory",
        "factory",
    ]


def test_partial_tree_keeps_only_error_free_top_level_call_siblings() -> None:
    result = _extract("safe();\n}\nfunction kept() { nested(); }\n", "partial.js")

    assert [fact.callee for fact in result.javascript_calls] == ["safe", "nested"]
    assert result.diagnostics == ("tree_sitter_syntax_error:partial.js:2:0",)


def test_repository_validation_sorts_calls_and_rejects_invalid_owners() -> None:
    module = GraphNode(
        id="module:owner",
        kind=NodeKind.MODULE,
        label="calls",
        language="typescript",
        source_path="calls.ts",
        qualified_name="calls",
    )
    span = SourceSpan(start_line=1, end_line=1, start_column=0, end_column=6)
    fact = UnresolvedJavaScriptCallFact(
        kind=JavaScriptCallKind.IDENTIFIER,
        callee="load",
        enclosing_id=module.id,
        source_path="calls.ts",
        span=span,
    )
    later = fact.model_copy(
        update={
            "callee": "later",
            "span": SourceSpan(
                start_line=2,
                end_line=2,
                start_column=0,
                end_column=7,
            ),
        }
    )
    result = RepositoryIndexResult(
        graph=GraphSnapshot(nodes=(module,)),
        javascript_calls=(later, fact),
    )

    assert result.javascript_calls == (fact, later)
    rendered = canonical_index_json(result)
    assert parse_index_json(rendered) == result
    assert json.loads(rendered)["javascript_calls"][0]["callee"] == "load"

    wrong_kind = module.model_copy(update={"kind": NodeKind.FILE})
    with pytest.raises(ValidationError, match="allowed owner"):
        RepositoryIndexResult(
            graph=GraphSnapshot(nodes=(wrong_kind,)),
            javascript_calls=(fact,),
        )
    with pytest.raises(ValidationError, match="does not exist"):
        RepositoryIndexResult(
            graph=GraphSnapshot(nodes=(module,)),
            javascript_calls=(fact.model_copy(update={"enclosing_id": "missing"}),),
        )
    with pytest.raises(ValidationError, match="same source path"):
        RepositoryIndexResult(
            graph=GraphSnapshot(nodes=(module,)),
            javascript_calls=(fact.model_copy(update={"source_path": "other.ts"}),),
        )


def test_empty_call_channels_are_omitted_and_old_payloads_default_empty() -> None:
    extraction = ExtractionResult()
    rendered = canonical_index_json(RepositoryIndexResult(graph=GraphSnapshot()))
    parsed = parse_index_json(rendered)

    assert extraction.javascript_calls == ()
    assert '"javascript_calls"' not in rendered
    assert parsed.javascript_calls == ()


def test_indexing_is_deterministic_private_nonexecuting_and_adds_no_semantic_edges(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "executed.txt"
    source = (
        'import { writeFileSync } from "node:fs";\n'
        f"writeFileSync({str(sentinel)!r}, 'executed');\n"
        "api?.load();\n"
    )
    path = tmp_path / "src" / "calls.ts"
    path.parent.mkdir()
    path.write_text(source, encoding="utf-8")

    first = canonical_index_json(index_repository(tmp_path, RuntimeConfig()))
    second = canonical_index_json(index_repository(tmp_path, RuntimeConfig()))
    parsed = parse_index_json(second)

    assert first == second
    assert [fact.callee for fact in parsed.javascript_calls] == ["writeFileSync", "api.load"]
    assert not sentinel.exists()
    assert str(tmp_path.resolve()) not in second
    assert "timestamp" not in second.casefold()
    assert all(
        edge.relation
        not in {
            EdgeKind.CALLS,
            EdgeKind.IMPORTS,
            EdgeKind.EXPORTS,
            EdgeKind.INHERITS,
            EdgeKind.INVOKES_ENDPOINT,
        }
        for edge in parsed.graph.edges
    )


def test_m22b_typescript_frontend_partial_gold_matches_semantics_and_repeated_generation() -> None:
    fixture = PROJECT_ROOT / "harness" / "fixtures" / "typescript_frontend"
    repository = fixture / "repo"
    expected = (fixture / "m2-2b-graph.json").read_bytes()

    first = canonical_index_json(index_repository(repository, RuntimeConfig())).encode()
    second = canonical_index_json(index_repository(repository, RuntimeConfig())).encode()
    parsed = parse_index_json(expected.decode())
    profile_card = next(
        node for node in parsed.graph.nodes if node.qualified_name == "src.ProfileCard.ProfileCard"
    )
    load_profile = next(
        fact
        for fact in parsed.javascript_calls
        if fact.source_path == "src/ProfileCard.tsx" and fact.callee == "loadProfile"
    )

    assert first == second == expected
    assert expected.endswith(b"\n") and b"\r" not in expected
    assert str(repository.resolve()).encode() not in expected
    assert b"timestamp" not in expected.lower()
    assert [
        (fact.kind, fact.callee, fact.is_optional, fact.source_path)
        for fact in parsed.javascript_calls
    ] == [
        (
            JavaScriptCallKind.IDENTIFIER,
            "useState",
            False,
            "src/ProfileCard.tsx",
        ),
        (
            JavaScriptCallKind.IDENTIFIER,
            "useEffect",
            False,
            "src/ProfileCard.tsx",
        ),
        (
            JavaScriptCallKind.IDENTIFIER,
            "loadProfile",
            False,
            "src/ProfileCard.tsx",
        ),
        (JavaScriptCallKind.IDENTIFIER, "fetch", False, "src/api.ts"),
        (JavaScriptCallKind.MEMBER, "response.json", False, "src/api.ts"),
    ]
    assert load_profile.enclosing_id == profile_card.id
    assert load_profile.span == SourceSpan(
        start_line=6,
        end_line=6,
        start_column=25,
        end_column=40,
    )
    assert all(edge.relation is EdgeKind.CONTAINS for edge in parsed.graph.edges)
