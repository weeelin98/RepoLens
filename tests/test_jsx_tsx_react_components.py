from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest
import tree_sitter
import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser

from repolens.config import RuntimeConfig
from repolens.extractors import (
    EsmExportKind,
    ExtractionResult,
    JavaScriptTypeScriptExtractor,
)
from repolens.graph.serialization import canonical_index_json, parse_index_json
from repolens.indexer import index_repository
from repolens.models import EdgeKind, GraphNode, NodeKind, SourceSpan

PROJECT_ROOT = Path(__file__).parents[1]


def _node_for_name(nodes: tuple[GraphNode, ...], qualified_name: str) -> GraphNode:
    return next(node for node in nodes if node.qualified_name == qualified_name)


def _component_names(source: str, path: str = "components.tsx") -> set[str]:
    result = JavaScriptTypeScriptExtractor().extract(Path(path), source)
    return {node.label for node in result.nodes if node.kind is NodeKind.REACT_COMPONENT}


def test_locked_javascript_and_tsx_parser_capsules_and_abis() -> None:
    javascript = Language(tree_sitter_javascript.language())
    typescript = Language(tree_sitter_typescript.language_typescript())
    tsx = Language(tree_sitter_typescript.language_tsx())

    assert importlib.metadata.version("tree-sitter") == "0.26.0"
    assert importlib.metadata.version("tree-sitter-javascript") == "0.25.0"
    assert importlib.metadata.version("tree-sitter-typescript") == "0.23.2"
    assert tree_sitter.MIN_COMPATIBLE_LANGUAGE_VERSION == 13
    assert tree_sitter.LANGUAGE_VERSION == 15
    assert javascript.abi_version == 15
    assert typescript.abi_version == tsx.abi_version == 14
    assert not Parser(javascript).parse(b"const View = () => <main />;").root_node.has_error
    assert not Parser(tsx).parse(b"const View = <T>(value: T) => <main />;").root_node.has_error
    assert Parser(typescript).parse(b"const View = () => <main />;").root_node.has_error


def test_extractor_routes_jsx_and_tsx_with_exact_language_labels() -> None:
    extractor = JavaScriptTypeScriptExtractor()

    jsx = extractor.extract(Path("src/View.JSX"), "export function helper() {}")
    tsx = extractor.extract(
        Path("src/View.TSX"),
        "export interface Props { id: string }\nexport function helper(): void {}",
    )

    assert extractor.extensions == frozenset({".js", ".jsx", ".ts", ".tsx"})
    assert {node.language for node in jsx.nodes} == {"jsx"}
    assert {node.language for node in tsx.nodes} == {"tsx"}
    assert _node_for_name(jsx.nodes, "src.View.helper").kind is NodeKind.FUNCTION
    assert _node_for_name(tsx.nodes, "src.View.Props").kind is NodeKind.INTERFACE


@pytest.mark.parametrize("suffix", [".mjs", ".cjs", ".py"])
def test_extractor_still_rejects_unapproved_suffixes(suffix: str) -> None:
    with pytest.raises(ValueError, match=r"only \.js, \.jsx, \.ts, and \.tsx"):
        JavaScriptTypeScriptExtractor().extract(Path(f"module{suffix}"), "")


def test_non_jsx_m21_behavior_is_semantically_equal_on_new_suffixes() -> None:
    javascript_source = (
        'import value from "pkg";\n'
        "export const load = () => value;\n"
        "class Service { run() {} }\n"
        "const common = require('common');\n"
    )
    typescript_source = (
        'export { value } from "pkg";\n'
        "export interface Shape { value: string }\n"
        "export type Name = string;\n"
        "export enum State { Ready }\n"
        "const identity = <T>(value: T) => value;\n"
    )
    extractor = JavaScriptTypeScriptExtractor()

    js = extractor.extract(Path("same.js"), javascript_source)
    jsx = extractor.extract(Path("same.jsx"), javascript_source)
    ts = extractor.extract(Path("same.ts"), typescript_source)
    tsx = extractor.extract(Path("same.tsx"), typescript_source)

    def definitions(result: ExtractionResult) -> list[tuple[NodeKind, str, SourceSpan | None]]:
        return [
            (node.kind, node.label, node.span)
            for node in result.nodes
            if node.kind is not NodeKind.MODULE
        ]

    assert definitions(js) == definitions(jsx)
    assert definitions(ts) == definitions(tsx)
    assert [(fact.kind, fact.module) for fact in js.esm_imports] == [
        (fact.kind, fact.module) for fact in jsx.esm_imports
    ]
    assert [(fact.kind, fact.module) for fact in ts.esm_reexports] == [
        (fact.kind, fact.module) for fact in tsx.esm_reexports
    ]
    assert [(fact.kind, fact.module) for fact in js.commonjs_requires] == [
        (fact.kind, fact.module) for fact in jsx.commonjs_requires
    ]


def test_function_components_require_runtime_react_and_direct_jsx_return() -> None:
    source = """
import React, { useState, type FC } from "react";
export function Card({ id }: { id: string }) { return <main>{id}</main>; }
export default function Panel() { return (((<><span /></>))); }
function lower() { return <main />; }
function Helper() { return 1; }
async function AsyncCard() { return <main />; }
function Conditional() { return condition ? <main /> : <aside />; }
function NestedControl() { if (condition) { return <main />; } }
function Multiple() { return <main />; return <aside />; }
export default () => <main />;
""".lstrip()

    result = JavaScriptTypeScriptExtractor().extract(Path("src/components.tsx"), source)

    assert _component_names(source, "src/components.tsx") == {"Card", "Panel"}
    assert _node_for_name(result.nodes, "src.components.lower").kind is NodeKind.FUNCTION
    assert _node_for_name(result.nodes, "src.components.Helper").kind is NodeKind.FUNCTION
    assert _node_for_name(result.nodes, "src.components.AsyncCard").kind is NodeKind.FUNCTION
    assert _node_for_name(result.nodes, "src.components.Conditional").kind is NodeKind.FUNCTION
    assert _node_for_name(result.nodes, "src.components.NestedControl").kind is NodeKind.FUNCTION
    assert _node_for_name(result.nodes, "src.components.Multiple").kind is NodeKind.FUNCTION


@pytest.mark.parametrize(
    "import_source",
    [
        "",
        'import "react";\n',
        'import type React from "react";\n',
        'import { type Component } from "react";\n',
        'import React from "preact";\n',
    ],
)
def test_function_component_framework_false_positives_remain_ordinary(
    import_source: str,
) -> None:
    source = import_source + "function Card() { return <main />; }\n"
    result = JavaScriptTypeScriptExtractor().extract(Path("Card.tsx"), source)

    assert _node_for_name(result.nodes, "Card.Card").kind is NodeKind.FUNCTION
    assert not any(node.kind is NodeKind.REACT_COMPONENT for node in result.nodes)


def test_arrow_components_cover_expression_block_and_generic_forms() -> None:
    source = """
import { useMemo } from "react";
export const Card = () => <main />, Panel = () => { return (<section />); };
const Generic = <T>(value: T) => <main>{String(value)}</main>;
const GenericComma = <T,>(value: T) => (<main>{String(value)}</main>);
const AsyncCard = async () => <main />;
const Wrapped = memo(() => <main />);
const Conditional = () => condition && <main />;
const Asserted = () => (<main /> as JSX.Element);
const Satisfied = () => (<main /> satisfies JSX.Element);
function Outer() { const Nested = () => <main />; return <aside />; }
""".lstrip()

    result = JavaScriptTypeScriptExtractor().extract(Path("arrows.tsx"), source)

    assert _component_names(source, "arrows.tsx") == {
        "Card",
        "Panel",
        "Generic",
        "GenericComma",
        "Outer",
    }
    assert _node_for_name(result.nodes, "arrows.AsyncCard").kind is NodeKind.FUNCTION
    assert _node_for_name(result.nodes, "arrows.Asserted").kind is NodeKind.FUNCTION
    assert _node_for_name(result.nodes, "arrows.Conditional").kind is NodeKind.FUNCTION
    assert _node_for_name(result.nodes, "arrows.Outer.Nested").kind is NodeKind.FUNCTION
    assert _node_for_name(result.nodes, "arrows.Satisfied").kind is NodeKind.FUNCTION
    assert all(node.label != "Wrapped" for node in result.nodes)


@pytest.mark.parametrize(
    ("import_line", "heritage"),
    [
        ('import React from "react";', "React.Component"),
        ('import * as React from "react";', "React.PureComponent"),
        ('import { Component } from "react";', "Component"),
        ('import { PureComponent as Base } from "react";', "Base<Props>"),
    ],
)
def test_class_components_use_exact_runtime_import_and_heritage(
    import_line: str,
    heritage: str,
) -> None:
    source = (
        f"{import_line}\n"
        "interface Props { value: string }\n"
        f"export default class Card extends {heritage} {{\n"
        "  helper() {}\n"
        "  render() { return (<><main /></>); }\n"
        "}\n"
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("src/Card.tsx"), source)
    component = _node_for_name(result.nodes, "src.Card.Card")
    helper = _node_for_name(result.nodes, "src.Card.Card.helper")
    render = _node_for_name(result.nodes, "src.Card.Card.render")

    assert component.kind is NodeKind.REACT_COMPONENT
    assert helper.kind is render.kind is NodeKind.METHOD
    parents = {edge.target_id: edge.source_id for edge in result.edges}
    assert parents[helper.id] == parents[render.id] == component.id
    assert [(fact.kind, fact.exported_name, fact.local_name) for fact in result.esm_exports] == [
        (EsmExportKind.DECLARATION, "default", "Card")
    ]


@pytest.mark.parametrize(
    "source",
    [
        "class Card extends Component { render() { return <main />; } }",
        'import type React from "react"; '
        "class Card extends React.Component { render() { return <main />; } }",
        'import React from "preact"; '
        "class Card extends React.Component { render() { return <main />; } }",
        'import React from "react"; class Card extends Base { render() { return <main />; } }',
        'import React from "react"; '
        "class Card extends React.Component { static render() { return <main />; } }",
        'import React from "react"; '
        "class Card extends React.Component { async render() { return <main />; } }",
        'import React from "react"; '
        "class Card extends React.Component { *render() { return <main />; } }",
        'import React from "react"; '
        "class Card extends React.Component { get render() { return <main />; } }",
        'import React from "react"; '
        "class Card extends React.Component { render = () => <main />; }",
        'import React from "react"; '
        "class Card extends React.Component { render?() { return <main />; } }",
        'import React from "react"; '
        "class Card extends React.Component { render(): JSX.Element; "
        "render() { return <main />; } }",
        'import React from "react"; '
        "class Card extends React.Component { render() { return <main />; } "
        "render(value: string) { return <aside />; } }",
    ],
)
def test_class_component_near_misses_remain_ordinary(source: str) -> None:
    result = JavaScriptTypeScriptExtractor().extract(Path("Card.tsx"), source)

    assert _node_for_name(result.nodes, "Card.Card").kind is NodeKind.CLASS
    assert not any(node.kind is NodeKind.REACT_COMPONENT for node in result.nodes)


def test_component_representation_span_id_containment_and_exports_are_exact() -> None:
    source = """
import React from "react";
function Card() {
  function Nested() {}
  return (<><span /></>);
}
export { Card, Card as default };
""".lstrip()
    result = JavaScriptTypeScriptExtractor().extract(Path("src/Card.tsx"), source)
    component = _node_for_name(result.nodes, "src.Card.Card")
    nested = _node_for_name(result.nodes, "src.Card.Card.Nested")
    module = _node_for_name(result.nodes, "src.Card")

    assert component.kind is NodeKind.REACT_COMPONENT
    assert component.id == "react_component:4fca22beb99cff67a81a"
    assert component.span == SourceSpan(
        start_line=2,
        end_line=5,
        start_column=0,
        end_column=1,
    )
    assert nested.kind is NodeKind.FUNCTION
    assert not any(
        node.kind is NodeKind.FUNCTION and node.qualified_name == component.qualified_name
        for node in result.nodes
    )
    assert {(edge.source_id, edge.target_id) for edge in result.edges} >= {
        (module.id, component.id),
        (component.id, nested.id),
    }
    assert [
        (fact.exported_name, fact.local_name, fact.is_default) for fact in result.esm_exports
    ] == [
        ("Card", "Card", False),
        ("default", "Card", True),
    ]
    assert all(
        edge.relation not in {EdgeKind.IMPORTS, EdgeKind.EXPORTS, EdgeKind.CALLS, EdgeKind.INHERITS}
        for edge in result.edges
    )


def test_partial_tree_keeps_safe_function_but_suppresses_class_and_commonjs() -> None:
    source = """
import React from "react";
function Safe() { return <main />; }
}
class Card extends React.Component { render() { return <main />; } }
require("pkg");
""".lstrip()
    result = JavaScriptTypeScriptExtractor().extract(Path("partial.jsx"), source)

    assert _node_for_name(result.nodes, "partial.Safe").kind is NodeKind.REACT_COMPONENT
    assert _node_for_name(result.nodes, "partial.Card").kind is NodeKind.CLASS
    assert result.commonjs_requires == ()
    assert result.diagnostics == ("tree_sitter_syntax_error:partial.jsx:3:0",)


def test_js_and_ts_component_classification_remains_disabled() -> None:
    extractor = JavaScriptTypeScriptExtractor()
    javascript = extractor.extract(
        Path("Card.js"),
        'import React from "react"; function Card() { return <main />; }',
    )

    assert _node_for_name(javascript.nodes, "Card.Card").kind is NodeKind.FUNCTION


def test_component_extraction_is_repeatable_private_and_nonexecuting(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed.txt"
    source = (
        'import React from "react";\n'
        'import { writeFileSync } from "node:fs";\n'
        f"writeFileSync({str(sentinel)!r}, 'executed');\n"
        "export const Card = () => <main />;\n"
    )
    extractor = JavaScriptTypeScriptExtractor()

    first = extractor.extract(Path("src/Card.jsx"), source)
    second = extractor.extract(Path("src/Card.jsx"), source)

    assert first == second
    assert _node_for_name(first.nodes, "src.Card.Card").kind is NodeKind.REACT_COMPONENT
    assert str(tmp_path) not in repr(first)
    assert not sentinel.exists()


def test_fullstack_task_panel_is_component_without_later_relationships() -> None:
    repository = PROJECT_ROOT / "harness" / "fixtures" / "fullstack_fastapi_react" / "repo"
    result = index_repository(repository, RuntimeConfig())
    panel = _node_for_name(result.graph.nodes, "frontend.src.TaskPanel.TaskPanel")

    assert panel.kind is NodeKind.REACT_COMPONENT
    assert panel.source_path == "frontend/src/TaskPanel.tsx"
    assert panel.span == SourceSpan(
        start_line=4,
        end_line=8,
        start_column=7,
        end_column=1,
    )
    assert all(
        edge.relation not in {EdgeKind.IMPORTS, EdgeKind.EXPORTS, EdgeKind.CALLS, EdgeKind.INHERITS}
        for edge in result.graph.edges
    )
    rendered = canonical_index_json(result)
    assert str(repository.resolve()) not in rendered
    assert "timestamp" not in rendered.casefold()


def test_m22a_typescript_frontend_partial_gold_matches_semantics_and_repeated_generation() -> None:
    fixture = PROJECT_ROOT / "harness" / "fixtures" / "typescript_frontend"
    repository = fixture / "repo"
    expected = (fixture / "m2-2a-graph.json").read_bytes()

    first = canonical_index_json(index_repository(repository, RuntimeConfig())).encode()
    second = canonical_index_json(index_repository(repository, RuntimeConfig())).encode()
    parsed = parse_index_json(expected.decode())
    profile_card = _node_for_name(
        parsed.graph.nodes,
        "src.ProfileCard.ProfileCard",
    )

    assert first == second == expected
    assert expected.endswith(b"\n") and b"\r" not in expected
    assert profile_card.kind is NodeKind.REACT_COMPONENT
    assert profile_card.language == "tsx"
    assert profile_card.source_path == "src/ProfileCard.tsx"
    assert profile_card.span == SourceSpan(
        start_line=4,
        end_line=8,
        start_column=7,
        end_column=1,
    )
    assert [
        (fact.module, fact.imported_name, fact.local_name)
        for fact in parsed.esm_imports
        if fact.source_path == "src/ProfileCard.tsx"
    ] == [
        ("react", "useEffect", "useEffect"),
        ("react", "useState", "useState"),
        ("./api", "loadProfile", "loadProfile"),
    ]
    assert all(fact.imported_name != "Profile" for fact in parsed.esm_imports)
    assert all(
        edge.relation not in {EdgeKind.IMPORTS, EdgeKind.EXPORTS, EdgeKind.CALLS, EdgeKind.INHERITS}
        for edge in parsed.graph.edges
    )
    assert str(repository.resolve()).encode() not in expected
    assert b"timestamp" not in expected.lower()
