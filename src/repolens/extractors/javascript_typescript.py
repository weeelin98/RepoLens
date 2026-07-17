"""Direct JavaScript and TypeScript definition and ESM syntax facts."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from repolens.extractors.base import (
    EsmExportKind,
    EsmImportKind,
    ExtractionResult,
    UnresolvedEsmExportFact,
    UnresolvedEsmImportFact,
)
from repolens.ids import normalize_repo_path, stable_node_id
from repolens.models import (
    EdgeKind,
    EvidenceKind,
    GraphEdge,
    GraphNode,
    NodeKind,
    SourceSpan,
)

_JAVASCRIPT_LANGUAGE = Language(tree_sitter_javascript.language())
_TYPESCRIPT_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
_DECLARATION_TYPES = {"function_declaration", "class_declaration"}
_VARIABLE_DECLARATION_TYPES = {"lexical_declaration", "variable_declaration"}
_SCOPE_BARRIERS = {
    "ambient_declaration",
    "arrow_function",
    "function_expression",
    "generator_function",
    "generator_function_declaration",
    "internal_module",
    "module",
}


def _normalized_source_path(path: Path) -> str:
    rendered = path.as_posix()
    if path.is_absolute() or PureWindowsPath(rendered).is_absolute():
        raise ValueError("extractor paths must be repository-relative")
    normalized = normalize_repo_path(rendered)
    if normalized == ".":
        raise ValueError("extractor path must name a file")
    return normalized


def _module_name(source_path: str) -> str:
    return ".".join(PurePosixPath(source_path).with_suffix("").parts)


def _span(node: Node) -> SourceSpan:
    return SourceSpan(
        start_line=node.start_point.row + 1,
        end_line=node.end_point.row + 1,
        start_column=node.start_point.column,
        end_column=node.end_point.column,
    )


def _node_sort_key(node: GraphNode) -> tuple[object, ...]:
    span = node.span
    return (
        span.start_line if span else 0,
        span.start_column if span and span.start_column is not None else -1,
        node.qualified_name or "",
        node.kind.value,
        node.id,
    )


def _has_type_modifier(node: Node) -> bool:
    return any(not child.is_named and child.type == "type" for child in node.children)


class _SyntaxVisitor:
    def __init__(
        self,
        source: bytes,
        source_path: str,
        language: str,
        module_node: GraphNode,
    ) -> None:
        self._source = source
        self._source_path = source_path
        self._language = language
        self._scopes = [module_node]
        self.nodes: list[GraphNode] = [module_node]
        self.edges: list[GraphEdge] = []
        self.imports: list[UnresolvedEsmImportFact] = []
        self.exports: list[UnresolvedEsmExportFact] = []

    def visit_program(self, root: Node) -> None:
        for child in root.named_children:
            self._visit(child)

    def _visit(self, node: Node) -> None:
        if node.has_error or node.is_error or node.is_missing:
            return
        if node.type == "import_statement":
            self._visit_import(node)
            return
        if node.type == "export_statement":
            self._visit_export(node)
            return
        if node.type == "function_declaration":
            self._visit_named_definition(node, NodeKind.FUNCTION)
            return
        if node.type == "class_declaration":
            self._visit_named_definition(node, NodeKind.CLASS)
            return
        if node.type in _VARIABLE_DECLARATION_TYPES:
            self._visit_variable_declaration(node)
            return
        if node.type == "method_definition" or node.type in _SCOPE_BARRIERS:
            return
        for child in node.named_children:
            self._visit(child)

    def _visit_named_definition(self, syntax_node: Node, kind: NodeKind) -> None:
        name_node = syntax_node.child_by_field_name("name")
        if name_node is None or name_node.type not in {"identifier", "type_identifier"}:
            return
        definition = self._add_definition(syntax_node, name_node, kind)
        self._scopes.append(definition)
        if kind is NodeKind.CLASS:
            body = syntax_node.child_by_field_name("body")
            if body is not None:
                for child in body.named_children:
                    if child.type == "method_definition":
                        self._visit_method(child)
        else:
            body = syntax_node.child_by_field_name("body")
            if body is not None:
                for child in body.named_children:
                    self._visit(child)
        self._scopes.pop()

    def _visit_method(self, syntax_node: Node) -> None:
        name_node = syntax_node.child_by_field_name("name")
        if name_node is None or name_node.type not in {"identifier", "property_identifier"}:
            return
        name = self._text(name_node)
        is_accessor = any(child.type in {"get", "set"} for child in syntax_node.children)
        is_generator = any(child.type == "*" for child in syntax_node.children)
        if name == "constructor" or is_accessor or is_generator:
            return
        definition = self._add_definition(syntax_node, name_node, NodeKind.METHOD)
        self._scopes.append(definition)
        body = syntax_node.child_by_field_name("body")
        if body is not None:
            for child in body.named_children:
                self._visit(child)
        self._scopes.pop()

    def _visit_variable_declaration(self, declaration: Node) -> None:
        for child in declaration.named_children:
            if child.type != "variable_declarator":
                continue
            name_node = child.child_by_field_name("name")
            value_node = child.child_by_field_name("value")
            if (
                name_node is None
                or name_node.type != "identifier"
                or value_node is None
                or value_node.type != "arrow_function"
                or value_node.has_error
            ):
                continue
            definition = self._add_definition(child, name_node, NodeKind.FUNCTION)
            self._scopes.append(definition)
            body = value_node.child_by_field_name("body")
            if body is not None and body.type == "statement_block":
                for body_child in body.named_children:
                    self._visit(body_child)
            self._scopes.pop()

    def _add_definition(self, syntax_node: Node, name_node: Node, kind: NodeKind) -> GraphNode:
        parent = self._scopes[-1]
        if parent.qualified_name is None:
            raise ValueError("definition parent must have a qualified name")
        name = self._text(name_node)
        qualified_name = f"{parent.qualified_name}.{name}"
        span = _span(syntax_node)
        definition = GraphNode(
            id=stable_node_id(
                kind,
                source_path=self._source_path,
                qualified_name=qualified_name,
                start_line=span.start_line,
                disambiguator=f"column:{span.start_column}",
            ),
            kind=kind,
            label=name,
            language=self._language,
            source_path=self._source_path,
            span=span,
            qualified_name=qualified_name,
        )
        self.nodes.append(definition)
        self.edges.append(
            GraphEdge(
                source_id=parent.id,
                target_id=definition.id,
                relation=EdgeKind.CONTAINS,
                evidence_kind=EvidenceKind.SYNTAX_DIRECT,
                confidence=1.0,
                source_path=self._source_path,
                span=span,
            )
        )
        return definition

    def _visit_import(self, statement: Node) -> None:
        if _has_type_modifier(statement):
            return
        source_node = statement.child_by_field_name("source")
        if source_node is None:
            return
        module = self._string_value(source_node)
        if not module:
            return
        clause = next(
            (child for child in statement.named_children if child.type == "import_clause"),
            None,
        )
        if clause is None:
            self.imports.append(
                UnresolvedEsmImportFact(
                    kind=EsmImportKind.SIDE_EFFECT,
                    module=module,
                    source_path=self._source_path,
                    span=_span(source_node),
                )
            )
            return
        for child in clause.named_children:
            if child.type == "identifier":
                local_name = self._text(child)
                self.imports.append(
                    UnresolvedEsmImportFact(
                        kind=EsmImportKind.DEFAULT,
                        module=module,
                        imported_name="default",
                        local_name=local_name,
                        source_path=self._source_path,
                        span=_span(child),
                    )
                )
            elif child.type == "namespace_import":
                local_node = next(
                    (item for item in child.named_children if item.type == "identifier"),
                    None,
                )
                if local_node is not None:
                    self.imports.append(
                        UnresolvedEsmImportFact(
                            kind=EsmImportKind.NAMESPACE,
                            module=module,
                            imported_name="*",
                            local_name=self._text(local_node),
                            source_path=self._source_path,
                            span=_span(child),
                        )
                    )
            elif child.type == "named_imports":
                for specifier in child.named_children:
                    if specifier.type == "import_specifier" and not _has_type_modifier(specifier):
                        self._add_named_import(module, specifier)

    def _add_named_import(self, module: str, specifier: Node) -> None:
        imported_node = specifier.child_by_field_name("name")
        if imported_node is None:
            return
        local_node = specifier.child_by_field_name("alias") or imported_node
        self.imports.append(
            UnresolvedEsmImportFact(
                kind=EsmImportKind.NAMED,
                module=module,
                imported_name=self._text(imported_node),
                local_name=self._text(local_node),
                source_path=self._source_path,
                span=_span(specifier),
            )
        )

    def _visit_export(self, statement: Node) -> None:
        if statement.child_by_field_name("source") is not None:
            return
        if _has_type_modifier(statement):
            return
        is_default = any(child.type == "default" for child in statement.children)
        declaration = statement.child_by_field_name("declaration")
        if declaration is None:
            declaration = next(
                (
                    child
                    for child in statement.named_children
                    if child.type in _DECLARATION_TYPES | _VARIABLE_DECLARATION_TYPES
                ),
                None,
            )
        if declaration is not None:
            self._add_declaration_exports(declaration, is_default)
            self._visit(declaration)
            return
        export_clause = next(
            (child for child in statement.named_children if child.type == "export_clause"),
            None,
        )
        if export_clause is None:
            return
        for specifier in export_clause.named_children:
            if specifier.type != "export_specifier" or _has_type_modifier(specifier):
                continue
            local_node = specifier.child_by_field_name("name")
            if local_node is None:
                continue
            exported_node = specifier.child_by_field_name("alias") or local_node
            exported_name = self._text(exported_node)
            self.exports.append(
                UnresolvedEsmExportFact(
                    kind=EsmExportKind.LIST,
                    exported_name=exported_name,
                    local_name=self._text(local_node),
                    is_default=exported_name == "default",
                    source_path=self._source_path,
                    span=_span(specifier),
                )
            )

    def _add_declaration_exports(self, declaration: Node, is_default: bool) -> None:
        if declaration.type in _DECLARATION_TYPES:
            name_node = declaration.child_by_field_name("name")
            if name_node is not None and name_node.type in {"identifier", "type_identifier"}:
                self._append_declaration_export(name_node, declaration, is_default)
            return
        for child in declaration.named_children:
            if child.type != "variable_declarator":
                continue
            name_node = child.child_by_field_name("name")
            value_node = child.child_by_field_name("value")
            if (
                name_node is not None
                and name_node.type == "identifier"
                and value_node is not None
                and value_node.type == "arrow_function"
            ):
                self._append_declaration_export(name_node, child, is_default)

    def _append_declaration_export(
        self,
        name_node: Node,
        syntax_node: Node,
        is_default: bool,
    ) -> None:
        local_name = self._text(name_node)
        self.exports.append(
            UnresolvedEsmExportFact(
                kind=EsmExportKind.DECLARATION,
                exported_name="default" if is_default else local_name,
                local_name=local_name,
                is_default=is_default,
                source_path=self._source_path,
                span=_span(syntax_node),
            )
        )

    def _text(self, node: Node) -> str:
        return self._source[node.start_byte : node.end_byte].decode("utf-8")

    def _string_value(self, node: Node) -> str:
        fragments = [child for child in node.named_children if child.type == "string_fragment"]
        if fragments:
            return "".join(self._text(fragment) for fragment in fragments)
        rendered = self._text(node)
        return rendered[1:-1] if len(rendered) >= 2 else rendered


def _first_error(node: Node) -> Node | None:
    candidates: list[Node] = []
    if node.is_error or node.is_missing:
        candidates.append(node)
    for child in node.children:
        if child.has_error or child.is_error or child.is_missing:
            error = _first_error(child)
            if error is not None:
                candidates.append(error)
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item.start_byte, item.end_byte))


class JavaScriptTypeScriptExtractor:
    """Extract basic JS/TS definitions and unresolved local ESM syntax."""

    @property
    def extensions(self) -> frozenset[str]:
        return frozenset({".js", ".ts"})

    @property
    def filenames(self) -> frozenset[str]:
        return frozenset()

    def extract(self, path: Path, source: str) -> ExtractionResult:
        source_path = _normalized_source_path(path)
        suffix = path.suffix.casefold()
        if suffix == ".js":
            language_name = "javascript"
            language = _JAVASCRIPT_LANGUAGE
        elif suffix == ".ts":
            language_name = "typescript"
            language = _TYPESCRIPT_LANGUAGE
        else:
            raise ValueError("JavaScriptTypeScriptExtractor supports only .js and .ts")

        source_bytes = source.encode("utf-8")
        tree = Parser(language).parse(source_bytes)
        root = tree.root_node
        module_name = _module_name(source_path)
        module_span = _span(root)
        module_node = GraphNode(
            id=stable_node_id(
                NodeKind.MODULE,
                source_path=source_path,
                qualified_name=module_name,
                start_line=module_span.start_line,
                disambiguator=f"column:{module_span.start_column}",
            ),
            kind=NodeKind.MODULE,
            label=module_name,
            language=language_name,
            source_path=source_path,
            span=module_span,
            qualified_name=module_name,
        )
        visitor = _SyntaxVisitor(source_bytes, source_path, language_name, module_node)
        visitor.visit_program(root)
        first_error = _first_error(root)
        diagnostics: tuple[str, ...] = ()
        if first_error is not None:
            diagnostics = (
                f"tree_sitter_syntax_error:{source_path}:"
                f"{first_error.start_point.row + 1}:{first_error.start_point.column}",
            )
        return ExtractionResult(
            nodes=tuple(sorted(visitor.nodes, key=_node_sort_key)),
            edges=tuple(sorted(visitor.edges, key=GraphEdge.sort_key)),
            esm_imports=tuple(sorted(visitor.imports, key=UnresolvedEsmImportFact.sort_key)),
            esm_exports=tuple(sorted(visitor.exports, key=UnresolvedEsmExportFact.sort_key)),
            diagnostics=diagnostics,
        )
