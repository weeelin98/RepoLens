from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pytest
import tree_sitter
import tree_sitter_javascript
import tree_sitter_typescript
from pydantic import ValidationError
from tree_sitter import Language, Parser

from repolens.config import RuntimeConfig
from repolens.extractors import (
    EsmExportKind,
    EsmImportKind,
    ExtractionResult,
    Extractor,
    ExtractorRegistry,
    JavaScriptTypeScriptExtractor,
    UnresolvedEsmExportFact,
    UnresolvedEsmImportFact,
)
from repolens.graph.serialization import canonical_index_json, parse_index_json
from repolens.ids import stable_node_id
from repolens.indexer import RepositoryIndexResult, index_repository
from repolens.models import (
    EdgeKind,
    EvidenceKind,
    GraphNode,
    GraphSnapshot,
    NodeKind,
    SourceSpan,
)

PROJECT_ROOT = Path(__file__).parents[1]


def _node(result: ExtractionResult, qualified_name: str) -> GraphNode:
    return next(node for node in result.nodes if node.qualified_name == qualified_name)


def test_locked_tree_sitter_versions_and_real_parser_abi_compatibility() -> None:
    javascript = Language(tree_sitter_javascript.language())
    typescript = Language(tree_sitter_typescript.language_typescript())

    assert importlib.metadata.version("tree-sitter") == "0.26.0"
    assert importlib.metadata.version("tree-sitter-javascript") == "0.25.0"
    assert importlib.metadata.version("tree-sitter-typescript") == "0.23.2"
    assert tree_sitter.LANGUAGE_VERSION == 15
    assert tree_sitter.MIN_COMPATIBLE_LANGUAGE_VERSION == 13
    assert javascript.abi_version == 15
    assert typescript.abi_version == 14
    assert not Parser(javascript).parse(b"function js() {}").root_node.has_error
    assert not Parser(typescript).parse(b"function ts(value: string) {}").root_node.has_error


def test_extractor_declares_exact_extensions_and_matches_registry_protocol() -> None:
    extractor = JavaScriptTypeScriptExtractor()
    registry = ExtractorRegistry()
    registry.register(extractor)

    assert isinstance(extractor, Extractor)
    assert extractor.extensions == frozenset({".js", ".ts"})
    assert extractor.filenames == frozenset()
    assert registry.for_path(Path("app.JS")) is extractor
    assert registry.for_path(Path("app.TS")) is extractor
    assert registry.for_path(Path("app.jsx")) is None
    assert registry.for_path(Path("app.tsx")) is None


@pytest.mark.parametrize("suffix", [".jsx", ".tsx", ".mjs", ".cjs", ".py"])
def test_extractor_rejects_unsupported_extensions(suffix: str) -> None:
    with pytest.raises(ValueError, match=r"only \.js and \.ts"):
        JavaScriptTypeScriptExtractor().extract(Path(f"module{suffix}"), "")


def test_extractor_rejects_absolute_and_parent_paths() -> None:
    extractor = JavaScriptTypeScriptExtractor()

    with pytest.raises(ValueError, match="repository-relative"):
        extractor.extract(Path(r"C:\repo\module.js"), "")
    with pytest.raises(ValueError, match=r"cannot contain '\.\.'"):
        extractor.extract(Path("../module.ts"), "")


@pytest.mark.parametrize(
    ("path", "language", "module_name"),
    [
        (Path("index.js"), "javascript", "index"),
        (Path("src/utils.js"), "javascript", "src.utils"),
        (Path("src/user.ts"), "typescript", "src.user"),
        (Path(r"src\nested\user.ts"), "typescript", "src.nested.user"),
    ],
)
def test_module_names_languages_paths_spans_and_ids(
    path: Path,
    language: str,
    module_name: str,
) -> None:
    result = JavaScriptTypeScriptExtractor().extract(path, "")
    module = result.nodes[0]
    source_path = path.as_posix().replace("\\", "/")

    assert module.kind is NodeKind.MODULE
    assert module.label == module.qualified_name == module_name
    assert module.language == language
    assert module.source_path == source_path
    assert module.span == SourceSpan(
        start_line=1,
        end_line=1,
        start_column=0,
        end_column=0,
    )
    assert module.id == stable_node_id(
        NodeKind.MODULE,
        source_path=source_path,
        qualified_name=module_name,
        start_line=1,
        disambiguator="column:0",
    )


def test_extracts_js_definitions_with_exact_spans_and_nearest_parents() -> None:
    source = "\n".join(
        [
            "async function load() {",
            "  function nested() {}",
            "}",
            "class Service {",
            "  run() {}",
            "  async save() {}",
            "}",
            "const arrow = () => {",
            "  class Nested {}",
            "};",
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("src/app.js"), source)
    expected = {
        "src.app": (
            NodeKind.MODULE,
            SourceSpan(start_line=1, end_line=10, start_column=0, end_column=2),
        ),
        "src.app.load": (
            NodeKind.FUNCTION,
            SourceSpan(start_line=1, end_line=3, start_column=0, end_column=1),
        ),
        "src.app.load.nested": (
            NodeKind.FUNCTION,
            SourceSpan(start_line=2, end_line=2, start_column=2, end_column=22),
        ),
        "src.app.Service": (
            NodeKind.CLASS,
            SourceSpan(start_line=4, end_line=7, start_column=0, end_column=1),
        ),
        "src.app.Service.run": (
            NodeKind.METHOD,
            SourceSpan(start_line=5, end_line=5, start_column=2, end_column=10),
        ),
        "src.app.Service.save": (
            NodeKind.METHOD,
            SourceSpan(start_line=6, end_line=6, start_column=2, end_column=17),
        ),
        "src.app.arrow": (
            NodeKind.FUNCTION,
            SourceSpan(start_line=8, end_line=10, start_column=6, end_column=1),
        ),
        "src.app.arrow.Nested": (
            NodeKind.CLASS,
            SourceSpan(start_line=9, end_line=9, start_column=2, end_column=17),
        ),
    }

    assert {node.qualified_name: (node.kind, node.span) for node in result.nodes} == expected
    by_name = {node.qualified_name: node for node in result.nodes}
    parents = {edge.target_id: edge.source_id for edge in result.edges}
    assert parents == {
        by_name["src.app.load"].id: by_name["src.app"].id,
        by_name["src.app.load.nested"].id: by_name["src.app.load"].id,
        by_name["src.app.Service"].id: by_name["src.app"].id,
        by_name["src.app.Service.run"].id: by_name["src.app.Service"].id,
        by_name["src.app.Service.save"].id: by_name["src.app.Service"].id,
        by_name["src.app.arrow"].id: by_name["src.app"].id,
        by_name["src.app.arrow.Nested"].id: by_name["src.app.arrow"].id,
    }
    assert all(
        edge.relation is EdgeKind.CONTAINS
        and edge.evidence_kind is EvidenceKind.SYNTAX_DIRECT
        and edge.confidence == 1.0
        for edge in result.edges
    )


def test_extracts_typed_classes_methods_functions_and_default_export() -> None:
    source = "\n".join(
        [
            "export default class Service {",
            "  async load(): Promise<void> {}",
            "}",
            "export async function fetchOne(id: string): Promise<void> {}",
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("src/api.ts"), source)

    assert [(node.kind, node.qualified_name) for node in result.nodes] == [
        (NodeKind.MODULE, "src.api"),
        (NodeKind.CLASS, "src.api.Service"),
        (NodeKind.METHOD, "src.api.Service.load"),
        (NodeKind.FUNCTION, "src.api.fetchOne"),
    ]
    assert [
        (fact.kind, fact.exported_name, fact.local_name, fact.is_default)
        for fact in result.esm_exports
    ] == [
        (EsmExportKind.DECLARATION, "default", "Service", True),
        (EsmExportKind.DECLARATION, "fetchOne", "fetchOne", False),
    ]


def test_only_simple_identifier_arrow_declarators_are_definitions() -> None:
    source = "\n".join(
        [
            "const kept = () => 1, second = async () => 2;",
            "const { skipped } = { skipped: () => 3 };",
            "const ordinary = 4;",
            "callback(() => { function hidden() {} });",
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("arrows.js"), source)

    assert [node.qualified_name for node in result.nodes] == [
        "arrows",
        "arrows.kept",
        "arrows.second",
    ]


def test_unsupported_scopes_are_barriers_and_do_not_leak_nested_definitions() -> None:
    source = "\n".join(
        [
            "function* generator() { function hiddenOne() {} }",
            "const expression = function () { function hiddenTwo() {} };",
            "({ method() { function hiddenThree() {} } });",
            "class Container {",
            "  constructor() { function hiddenFour() {} }",
            "  get value() { function hiddenFive() {} return 1; }",
            "  *iterate() { function hiddenSix() {} }",
            "}",
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("barriers.js"), source)

    assert [node.qualified_name for node in result.nodes] == [
        "barriers",
        "barriers.Container",
    ]


def test_typescript_namespaces_and_ambient_declarations_are_scope_barriers() -> None:
    source = "\n".join(
        [
            "namespace Hidden { export function leaked() {} }",
            "module AlsoHidden { export class Leaked {} }",
            "declare class Ambient { method(): void; }",
            "function visible() {}",
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("scope.ts"), source)

    assert [node.qualified_name for node in result.nodes] == ["scope", "scope.visible"]


def test_same_name_same_line_definitions_have_column_disambiguated_ids() -> None:
    source = "function duplicate() {} function duplicate() {}"
    result = JavaScriptTypeScriptExtractor().extract(Path("same-line.js"), source)
    duplicates = [node for node in result.nodes if node.label == "duplicate"]

    assert [node.span.start_column for node in duplicates if node.span] == [0, 24]
    assert len({node.id for node in duplicates}) == 2
    assert duplicates[0].id == stable_node_id(
        NodeKind.FUNCTION,
        source_path="same-line.js",
        qualified_name="same-line.duplicate",
        start_line=1,
        disambiguator="column:0",
    )
    assert duplicates[1].id == stable_node_id(
        NodeKind.FUNCTION,
        source_path="same-line.js",
        qualified_name="same-line.duplicate",
        start_line=1,
        disambiguator="column:24",
    )


def test_extracts_static_esm_import_forms_with_narrow_spans_and_no_edges() -> None:
    source = "\n".join(
        [
            "import 'setup';",
            "import primary from 'one';",
            "import * as namespace from 'two';",
            "import primaryTwo, { alpha, beta as localBeta } from 'three';",
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("imports.js"), source)

    assert [
        (fact.kind, fact.module, fact.imported_name, fact.local_name, fact.span)
        for fact in result.esm_imports
    ] == [
        (
            EsmImportKind.SIDE_EFFECT,
            "setup",
            None,
            None,
            SourceSpan(start_line=1, end_line=1, start_column=7, end_column=14),
        ),
        (
            EsmImportKind.DEFAULT,
            "one",
            "default",
            "primary",
            SourceSpan(start_line=2, end_line=2, start_column=7, end_column=14),
        ),
        (
            EsmImportKind.NAMESPACE,
            "two",
            "*",
            "namespace",
            SourceSpan(start_line=3, end_line=3, start_column=7, end_column=21),
        ),
        (
            EsmImportKind.DEFAULT,
            "three",
            "default",
            "primaryTwo",
            SourceSpan(start_line=4, end_line=4, start_column=7, end_column=17),
        ),
        (
            EsmImportKind.NAMED,
            "three",
            "alpha",
            "alpha",
            SourceSpan(start_line=4, end_line=4, start_column=21, end_column=26),
        ),
        (
            EsmImportKind.NAMED,
            "three",
            "beta",
            "localBeta",
            SourceSpan(start_line=4, end_line=4, start_column=28, end_column=45),
        ),
    ]
    assert all(edge.relation is not EdgeKind.IMPORTS for edge in result.edges)


def test_empty_module_specifier_is_ignored_without_crashing() -> None:
    result = JavaScriptTypeScriptExtractor().extract(Path("empty.js"), "import '';\n")

    assert result.esm_imports == ()
    assert result.diagnostics == ()


def test_statement_level_type_only_imports_are_omitted() -> None:
    source = "\n".join(
        [
            'import type { Foo } from "./types";',
            'import type DefaultType from "./default-type";',
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("type-imports.ts"), source)

    assert result.esm_imports == ()


def test_inline_type_only_import_is_omitted_without_an_empty_fact() -> None:
    result = JavaScriptTypeScriptExtractor().extract(
        Path("inline-type-import.ts"),
        'import { type Foo } from "./types";',
    )

    assert result.esm_imports == ()


def test_mixed_runtime_and_type_only_import_retains_only_runtime_specifier() -> None:
    source = 'import { Foo, type Bar } from "./types";'
    extractor = JavaScriptTypeScriptExtractor()

    first = extractor.extract(Path("mixed-import.ts"), source)
    second = extractor.extract(Path("mixed-import.ts"), source)

    assert first == second
    assert [
        (fact.kind, fact.module, fact.imported_name, fact.local_name) for fact in first.esm_imports
    ] == [(EsmImportKind.NAMED, "./types", "Foo", "Foo")]


def test_extracts_direct_local_esm_exports_but_not_reexports_or_edges() -> None:
    source = "\n".join(
        [
            "export function named() {}",
            "export default async function main() {}",
            "export class Service {}",
            "export const arrow = () => 1;",
            "const local = 1;",
            "export { local, arrow as renamed, local as default };",
            "export { remote } from './remote.js';",
            "export * from './all.js';",
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("exports.js"), source)

    assert [
        (fact.kind, fact.exported_name, fact.local_name, fact.is_default)
        for fact in result.esm_exports
    ] == [
        (EsmExportKind.DECLARATION, "named", "named", False),
        (EsmExportKind.DECLARATION, "default", "main", True),
        (EsmExportKind.DECLARATION, "Service", "Service", False),
        (EsmExportKind.DECLARATION, "arrow", "arrow", False),
        (EsmExportKind.LIST, "local", "local", False),
        (EsmExportKind.LIST, "renamed", "arrow", False),
        (EsmExportKind.LIST, "default", "local", True),
    ]
    assert all(edge.relation is not EdgeKind.EXPORTS for edge in result.edges)
    assert all("remote" not in fact.local_name for fact in result.esm_exports)


def test_statement_level_type_only_export_is_omitted() -> None:
    result = JavaScriptTypeScriptExtractor().extract(
        Path("type-export.ts"),
        "export type { Foo };",
    )

    assert result.esm_exports == ()


def test_inline_type_only_export_is_omitted_without_an_empty_fact() -> None:
    result = JavaScriptTypeScriptExtractor().extract(
        Path("inline-type-export.ts"),
        "export { type Foo };",
    )

    assert result.esm_exports == ()


def test_mixed_runtime_and_type_only_export_retains_only_runtime_specifier() -> None:
    source = "export { Foo, type Bar };"
    extractor = JavaScriptTypeScriptExtractor()

    first = extractor.extract(Path("mixed-export.ts"), source)
    second = extractor.extract(Path("mixed-export.ts"), source)

    assert first == second
    assert [
        (fact.kind, fact.exported_name, fact.local_name, fact.is_default)
        for fact in first.esm_exports
    ] == [(EsmExportKind.LIST, "Foo", "Foo", False)]


def test_type_only_and_runtime_reexports_remain_unsupported() -> None:
    source = "\n".join(
        [
            'export type { Foo } from "./types";',
            'export { RuntimeValue } from "./runtime";',
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("reexports.ts"), source)

    assert result.esm_exports == ()


def test_anonymous_default_exports_are_out_of_scope() -> None:
    source = "\n".join(
        [
            "export default function () { function hidden() {} }",
            "export default class { method() {} }",
            "export default () => 1;",
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("anonymous.js"), source)

    assert [node.qualified_name for node in result.nodes] == ["anonymous"]
    assert result.esm_exports == ()


def test_malformed_top_level_error_keeps_only_error_free_sibling_subtrees() -> None:
    source = "function before() {}\n}\nfunction after() {}"
    extractor = JavaScriptTypeScriptExtractor()

    first = extractor.extract(Path("broken.js"), source)
    second = extractor.extract(Path("broken.js"), source)

    assert first == second
    assert [node.qualified_name for node in first.nodes] == [
        "broken",
        "broken.before",
        "broken.after",
    ]
    assert first.diagnostics == ("tree_sitter_syntax_error:broken.js:2:0",)


def test_malformed_declaration_subtree_is_not_partially_promoted() -> None:
    source = "\n".join(
        [
            "function outer() {",
            "  const broken = ;",
            "  function nestedButTainted() {}",
            "}",
            "function after() {}",
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("broken.js"), source)

    assert [node.qualified_name for node in result.nodes] == ["broken", "broken.after"]
    assert result.diagnostics == ("tree_sitter_syntax_error:broken.js:2:17",)


def test_unicode_columns_remain_zero_based_utf8_byte_offsets() -> None:
    source = "const café = () => 1;"
    result = JavaScriptTypeScriptExtractor().extract(Path("unicode.js"), source)
    arrow = _node(result, "unicode.café")

    assert arrow.span == SourceSpan(
        start_line=1,
        end_line=1,
        start_column=6,
        end_column=21,
    )


def test_extraction_is_repeatable_and_does_not_execute_source(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed.txt"
    source = (
        "import { writeFileSync } from 'node:fs';\n"
        f"writeFileSync({str(sentinel)!r}, 'executed');\n"
        "export const safe = () => 1;\n"
    )
    extractor = JavaScriptTypeScriptExtractor()

    first = extractor.extract(Path("danger.js"), source)
    second = extractor.extract(Path("danger.js"), source)

    assert first == second
    assert _node(first, "danger.safe")
    assert not sentinel.exists()


def test_esm_fact_models_reject_inconsistent_forms_and_absolute_paths() -> None:
    span = SourceSpan(start_line=1, end_line=1, start_column=0, end_column=1)

    with pytest.raises(ValidationError):
        UnresolvedEsmImportFact(
            kind=EsmImportKind.DEFAULT,
            module="pkg",
            imported_name="wrong",
            local_name="local",
            source_path="module.js",
            span=span,
        )
    with pytest.raises(ValidationError, match="repository-relative"):
        UnresolvedEsmExportFact(
            kind=EsmExportKind.LIST,
            exported_name="name",
            local_name="name",
            source_path=r"C:\repo\module.js",
            span=span,
        )


def test_empty_esm_channels_preserve_old_index_serialization_and_parsing() -> None:
    result = RepositoryIndexResult(graph=GraphSnapshot())
    rendered = canonical_index_json(result)

    assert '"esm_imports"' not in rendered
    assert '"esm_exports"' not in rendered
    parsed = parse_index_json(rendered)
    assert parsed.esm_imports == ()
    assert parsed.esm_exports == ()


def test_typescript_frontend_matches_separate_m21a_partial_gold() -> None:
    fixture = PROJECT_ROOT / "harness" / "fixtures" / "typescript_frontend"
    result = index_repository(fixture / "repo", RuntimeConfig())
    rendered = canonical_index_json(result)
    expected = (fixture / "m2-1a-graph.json").read_text(encoding="utf-8")

    assert rendered == expected
    assert result == parse_index_json(expected)
    assert {node.source_path for node in result.graph.nodes} == {
        ".",
        "src",
        "src/api.ts",
        "tsconfig.json",
    }
    assert [node.qualified_name for node in result.graph.nodes if node.qualified_name] == [
        "src.api.loadProfile",
        "src.api",
        "<repository>",
    ]
    assert [(fact.exported_name, fact.local_name) for fact in result.esm_exports] == [
        ("loadProfile", "loadProfile")
    ]
    assert all(node.source_path != "src/ProfileCard.tsx" for node in result.graph.nodes)
