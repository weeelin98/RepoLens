from __future__ import annotations

import importlib.metadata
import shutil
from pathlib import Path

import pytest
import tree_sitter
import tree_sitter_javascript
import tree_sitter_typescript
from pydantic import ValidationError
from tree_sitter import Language, Parser

from repolens.config import RuntimeConfig
from repolens.extractors import (
    CommonJsExportKind,
    CommonJsRequireKind,
    EsmExportKind,
    EsmImportKind,
    EsmReExportKind,
    ExtractionResult,
    Extractor,
    ExtractorRegistry,
    JavaScriptTypeScriptExtractor,
    UnresolvedCommonJsExportFact,
    UnresolvedCommonJsRequireFact,
    UnresolvedEsmExportFact,
    UnresolvedEsmImportFact,
    UnresolvedEsmReExportFact,
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


def _m21a_compatibility_projection(result: RepositoryIndexResult) -> RepositoryIndexResult:
    additive_kinds = {NodeKind.INTERFACE, NodeKind.TYPE_ALIAS, NodeKind.ENUM}
    additive_ids = {node.id for node in result.graph.nodes if node.kind in additive_kinds}
    assert all(
        edge.relation is EdgeKind.CONTAINS
        for edge in result.graph.edges
        if edge.source_id in additive_ids or edge.target_id in additive_ids
    )
    return RepositoryIndexResult(
        graph=GraphSnapshot(
            schema_version=result.graph.schema_version,
            nodes=tuple(node for node in result.graph.nodes if node.id not in additive_ids),
            edges=tuple(
                edge
                for edge in result.graph.edges
                if edge.source_id not in additive_ids and edge.target_id not in additive_ids
            ),
            metadata=result.graph.metadata,
        ),
        imports=result.imports,
        esm_imports=result.esm_imports,
        esm_exports=result.esm_exports,
        markdown_facts=result.markdown_facts,
        metadata_facts=result.metadata_facts,
        scanner_diagnostics=result.scanner_diagnostics,
        extractor_diagnostics=result.extractor_diagnostics,
    )


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
    assert extractor.extensions == frozenset({".js", ".jsx", ".ts", ".tsx"})
    assert extractor.filenames == frozenset()
    assert registry.for_path(Path("app.JS")) is extractor
    assert registry.for_path(Path("app.TS")) is extractor
    assert registry.for_path(Path("app.jsx")) is extractor
    assert registry.for_path(Path("app.tsx")) is extractor


@pytest.mark.parametrize("suffix", [".mjs", ".cjs", ".py"])
def test_extractor_rejects_unsupported_extensions(suffix: str) -> None:
    with pytest.raises(ValueError, match=r"only \.js, \.jsx, \.ts, and \.tsx"):
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


def test_reexports_do_not_leak_into_local_esm_export_channel() -> None:
    source = "\n".join(
        [
            'export type { Foo } from "./types";',
            'export { RuntimeValue } from "./runtime";',
        ]
    )
    result = JavaScriptTypeScriptExtractor().extract(Path("reexports.ts"), source)

    assert result.esm_exports == ()
    assert [
        (fact.module, fact.imported_name, fact.exported_name) for fact in result.esm_reexports
    ] == [("./runtime", "RuntimeValue", "RuntimeValue")]


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


def test_typescript_frontend_matches_separate_m21a_partial_gold(tmp_path: Path) -> None:
    fixture = PROJECT_ROOT / "harness" / "fixtures" / "typescript_frontend"
    repository = tmp_path / "repo"
    shutil.copytree(fixture / "repo", repository)
    (repository / ".gitignore").write_text("*.jsx\n*.tsx\n", encoding="utf-8", newline="\n")
    result = index_repository(repository, RuntimeConfig())
    projected = _m21a_compatibility_projection(result)
    rendered = canonical_index_json(projected)
    expected = (fixture / "m2-1a-graph.json").read_text(encoding="utf-8")

    assert rendered == expected
    assert projected == parse_index_json(expected)
    assert {node.source_path for node in result.graph.nodes} == {
        ".",
        "src",
        "src/api.ts",
        "tsconfig.json",
    }
    assert [node.qualified_name for node in projected.graph.nodes if node.qualified_name] == [
        "src.api.loadProfile",
        "src.api",
        "<repository>",
    ]
    assert [(fact.exported_name, fact.local_name) for fact in projected.esm_exports] == [
        ("loadProfile", "loadProfile")
    ]
    assert all(node.source_path != "src/ProfileCard.tsx" for node in result.graph.nodes)


def test_top_level_commonjs_supported_forms_are_occurrence_facts() -> None:
    source = (
        'require("setup");\n'
        "const client = require('pkg'), other = require(\"other\");\n"
        "module.exports = client;\n"
        "exports.client = client;\n"
        "module.exports.other = other;\n"
    )

    result = JavaScriptTypeScriptExtractor().extract(Path("src/common.js"), source)

    assert [(fact.kind, fact.module, fact.local_name) for fact in result.commonjs_requires] == [
        (CommonJsRequireKind.SIDE_EFFECT, "setup", None),
        (CommonJsRequireKind.BINDING, "pkg", "client"),
        (CommonJsRequireKind.BINDING, "other", "other"),
    ]
    assert [
        (fact.kind, fact.exported_name, fact.local_name) for fact in result.commonjs_exports
    ] == [
        (CommonJsExportKind.MODULE_EXPORTS, None, "client"),
        (CommonJsExportKind.NAMED, "client", "client"),
        (CommonJsExportKind.NAMED, "other", "other"),
    ]
    assert result.commonjs_requires[0].span == SourceSpan(
        start_line=1, end_line=1, start_column=0, end_column=16
    )
    assert all(edge.relation not in {EdgeKind.IMPORTS, EdgeKind.EXPORTS} for edge in result.edges)


@pytest.mark.parametrize(
    "source",
    [
        "function nested() { require('pkg'); }",
        "const { value } = require('pkg');",
        "const value = require(`pkg`);",
        "const value = require('pkg').value;",
        "const value = require?.('pkg');",
        "const value = require<string>('pkg');",
        "consume(require('pkg'));",
        "module['exports'] = value;",
        "exports.value += value;",
        "exports.value = { value };",
        "module.exports = exports.value = value;",
        "import value = require('pkg');",
        "export = value;",
    ],
)
def test_unsupported_commonjs_neighbors_are_omitted(source: str) -> None:
    result = JavaScriptTypeScriptExtractor().extract(Path("unsupported.ts"), source)

    assert result.commonjs_requires == ()
    assert result.commonjs_exports == ()


@pytest.mark.parametrize(
    ("source", "channel"),
    [
        ("require('pkg'); const require = local;", "require"),
        ("require('pkg'); function require() {}", "require"),
        ("import require from 'shim'; require('pkg');", "require"),
        ("import require = require('shim'); require('pkg');", "require"),
        ("require = local; require('pkg');", "require"),
        ("require('pkg'); require++;", "require"),
        ("require('pkg'); if (flag) { require = local; }", "require"),
        ("require('pkg'); if (flag) { var require; }", "require"),
        ("require('pkg'); function* require() {}", "require"),
        ("require('pkg'); abstract class require {}", "require"),
        ("require('pkg'); namespace require {}", "require"),
        ("module.exports = value; class module {}", "export"),
        ("exports.value = value; let exports;", "export"),
        ("module = local; module.exports = value;", "export"),
    ],
)
def test_commonjs_program_scope_ambiguity_suppresses_relevant_facts(
    source: str,
    channel: str,
) -> None:
    result = JavaScriptTypeScriptExtractor().extract(Path("shadow.ts"), source)

    if channel == "require":
        assert result.commonjs_requires == ()
    else:
        assert result.commonjs_exports == ()


@pytest.mark.parametrize(
    "source",
    [
        "const { value = require } = config; const client = require('pkg');",
        "interface require {} const client = require('pkg');",
        "type require = () => void; const client = require('pkg');",
        "const enum require { Value } const client = require('pkg');",
        "import type require from 'types'; const client = require('pkg');",
        "{ let require; require = local; } const client = require('pkg');",
    ],
)
def test_type_only_names_and_destructuring_references_do_not_shadow_require(source: str) -> None:
    result = JavaScriptTypeScriptExtractor().extract(Path("runtime-shadow.ts"), source)

    assert [(fact.module, fact.local_name) for fact in result.commonjs_requires] == [
        ("pkg", "client")
    ]


def test_partial_parse_suppresses_commonjs_but_keeps_safe_m21a_siblings() -> None:
    source = "require('pkg');\n}\nfunction safe() {}\nmodule.exports = safe;\n"

    result = JavaScriptTypeScriptExtractor().extract(Path("broken.js"), source)

    assert result.commonjs_requires == ()
    assert result.commonjs_exports == ()
    assert _node(result, "broken.safe")
    assert result.diagnostics == ("tree_sitter_syntax_error:broken.js:2:0",)


def test_partial_parse_keeps_safe_m21b_reexport_and_declaration_siblings() -> None:
    source = 'export { value } from "pkg";\n}\ninterface Safe {}\n'

    result = JavaScriptTypeScriptExtractor().extract(Path("partial.ts"), source)

    assert [(fact.module, fact.imported_name) for fact in result.esm_reexports] == [
        ("pkg", "value")
    ]
    assert _node(result, "partial.Safe").kind is NodeKind.INTERFACE
    assert result.diagnostics == ("tree_sitter_syntax_error:partial.ts:2:0",)


def test_runtime_esm_reexport_forms_and_type_filters() -> None:
    source = (
        'export { value, value as alias, default as primary, type Type } from "pkg";\n'
        'export * from "star";\n'
        'export * as namespace from "space";\n'
        'export type { Hidden } from "types";\n'
        'export type * from "more-types";\n'
    )

    result = JavaScriptTypeScriptExtractor().extract(Path("exports.ts"), source)

    assert [
        (fact.kind, fact.module, fact.imported_name, fact.exported_name)
        for fact in result.esm_reexports
    ] == [
        (EsmReExportKind.NAMED, "pkg", "value", "value"),
        (EsmReExportKind.NAMED, "pkg", "value", "alias"),
        (EsmReExportKind.NAMED, "pkg", "default", "primary"),
        (EsmReExportKind.STAR, "star", "*", None),
        (EsmReExportKind.NAMESPACE, "space", "*", "namespace"),
    ]
    assert result.esm_exports == ()


def test_string_named_reexports_remain_outside_the_exact_supported_forms() -> None:
    result = JavaScriptTypeScriptExtractor().extract(
        Path("string-names.ts"),
        'export { "value" as alias, value as "alias" } from "pkg";',
    )

    assert result.esm_reexports == ()


def test_selected_typescript_declarations_are_module_children_only() -> None:
    source = (
        "interface User<T> { value: T }\n"
        "type UserId = string | number;\n"
        "enum Status { Ready, Done = 2 }\n"
        "const enum Hidden { Value }\n"
        "declare interface Ambient {}\n"
        "namespace Space { interface Nested {} }\n"
        "function scope() { type Nested = string; }\n"
    )

    result = JavaScriptTypeScriptExtractor().extract(Path("src/types.ts"), source)
    selected = {
        node.qualified_name: node
        for node in result.nodes
        if node.kind
        in {
            NodeKind.INTERFACE,
            NodeKind.TYPE_ALIAS,
            NodeKind.ENUM,
        }
    }

    assert set(selected) == {"src.types.User", "src.types.UserId", "src.types.Status"}
    assert selected["src.types.User"].kind is NodeKind.INTERFACE
    assert selected["src.types.UserId"].kind is NodeKind.TYPE_ALIAS
    assert selected["src.types.Status"].kind is NodeKind.ENUM
    module = _node(result, "src.types")
    assert {(edge.source_id, edge.target_id) for edge in result.edges} >= {
        (module.id, selected["src.types.User"].id),
        (module.id, selected["src.types.UserId"].id),
        (module.id, selected["src.types.Status"].id),
    }


def test_exported_typescript_type_declarations_do_not_claim_runtime_exports() -> None:
    source = (
        "export interface User {}\nexport type UserId = string;\nexport enum Status { Ready }\n"
    )

    result = JavaScriptTypeScriptExtractor().extract(Path("types.ts"), source)

    assert {node.kind for node in result.nodes} >= {
        NodeKind.INTERFACE,
        NodeKind.TYPE_ALIAS,
        NodeKind.ENUM,
    }
    assert [(fact.exported_name, fact.local_name) for fact in result.esm_exports] == [
        ("Status", "Status")
    ]


def test_new_fact_models_validate_forms_paths_and_old_json_compatibility() -> None:
    span = SourceSpan(start_line=1, end_line=1, start_column=0, end_column=1)

    with pytest.raises(ValidationError):
        UnresolvedCommonJsRequireFact(
            kind=CommonJsRequireKind.SIDE_EFFECT,
            module="pkg",
            local_name="value",
            source_path="module.js",
            span=span,
        )
    with pytest.raises(ValidationError):
        UnresolvedCommonJsExportFact(
            kind=CommonJsExportKind.NAMED,
            local_name="value",
            source_path="module.js",
            span=span,
        )
    with pytest.raises(ValidationError):
        UnresolvedEsmReExportFact(
            kind=EsmReExportKind.STAR,
            module="pkg",
            imported_name="*",
            exported_name="wrong",
            source_path="module.js",
            span=span,
        )
    with pytest.raises(ValidationError, match="cannot contain"):
        UnresolvedCommonJsRequireFact(
            kind=CommonJsRequireKind.SIDE_EFFECT,
            module="pkg",
            source_path="../module.js",
            span=span,
        )

    rendered = canonical_index_json(RepositoryIndexResult(graph=GraphSnapshot()))
    assert '"commonjs_requires"' not in rendered
    assert '"commonjs_exports"' not in rendered
    assert '"esm_reexports"' not in rendered
    parsed = parse_index_json(rendered)
    assert parsed.commonjs_requires == ()
    assert parsed.commonjs_exports == ()
    assert parsed.esm_reexports == ()


def test_m21b_isolated_partial_gold_matches_semantics_and_repeated_generation() -> None:
    fixture = PROJECT_ROOT / "harness" / "fixtures" / "typescript_frontend"
    repository = fixture / "m2-1b-repo"
    expected_bytes = (fixture / "m2-1b-graph.json").read_bytes()

    first = canonical_index_json(index_repository(repository, RuntimeConfig())).encode()
    second = canonical_index_json(index_repository(repository, RuntimeConfig())).encode()
    result = parse_index_json(expected_bytes.decode())

    assert first == second == expected_bytes
    assert b"\r" not in expected_bytes
    assert str(repository).encode() not in expected_bytes
    assert not (repository / "executed.txt").exists()
    assert {node.kind for node in result.graph.nodes} >= {
        NodeKind.INTERFACE,
        NodeKind.TYPE_ALIAS,
        NodeKind.ENUM,
    }
    interface = _node(
        ExtractionResult(nodes=result.graph.nodes),
        "src.exports.Profile",
    )
    assert interface.id == "interface:077f74123649e1c67015"
    assert interface.span == SourceSpan(
        start_line=6,
        end_line=8,
        start_column=7,
        end_column=1,
    )
    assert [fact.module for fact in result.commonjs_requires] == ["setup", "./client"]
    assert [fact.kind for fact in result.esm_reexports] == [
        EsmReExportKind.NAMED,
        EsmReExportKind.NAMED,
        EsmReExportKind.NAMED,
        EsmReExportKind.STAR,
        EsmReExportKind.NAMESPACE,
    ]
