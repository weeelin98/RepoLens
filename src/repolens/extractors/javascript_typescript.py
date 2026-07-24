"""Direct JavaScript and TypeScript definition and ESM syntax facts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from repolens.extractors.base import (
    CommonJsExportKind,
    CommonJsRequireKind,
    EsmExportKind,
    EsmImportKind,
    EsmReExportKind,
    ExtractionResult,
    JavaScriptCallKind,
    UnresolvedCommonJsExportFact,
    UnresolvedCommonJsRequireFact,
    UnresolvedEsmExportFact,
    UnresolvedEsmImportFact,
    UnresolvedEsmReExportFact,
    UnresolvedJavaScriptCallFact,
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
_JSX_LANGUAGE = _JAVASCRIPT_LANGUAGE
_TYPESCRIPT_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
_TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())
_DECLARATION_TYPES = {"function_declaration", "class_declaration"}
_TYPESCRIPT_DECLARATION_KINDS = {
    "interface_declaration": NodeKind.INTERFACE,
    "type_alias_declaration": NodeKind.TYPE_ALIAS,
    "enum_declaration": NodeKind.ENUM,
}
_VARIABLE_DECLARATION_TYPES = {"lexical_declaration", "variable_declaration"}
_PROGRAM_VAR_SCOPE_BARRIERS = {
    "abstract_class_declaration",
    "ambient_declaration",
    "arrow_function",
    "class_declaration",
    "function_declaration",
    "function_expression",
    "generator_function",
    "generator_function_declaration",
    "internal_module",
    "method_definition",
    "module",
}
_SCOPE_BARRIERS = {
    "ambient_declaration",
    "arrow_function",
    "function_expression",
    "generator_function",
    "generator_function_declaration",
    "internal_module",
    "module",
}
_CALL_SCOPE_BARRIERS = {
    "abstract_class_declaration",
    "ambient_declaration",
    "class",
    "class_expression",
    "class_static_block",
    "decorator",
    "generator_function",
    "generator_function_declaration",
    "interface_declaration",
    "internal_module",
    "module",
    "object_pattern",
    "type_alias_declaration",
}
_CALL_OWNER_KINDS = {
    NodeKind.MODULE,
    NodeKind.FUNCTION,
    NodeKind.METHOD,
    NodeKind.REACT_COMPONENT,
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


def _syntax_key(node: Node) -> tuple[int, int, str]:
    return (node.start_byte, node.end_byte, node.type)


def _has_type_modifier(node: Node) -> bool:
    return any(not child.is_named and child.type == "type" for child in node.children)


@dataclass(frozen=True)
class _ReactImportEvidence:
    has_runtime_binding: bool = False
    object_bindings: frozenset[str] = frozenset()
    component_bindings: frozenset[str] = frozenset()
    pure_component_bindings: frozenset[str] = frozenset()


def _is_component_name(name: str) -> bool:
    return (
        bool(name)
        and name.isascii()
        and "A" <= name[0] <= "Z"
        and all(character.isalpha() or character.isdigit() for character in name)
    )


def _is_top_level_declaration(node: Node) -> bool:
    parent = node.parent
    if parent is None:
        return False
    if parent.type == "program":
        return True
    return (
        parent.type == "export_statement"
        and parent.parent is not None
        and parent.parent.type == "program"
    )


def _is_top_level_declarator(node: Node) -> bool:
    declaration = node.parent
    if declaration is None or declaration.type not in _VARIABLE_DECLARATION_TYPES:
        return False
    parent = declaration.parent
    if parent is None:
        return False
    if parent.type == "program":
        return True
    return (
        parent.type == "export_statement"
        and parent.parent is not None
        and parent.parent.type == "program"
    )


def _has_unnamed_token(node: Node, *types: str) -> bool:
    expected = set(types)
    return any(not child.is_named and child.type in expected for child in node.children)


def _jsx_evidence_expression(node: Node | None) -> bool:
    while node is not None and node.type == "parenthesized_expression":
        children = node.named_children
        if len(children) != 1:
            return False
        node = children[0]
    return node is not None and node.type in {"jsx_element", "jsx_self_closing_element"}


def _has_direct_jsx_return(body: Node | None) -> bool:
    if body is None or body.type != "statement_block":
        return False
    returns = [child for child in body.named_children if child.type == "return_statement"]
    if len(returns) != 1:
        return False
    values = returns[0].named_children
    return len(values) == 1 and _jsx_evidence_expression(values[0])


def _is_function_component(
    syntax_node: Node,
    name: str,
    react_imports: _ReactImportEvidence,
) -> bool:
    return (
        react_imports.has_runtime_binding
        and _is_component_name(name)
        and _is_top_level_declaration(syntax_node)
        and not _has_unnamed_token(syntax_node, "async", "*")
        and _has_direct_jsx_return(syntax_node.child_by_field_name("body"))
    )


def _is_arrow_component(
    declarator: Node,
    arrow: Node,
    name: str,
    react_imports: _ReactImportEvidence,
) -> bool:
    if (
        not react_imports.has_runtime_binding
        or not _is_component_name(name)
        or not _is_top_level_declarator(declarator)
        or _has_unnamed_token(arrow, "async")
    ):
        return False
    body = arrow.child_by_field_name("body")
    if body is None:
        return False
    return (
        _has_direct_jsx_return(body)
        if body.type == "statement_block"
        else (_jsx_evidence_expression(body))
    )


def _class_runtime_base(
    syntax_node: Node,
    source: bytes,
    react_imports: _ReactImportEvidence,
) -> bool:
    heritage = next(
        (child for child in syntax_node.named_children if child.type == "class_heritage"),
        None,
    )
    if heritage is None:
        return False
    extends = next(
        (child for child in heritage.named_children if child.type == "extends_clause"),
        None,
    )
    value = (
        extends.child_by_field_name("value")
        if extends is not None
        else next(iter(heritage.named_children), None)
    )
    if value is None:
        return False
    if value.type == "identifier":
        local_name = _source_text(source, value)
        return local_name in (
            react_imports.component_bindings | react_imports.pure_component_bindings
        )
    if value.type != "member_expression":
        return False
    object_node = value.child_by_field_name("object")
    property_node = value.child_by_field_name("property")
    return (
        object_node is not None
        and object_node.type == "identifier"
        and _source_text(source, object_node) in react_imports.object_bindings
        and property_node is not None
        and property_node.type == "property_identifier"
        and _source_text(source, property_node) in {"Component", "PureComponent"}
    )


def _is_class_component(
    syntax_node: Node,
    name: str,
    source: bytes,
    react_imports: _ReactImportEvidence,
    class_components_enabled: bool,
) -> bool:
    if (
        not class_components_enabled
        or not react_imports.has_runtime_binding
        or not _is_component_name(name)
        or not _is_top_level_declaration(syntax_node)
        or not _class_runtime_base(syntax_node, source, react_imports)
    ):
        return False
    body = syntax_node.child_by_field_name("body")
    if body is None:
        return False
    render_members = []
    for member in body.named_children:
        name_node = member.child_by_field_name("name")
        if name_node is not None and _source_text(source, name_node) == "render":
            render_members.append(member)
    if len(render_members) != 1:
        return False
    render = render_members[0]
    return (
        render.type == "method_definition"
        and not _has_unnamed_token(
            render,
            "static",
            "async",
            "*",
            "get",
            "set",
            "abstract",
            "?",
        )
        and _has_direct_jsx_return(render.child_by_field_name("body"))
    )


class _SyntaxVisitor:
    def __init__(
        self,
        source: bytes,
        source_path: str,
        language: str,
        module_node: GraphNode,
        commonjs_ambiguous_names: frozenset[str],
        commonjs_enabled: bool,
        component_classification_enabled: bool,
        class_components_enabled: bool,
        react_imports: _ReactImportEvidence,
    ) -> None:
        self._source = source
        self._source_path = source_path
        self._language = language
        self._scopes = [module_node]
        self.nodes: list[GraphNode] = [module_node]
        self.edges: list[GraphEdge] = []
        self.imports: list[UnresolvedEsmImportFact] = []
        self.exports: list[UnresolvedEsmExportFact] = []
        self.commonjs_requires: list[UnresolvedCommonJsRequireFact] = []
        self.commonjs_exports: list[UnresolvedCommonJsExportFact] = []
        self.reexports: list[UnresolvedEsmReExportFact] = []
        self.call_owners: dict[tuple[int, int, str], GraphNode] = {}
        self._commonjs_ambiguous_names = commonjs_ambiguous_names
        self._commonjs_enabled = commonjs_enabled
        self._component_classification_enabled = component_classification_enabled
        self._class_components_enabled = class_components_enabled
        self._react_imports = react_imports

    def visit_program(self, root: Node) -> None:
        for child in root.named_children:
            if child.has_error or child.is_error or child.is_missing:
                continue
            if self._commonjs_enabled:
                self._visit_top_level_commonjs(child)
            kind = _TYPESCRIPT_DECLARATION_KINDS.get(child.type)
            if kind is not None:
                self._visit_typescript_declaration(child, kind)
            else:
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
        if node.type in _TYPESCRIPT_DECLARATION_KINDS:
            return
        for child in node.named_children:
            self._visit(child)

    def _visit_named_definition(self, syntax_node: Node, kind: NodeKind) -> None:
        name_node = syntax_node.child_by_field_name("name")
        if name_node is None or name_node.type not in {"identifier", "type_identifier"}:
            return
        name = self._text(name_node)
        selected_kind = kind
        if self._component_classification_enabled and (
            (
                kind is NodeKind.FUNCTION
                and _is_function_component(
                    syntax_node,
                    name,
                    self._react_imports,
                )
            )
            or (
                kind is NodeKind.CLASS
                and _is_class_component(
                    syntax_node,
                    name,
                    self._source,
                    self._react_imports,
                    self._class_components_enabled,
                )
            )
        ):
            selected_kind = NodeKind.REACT_COMPONENT
        definition = self._add_definition(syntax_node, name_node, selected_kind)
        self._scopes.append(definition)
        if syntax_node.type == "class_declaration":
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
            selected_kind = NodeKind.FUNCTION
            if self._component_classification_enabled and _is_arrow_component(
                child,
                value_node,
                self._text(name_node),
                self._react_imports,
            ):
                selected_kind = NodeKind.REACT_COMPONENT
            definition = self._add_definition(child, name_node, selected_kind)
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
        if kind in _CALL_OWNER_KINDS:
            self.call_owners[_syntax_key(syntax_node)] = definition
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

    def _visit_typescript_declaration(self, syntax_node: Node, kind: NodeKind) -> None:
        if syntax_node.type == "enum_declaration" and any(
            not child.is_named and child.type == "const" for child in syntax_node.children
        ):
            return
        name_node = syntax_node.child_by_field_name("name")
        if name_node is None or name_node.type not in {"identifier", "type_identifier"}:
            return
        self._add_definition(syntax_node, name_node, kind)

    def _visit_top_level_commonjs(self, node: Node) -> None:
        if node.type == "expression_statement":
            expression = next(iter(node.named_children), None)
            if expression is None:
                return
            if expression.type == "call_expression":
                require_fact = self._commonjs_require_fact(expression, None)
                if require_fact is not None:
                    self.commonjs_requires.append(require_fact)
            elif expression.type == "assignment_expression":
                export_fact = self._commonjs_export_fact(expression)
                if export_fact is not None:
                    self.commonjs_exports.append(export_fact)
            return
        if node.type not in _VARIABLE_DECLARATION_TYPES:
            return
        for declarator in node.named_children:
            if declarator.type != "variable_declarator":
                continue
            name_node = declarator.child_by_field_name("name")
            value_node = declarator.child_by_field_name("value")
            if (
                name_node is None
                or name_node.type != "identifier"
                or value_node is None
                or value_node.type != "call_expression"
            ):
                continue
            require_fact = self._commonjs_require_fact(value_node, self._text(name_node))
            if require_fact is not None:
                self.commonjs_requires.append(require_fact)

    def _commonjs_require_fact(
        self,
        call: Node,
        local_name: str | None,
    ) -> UnresolvedCommonJsRequireFact | None:
        if "require" in self._commonjs_ambiguous_names:
            return None
        function = call.child_by_field_name("function")
        arguments = call.child_by_field_name("arguments")
        if (
            function is None
            or function.type != "identifier"
            or self._text(function) != "require"
            or arguments is None
            or any(
                child.type in {"?.", "optional_chain", "type_arguments"} for child in call.children
            )
        ):
            return None
        values = arguments.named_children
        if len(values) != 1 or values[0].type != "string":
            return None
        module = self._string_value(values[0])
        if not module:
            return None
        return UnresolvedCommonJsRequireFact(
            kind=(
                CommonJsRequireKind.SIDE_EFFECT
                if local_name is None
                else CommonJsRequireKind.BINDING
            ),
            module=module,
            local_name=local_name,
            source_path=self._source_path,
            span=_span(call),
        )

    def _commonjs_export_fact(
        self,
        assignment: Node,
    ) -> UnresolvedCommonJsExportFact | None:
        if not any(not child.is_named and child.type == "=" for child in assignment.children):
            return None
        left = assignment.child_by_field_name("left")
        right = assignment.child_by_field_name("right")
        if left is None or right is None or right.type != "identifier":
            return None
        receiver = self._commonjs_export_receiver(left)
        if receiver is None:
            return None
        required_name, kind, exported_name = receiver
        if required_name in self._commonjs_ambiguous_names:
            return None
        return UnresolvedCommonJsExportFact(
            kind=kind,
            exported_name=exported_name,
            local_name=self._text(right),
            source_path=self._source_path,
            span=_span(assignment),
        )

    def _commonjs_export_receiver(
        self,
        node: Node,
    ) -> tuple[str, CommonJsExportKind, str | None] | None:
        if node.type != "member_expression":
            return None
        object_node = node.child_by_field_name("object")
        property_node = node.child_by_field_name("property")
        if (
            object_node is None
            or property_node is None
            or property_node.type != "property_identifier"
        ):
            return None
        property_name = self._text(property_node)
        if (
            object_node.type == "identifier"
            and self._text(object_node) == "module"
            and property_name == "exports"
        ):
            return "module", CommonJsExportKind.MODULE_EXPORTS, None
        if object_node.type == "identifier" and self._text(object_node) == "exports":
            return "exports", CommonJsExportKind.NAMED, property_name
        if object_node.type != "member_expression":
            return None
        base = object_node.child_by_field_name("object")
        middle = object_node.child_by_field_name("property")
        if (
            base is None
            or base.type != "identifier"
            or self._text(base) != "module"
            or middle is None
            or middle.type != "property_identifier"
            or self._text(middle) != "exports"
        ):
            return None
        return "module", CommonJsExportKind.NAMED, property_name

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
        source_node = statement.child_by_field_name("source")
        if source_node is not None:
            self._visit_reexport(statement, source_node)
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
                    if child.type
                    in _DECLARATION_TYPES
                    | _VARIABLE_DECLARATION_TYPES
                    | set(_TYPESCRIPT_DECLARATION_KINDS)
                ),
                None,
            )
        if declaration is not None:
            declaration_kind = _TYPESCRIPT_DECLARATION_KINDS.get(declaration.type)
            if declaration_kind is not None:
                if declaration_kind is NodeKind.ENUM and not any(
                    not child.is_named and child.type == "const" for child in declaration.children
                ):
                    self._add_declaration_exports(declaration, is_default)
                self._visit_typescript_declaration(declaration, declaration_kind)
            else:
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

    def _visit_reexport(self, statement: Node, source_node: Node) -> None:
        if _has_type_modifier(statement) or source_node.type != "string":
            return
        if any(
            child.type in {"assert_clause", "attributes", "import_attribute"}
            for child in statement.named_children
        ):
            return
        module = self._string_value(source_node)
        if not module:
            return
        export_clause = next(
            (child for child in statement.named_children if child.type == "export_clause"),
            None,
        )
        if export_clause is not None:
            for specifier in export_clause.named_children:
                if specifier.type != "export_specifier" or _has_type_modifier(specifier):
                    continue
                imported_node = specifier.child_by_field_name("name")
                if imported_node is None or imported_node.type != "identifier":
                    continue
                exported_node = specifier.child_by_field_name("alias") or imported_node
                if exported_node.type != "identifier":
                    continue
                self.reexports.append(
                    UnresolvedEsmReExportFact(
                        kind=EsmReExportKind.NAMED,
                        module=module,
                        imported_name=self._text(imported_node),
                        exported_name=self._text(exported_node),
                        source_path=self._source_path,
                        span=_span(specifier),
                    )
                )
            return
        namespace = next(
            (child for child in statement.named_children if child.type == "namespace_export"),
            None,
        )
        if namespace is not None:
            name_node = namespace.child_by_field_name("name")
            if name_node is None:
                name_node = next(iter(namespace.named_children), None)
            if name_node is not None:
                self.reexports.append(
                    UnresolvedEsmReExportFact(
                        kind=EsmReExportKind.NAMESPACE,
                        module=module,
                        imported_name="*",
                        exported_name=self._text(name_node),
                        source_path=self._source_path,
                        span=_span(namespace),
                    )
                )
            return
        star = next(
            (child for child in statement.children if not child.is_named and child.type == "*"),
            None,
        )
        if star is not None:
            self.reexports.append(
                UnresolvedEsmReExportFact(
                    kind=EsmReExportKind.STAR,
                    module=module,
                    imported_name="*",
                    source_path=self._source_path,
                    span=_span(star),
                )
            )

    def _add_declaration_exports(self, declaration: Node, is_default: bool) -> None:
        if declaration.type in _DECLARATION_TYPES | {"enum_declaration"}:
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
        return _static_string_value(self._source, node)


class _CallCollector:
    def __init__(
        self,
        source: bytes,
        source_path: str,
        module_node: GraphNode,
        owners: dict[tuple[int, int, str], GraphNode],
    ) -> None:
        self._source = source
        self._source_path = source_path
        self._module_node = module_node
        self._owners = owners
        self.calls: list[UnresolvedJavaScriptCallFact] = []

    def collect_program(self, root: Node) -> None:
        for child in root.named_children:
            if child.has_error or child.is_error or child.is_missing:
                continue
            self._visit(child, self._module_node)

    def _visit(self, node: Node, owner: GraphNode) -> None:
        if node.has_error or node.is_error or node.is_missing:
            return
        if node.type in {"import_statement", "import_require_clause"}:
            return
        if node.type == "function_declaration":
            self._visit_supported_definition(node)
            return
        if node.type == "class_declaration":
            self._visit_class(node)
            return
        if node.type in _VARIABLE_DECLARATION_TYPES:
            self._visit_variable_declaration(node, owner)
            return
        if node.type == "method_definition":
            self._visit_supported_definition(node)
            return
        if node.type == "arrow_function":
            if self._is_direct_callback(node):
                self._visit_anonymous_callable(node, owner)
            return
        if node.type == "function_expression":
            if node.child_by_field_name("name") is None and self._is_direct_callback(node):
                self._visit_anonymous_callable(node, owner)
            return
        if node.type in _CALL_SCOPE_BARRIERS or node.type in _TYPESCRIPT_DECLARATION_KINDS:
            return
        if node.type == "call_expression":
            fact = self._call_fact(node, owner)
            if fact is not None:
                self.calls.append(fact)
        for child in node.named_children:
            if child.type != "type_arguments":
                self._visit(child, owner)

    def _visit_supported_definition(self, node: Node) -> None:
        owner = self._owners.get(_syntax_key(node))
        if owner is None or owner.kind not in _CALL_OWNER_KINDS:
            return
        parameters = node.child_by_field_name("parameters")
        if parameters is not None:
            self._visit(parameters, owner)
        body = node.child_by_field_name("body")
        if body is not None:
            self._visit(body, owner)

    def _visit_class(self, node: Node) -> None:
        body = node.child_by_field_name("body")
        if body is None or body.has_error:
            return
        for member in body.named_children:
            if member.type == "method_definition":
                owner = self._owners.get(_syntax_key(member))
                if owner is not None and owner.kind is NodeKind.METHOD:
                    parameters = member.child_by_field_name("parameters")
                    if parameters is not None:
                        self._visit(parameters, owner)
                    method_body = member.child_by_field_name("body")
                    if method_body is not None:
                        self._visit(method_body, owner)

    def _visit_variable_declaration(self, declaration: Node, owner: GraphNode) -> None:
        for declarator in declaration.named_children:
            if declarator.type != "variable_declarator" or declarator.has_error:
                continue
            value = declarator.child_by_field_name("value")
            if value is None:
                continue
            if value.type == "arrow_function":
                arrow_owner = self._owners.get(_syntax_key(declarator))
                if arrow_owner is not None and arrow_owner.kind in _CALL_OWNER_KINDS:
                    self._visit_anonymous_callable(value, arrow_owner)
            elif value.type == "function_expression":
                continue
            else:
                self._visit(value, owner)

    def _is_direct_callback(self, node: Node) -> bool:
        return node.parent is not None and node.parent.type == "arguments"

    def _visit_anonymous_callable(self, node: Node, owner: GraphNode) -> None:
        parameters = node.child_by_field_name("parameters")
        if parameters is not None:
            self._visit(parameters, owner)
        body = node.child_by_field_name("body")
        if body is not None:
            self._visit(body, owner)

    def _call_fact(
        self,
        call: Node,
        owner: GraphNode,
    ) -> UnresolvedJavaScriptCallFact | None:
        function = call.child_by_field_name("function")
        arguments = call.child_by_field_name("arguments")
        if (
            function is None
            or function.has_error
            or function.is_error
            or function.is_missing
            or arguments is None
            or arguments.type != "arguments"
        ):
            return None
        normalized = self._normalized_callee(function)
        if normalized is None:
            return None
        kind, callee = normalized
        if kind is JavaScriptCallKind.IDENTIFIER and callee == "require":
            return None
        return UnresolvedJavaScriptCallFact(
            kind=kind,
            callee=callee,
            enclosing_id=owner.id,
            is_optional=self._has_optional_syntax(call, function),
            source_path=self._source_path,
            span=_span(call),
        )

    def _normalized_callee(
        self,
        node: Node,
    ) -> tuple[JavaScriptCallKind, str] | None:
        if node.type == "identifier":
            return JavaScriptCallKind.IDENTIFIER, _source_text(self._source, node)
        if node.type != "member_expression":
            return None
        segments = self._member_segments(node)
        if segments is None:
            return None
        return JavaScriptCallKind.MEMBER, ".".join(segments)

    def _member_segments(self, node: Node) -> tuple[str, ...] | None:
        if node.type in {"identifier", "this", "super"}:
            return (_source_text(self._source, node),)
        if node.type != "member_expression":
            return None
        object_node = node.child_by_field_name("object")
        property_node = node.child_by_field_name("property")
        if (
            object_node is None
            or property_node is None
            or property_node.type != "property_identifier"
        ):
            return None
        prefix = self._member_segments(object_node)
        if prefix is None:
            return None
        return (*prefix, _source_text(self._source, property_node))

    def _has_optional_syntax(self, call: Node, function: Node) -> bool:
        return any(
            child.type in {"?.", "optional_chain"} for child in call.children
        ) or self._subtree_has_optional(function)

    def _subtree_has_optional(self, node: Node) -> bool:
        return node.type in {"?.", "optional_chain"} or any(
            self._subtree_has_optional(child) for child in node.children
        )


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


def _source_text(source: bytes, node: Node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _static_string_value(source: bytes, node: Node) -> str:
    rendered = _source_text(source, node)
    return rendered[1:-1] if len(rendered) >= 2 else rendered


def _pattern_binding_names(node: Node, source: bytes) -> set[str]:
    if node.type in {"identifier", "shorthand_property_identifier_pattern"}:
        return {_source_text(source, node)}
    if node.type in {"assignment_pattern", "object_assignment_pattern"}:
        left = node.child_by_field_name("left")
        return _pattern_binding_names(left, source) if left is not None else set()
    if node.type == "pair_pattern":
        value = node.child_by_field_name("value")
        return _pattern_binding_names(value, source) if value is not None else set()
    names: set[str] = set()
    for child in node.named_children:
        names.update(_pattern_binding_names(child, source))
    return names


def _import_binding_names(statement: Node, source: bytes) -> set[str]:
    if _has_type_modifier(statement):
        return set()
    require_clause = next(
        (child for child in statement.named_children if child.type == "import_require_clause"),
        None,
    )
    if require_clause is not None:
        name = next(
            (child for child in require_clause.named_children if child.type == "identifier"),
            None,
        )
        return {_source_text(source, name)} if name is not None else set()
    clause = next(
        (child for child in statement.named_children if child.type == "import_clause"),
        None,
    )
    if clause is None:
        return set()
    names: set[str] = set()
    for child in clause.named_children:
        if child.type == "identifier":
            names.add(_source_text(source, child))
        elif child.type == "namespace_import":
            names.update(
                _source_text(source, item)
                for item in child.named_children
                if item.type == "identifier"
            )
        elif child.type == "named_imports":
            for specifier in child.named_children:
                if specifier.type != "import_specifier" or _has_type_modifier(specifier):
                    continue
                local = specifier.child_by_field_name("alias")
                if local is None:
                    local = specifier.child_by_field_name("name")
                if local is not None:
                    names.add(_source_text(source, local))
    return names


def _react_import_evidence(root: Node, source: bytes) -> _ReactImportEvidence:
    has_runtime_binding = False
    object_bindings: set[str] = set()
    component_bindings: set[str] = set()
    pure_component_bindings: set[str] = set()
    for statement in root.named_children:
        if (
            statement.type != "import_statement"
            or statement.has_error
            or statement.is_error
            or statement.is_missing
            or _has_type_modifier(statement)
        ):
            continue
        source_node = statement.child_by_field_name("source")
        if (
            source_node is None
            or source_node.type != "string"
            or _static_string_value(source, source_node) != "react"
        ):
            continue
        clause = next(
            (child for child in statement.named_children if child.type == "import_clause"),
            None,
        )
        if clause is None:
            continue
        for child in clause.named_children:
            if child.type == "identifier":
                has_runtime_binding = True
                local_name = _source_text(source, child)
                if local_name == "React":
                    object_bindings.add(local_name)
            elif child.type == "namespace_import":
                local_node = next(
                    (item for item in child.named_children if item.type == "identifier"),
                    None,
                )
                if local_node is not None:
                    has_runtime_binding = True
                    local_name = _source_text(source, local_node)
                    if local_name == "React":
                        object_bindings.add(local_name)
            elif child.type == "named_imports":
                for specifier in child.named_children:
                    if specifier.type != "import_specifier" or _has_type_modifier(specifier):
                        continue
                    imported_node = specifier.child_by_field_name("name")
                    if imported_node is None or imported_node.type != "identifier":
                        continue
                    local_node = specifier.child_by_field_name("alias") or imported_node
                    if local_node.type != "identifier":
                        continue
                    has_runtime_binding = True
                    imported_name = _source_text(source, imported_node)
                    local_name = _source_text(source, local_node)
                    if imported_name == "Component":
                        component_bindings.add(local_name)
                    elif imported_name == "PureComponent":
                        pure_component_bindings.add(local_name)
    return _ReactImportEvidence(
        has_runtime_binding=has_runtime_binding,
        object_bindings=frozenset(object_bindings),
        component_bindings=frozenset(component_bindings),
        pure_component_bindings=frozenset(pure_component_bindings),
    )


def _runtime_declaration_binding_name(node: Node, source: bytes) -> str | None:
    if node.type == "enum_declaration" and any(
        not child.is_named and child.type == "const" for child in node.children
    ):
        return None
    if node.type not in {
        "abstract_class_declaration",
        "class_declaration",
        "enum_declaration",
        "function_declaration",
        "generator_function_declaration",
        "internal_module",
    }:
        return None
    name = node.child_by_field_name("name")
    return _source_text(source, name) if name is not None else None


def _program_var_binding_names(root: Node, source: bytes) -> set[str]:
    names: set[str] = set()

    def visit(node: Node) -> None:
        if node is not root and node.type in _PROGRAM_VAR_SCOPE_BARRIERS:
            return
        if node.type == "variable_declaration":
            for declarator in node.named_children:
                if declarator.type != "variable_declarator":
                    continue
                name = declarator.child_by_field_name("name")
                if name is not None:
                    names.update(_pattern_binding_names(name, source))
            return
        for child in node.named_children:
            visit(child)

    visit(root)
    return names


def _program_reassigned_names(root: Node, source: bytes) -> set[str]:
    names: set[str] = set()

    def declaration_names(node: Node) -> set[str]:
        if node.type != "lexical_declaration":
            return set()
        declared: set[str] = set()
        for declarator in node.named_children:
            if declarator.type != "variable_declarator":
                continue
            name = declarator.child_by_field_name("name")
            if name is not None:
                declared.update(_pattern_binding_names(name, source))
        return declared

    def direct_block_bindings(node: Node) -> set[str]:
        bindings: set[str] = set()
        for child in node.named_children:
            bindings.update(declaration_names(child))
            declaration_name = _runtime_declaration_binding_name(child, source)
            if declaration_name is not None:
                bindings.add(declaration_name)
            if child.type == "expression_statement":
                expression = next(iter(child.named_children), None)
                if expression is not None:
                    declaration_name = _runtime_declaration_binding_name(expression, source)
                    if declaration_name is not None:
                        bindings.add(declaration_name)
        return bindings

    def visit(node: Node, shadowed: frozenset[str]) -> None:
        if node is not root and node.type in _PROGRAM_VAR_SCOPE_BARRIERS:
            return
        nested_shadowed = set(shadowed)
        if node.type in {"statement_block", "switch_body"}:
            nested_shadowed.update(direct_block_bindings(node))
        elif node.type in {"for_in_statement", "for_statement"}:
            for child in node.named_children:
                nested_shadowed.update(declaration_names(child))
        elif node.type == "catch_clause":
            parameter = node.child_by_field_name("parameter")
            if parameter is not None:
                nested_shadowed.update(_pattern_binding_names(parameter, source))
        if node.type in {"assignment_expression", "augmented_assignment_expression"}:
            left = node.child_by_field_name("left")
            if (
                left is not None
                and left.type == "identifier"
                and _source_text(source, left) not in shadowed
            ):
                names.add(_source_text(source, left))
        elif node.type == "update_expression":
            argument = node.child_by_field_name("argument")
            if (
                argument is not None
                and argument.type == "identifier"
                and _source_text(source, argument) not in shadowed
            ):
                names.add(_source_text(source, argument))
        for child in node.named_children:
            visit(child, frozenset(nested_shadowed))

    visit(root, frozenset())
    return names


def _program_commonjs_ambiguity(root: Node, source: bytes) -> frozenset[str]:
    guarded_names = {"require", "module", "exports"}
    ambiguous = (
        _program_var_binding_names(root, source) | _program_reassigned_names(root, source)
    ) & guarded_names
    for program_child in root.named_children:
        child = program_child
        if child.type == "export_statement":
            declaration = child.child_by_field_name("declaration")
            if declaration is None:
                continue
            child = declaration
        if child.type == "import_statement":
            ambiguous.update(_import_binding_names(child, source) & guarded_names)
            continue
        if child.type in _VARIABLE_DECLARATION_TYPES:
            for declarator in child.named_children:
                if declarator.type != "variable_declarator":
                    continue
                name = declarator.child_by_field_name("name")
                if name is not None:
                    ambiguous.update(_pattern_binding_names(name, source) & guarded_names)
            continue
        declaration_name = _runtime_declaration_binding_name(child, source)
        if declaration_name in guarded_names:
            ambiguous.add(declaration_name)
            continue
        if child.type == "expression_statement":
            expression = next(iter(child.named_children), None)
            if expression is not None:
                declaration_name = _runtime_declaration_binding_name(expression, source)
                if declaration_name in guarded_names:
                    ambiguous.add(declaration_name)
                    continue
    return frozenset(ambiguous)


class JavaScriptTypeScriptExtractor:
    """Extract basic JS/TS definitions and unresolved local ESM syntax."""

    @property
    def extensions(self) -> frozenset[str]:
        return frozenset({".js", ".jsx", ".ts", ".tsx"})

    @property
    def filenames(self) -> frozenset[str]:
        return frozenset()

    def extract(self, path: Path, source: str) -> ExtractionResult:
        source_path = _normalized_source_path(path)
        suffix = path.suffix.casefold()
        if suffix == ".js":
            language_name = "javascript"
            language = _JAVASCRIPT_LANGUAGE
            component_classification_enabled = False
        elif suffix == ".jsx":
            language_name = "jsx"
            language = _JSX_LANGUAGE
            component_classification_enabled = True
        elif suffix == ".ts":
            language_name = "typescript"
            language = _TYPESCRIPT_LANGUAGE
            component_classification_enabled = False
        elif suffix == ".tsx":
            language_name = "tsx"
            language = _TSX_LANGUAGE
            component_classification_enabled = True
        else:
            raise ValueError("JavaScriptTypeScriptExtractor supports only .js, .jsx, .ts, and .tsx")

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
        first_error = _first_error(root)
        react_imports = _react_import_evidence(root, source_bytes)
        visitor = _SyntaxVisitor(
            source_bytes,
            source_path,
            language_name,
            module_node,
            _program_commonjs_ambiguity(root, source_bytes) if first_error is None else frozenset(),
            first_error is None,
            component_classification_enabled,
            component_classification_enabled and first_error is None,
            react_imports,
        )
        visitor.visit_program(root)
        call_collector = _CallCollector(
            source_bytes,
            source_path,
            module_node,
            visitor.call_owners,
        )
        call_collector.collect_program(root)
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
            commonjs_requires=tuple(
                sorted(visitor.commonjs_requires, key=UnresolvedCommonJsRequireFact.sort_key)
            ),
            commonjs_exports=tuple(
                sorted(visitor.commonjs_exports, key=UnresolvedCommonJsExportFact.sort_key)
            ),
            esm_reexports=tuple(sorted(visitor.reexports, key=UnresolvedEsmReExportFact.sort_key)),
            javascript_calls=tuple(
                sorted(call_collector.calls, key=UnresolvedJavaScriptCallFact.sort_key)
            ),
            diagnostics=diagnostics,
        )
