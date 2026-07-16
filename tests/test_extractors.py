from __future__ import annotations

from pathlib import Path

import pytest

from repolens.extractors import (
    ExtractionResult,
    Extractor,
    ExtractorRegistry,
    PythonExtractor,
)
from repolens.ids import stable_node_id
from repolens.models import (
    EdgeKind,
    EvidenceKind,
    GraphEdge,
    GraphNode,
    NodeKind,
    SourceSpan,
)


class FakeExtractor:
    def __init__(self, *extensions: str) -> None:
        self._extensions = frozenset(extensions)

    @property
    def extensions(self) -> frozenset[str]:
        return self._extensions

    def extract(self, path: Path, source: str) -> ExtractionResult:
        return ExtractionResult(diagnostics=(f"{path}:{len(source)}",))


def test_extractor_registry_behavior() -> None:
    registry = ExtractorRegistry()
    extractor = FakeExtractor("PY", ".pyi")
    registry.register(extractor)

    assert registry.for_path(Path("service.PY")) is extractor
    assert registry.for_path(Path("types.pyi")) is extractor
    assert registry.for_path(Path("README.md")) is None
    assert registry.extensions == (".py", ".pyi")


def test_extractor_registry_rejects_conflicts() -> None:
    registry = ExtractorRegistry()
    registry.register(FakeExtractor(".py"))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeExtractor("py"))


def test_extractor_registry_rejects_empty_extensions() -> None:
    with pytest.raises(ValueError, match="at least one"):
        ExtractorRegistry().register(FakeExtractor())


def expected_node(
    kind: NodeKind,
    *,
    path: str,
    qualified_name: str,
    label: str,
    span: SourceSpan,
) -> GraphNode:
    return GraphNode(
        id=stable_node_id(
            kind,
            source_path=path,
            qualified_name=qualified_name,
            start_line=span.start_line,
        ),
        kind=kind,
        label=label,
        language="python",
        source_path=path,
        span=span,
        qualified_name=qualified_name,
    )


def expected_contains(parent: GraphNode, child: GraphNode) -> GraphEdge:
    return GraphEdge(
        source_id=parent.id,
        target_id=child.id,
        relation=EdgeKind.CONTAINS,
        evidence_kind=EvidenceKind.SYNTAX_DIRECT,
        confidence=1.0,
        source_path=child.source_path,
        span=child.span,
    )


def test_python_extractor_declares_only_py_and_matches_protocol() -> None:
    extractor = PythonExtractor()
    registry = ExtractorRegistry()
    registry.register(extractor)

    assert isinstance(extractor, Extractor)
    assert extractor.extensions == frozenset({".py"})
    assert registry.for_path(Path("service.PY")) is extractor
    assert registry.for_path(Path("types.pyi")) is None


@pytest.mark.parametrize(
    ("path", "expected_name", "expected_path"),
    [
        (Path("app.py"), "app", "app.py"),
        (Path("services/user.py"), "services.user", "services/user.py"),
        (Path("services/__init__.py"), "services", "services/__init__.py"),
        (Path("__init__.py"), "<root>", "__init__.py"),
        (Path(r"services\user.py"), "services.user", "services/user.py"),
    ],
)
def test_python_module_names_and_relative_posix_paths(
    path: Path,
    expected_name: str,
    expected_path: str,
) -> None:
    span = SourceSpan(start_line=1, end_line=1, start_column=0, end_column=0)
    module = expected_node(
        NodeKind.MODULE,
        path=expected_path,
        qualified_name=expected_name,
        label=expected_name,
        span=span,
    )

    result = PythonExtractor().extract(path, "")

    assert result == ExtractionResult(nodes=(module,))


def test_extracts_top_level_function_and_async_function_with_spans() -> None:
    source = "def load():\n    return 1\n\nasync def refresh():\n    return 2\n"
    path = "services/user.py"
    module = expected_node(
        NodeKind.MODULE,
        path=path,
        qualified_name="services.user",
        label="services.user",
        span=SourceSpan(start_line=1, end_line=5, start_column=0, end_column=12),
    )
    load = expected_node(
        NodeKind.FUNCTION,
        path=path,
        qualified_name="services.user.load",
        label="load",
        span=SourceSpan(start_line=1, end_line=2, start_column=0, end_column=12),
    )
    refresh = expected_node(
        NodeKind.FUNCTION,
        path=path,
        qualified_name="services.user.refresh",
        label="refresh",
        span=SourceSpan(start_line=4, end_line=5, start_column=0, end_column=12),
    )

    result = PythonExtractor().extract(Path(path), source)

    assert result.nodes == (module, load, refresh)
    assert result.edges == tuple(
        sorted(
            (expected_contains(module, load), expected_contains(module, refresh)),
            key=GraphEdge.sort_key,
        )
    )
    assert result.diagnostics == ()


def test_extracts_class_and_multiple_direct_methods() -> None:
    source = (
        "class Service:\n"
        "    def one(self):\n"
        "        return 1\n"
        "\n"
        "    async def two(self):\n"
        "        return 2\n"
    )
    path = "services/user.py"
    module = expected_node(
        NodeKind.MODULE,
        path=path,
        qualified_name="services.user",
        label="services.user",
        span=SourceSpan(start_line=1, end_line=6, start_column=0, end_column=16),
    )
    service = expected_node(
        NodeKind.CLASS,
        path=path,
        qualified_name="services.user.Service",
        label="Service",
        span=SourceSpan(start_line=1, end_line=6, start_column=0, end_column=16),
    )
    one = expected_node(
        NodeKind.METHOD,
        path=path,
        qualified_name="services.user.Service.one",
        label="one",
        span=SourceSpan(start_line=2, end_line=3, start_column=4, end_column=16),
    )
    two = expected_node(
        NodeKind.METHOD,
        path=path,
        qualified_name="services.user.Service.two",
        label="two",
        span=SourceSpan(start_line=5, end_line=6, start_column=4, end_column=16),
    )

    result = PythonExtractor().extract(Path(path), source)

    assert result.nodes == (module, service, one, two)
    assert result.edges == tuple(
        sorted(
            (
                expected_contains(module, service),
                expected_contains(service, one),
                expected_contains(service, two),
            ),
            key=GraphEdge.sort_key,
        )
    )


def test_extracts_nested_functions_and_classes_with_nearest_parents() -> None:
    source = (
        "def outer():\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner\n"
        "\n"
        "class Outer:\n"
        "    class Inner:\n"
        "        def run(self):\n"
        "            pass\n"
    )
    path = "services/user.py"
    module = expected_node(
        NodeKind.MODULE,
        path=path,
        qualified_name="services.user",
        label="services.user",
        span=SourceSpan(start_line=1, end_line=9, start_column=0, end_column=16),
    )
    outer_function = expected_node(
        NodeKind.FUNCTION,
        path=path,
        qualified_name="services.user.outer",
        label="outer",
        span=SourceSpan(start_line=1, end_line=4, start_column=0, end_column=16),
    )
    inner_function = expected_node(
        NodeKind.FUNCTION,
        path=path,
        qualified_name="services.user.outer.inner",
        label="inner",
        span=SourceSpan(start_line=2, end_line=3, start_column=4, end_column=16),
    )
    outer_class = expected_node(
        NodeKind.CLASS,
        path=path,
        qualified_name="services.user.Outer",
        label="Outer",
        span=SourceSpan(start_line=6, end_line=9, start_column=0, end_column=16),
    )
    inner_class = expected_node(
        NodeKind.CLASS,
        path=path,
        qualified_name="services.user.Outer.Inner",
        label="Inner",
        span=SourceSpan(start_line=7, end_line=9, start_column=4, end_column=16),
    )
    run = expected_node(
        NodeKind.METHOD,
        path=path,
        qualified_name="services.user.Outer.Inner.run",
        label="run",
        span=SourceSpan(start_line=8, end_line=9, start_column=8, end_column=16),
    )

    result = PythonExtractor().extract(Path(path), source)

    assert result.nodes == (
        module,
        outer_function,
        inner_function,
        outer_class,
        inner_class,
        run,
    )
    assert result.edges == tuple(
        sorted(
            (
                expected_contains(module, outer_function),
                expected_contains(outer_function, inner_function),
                expected_contains(module, outer_class),
                expected_contains(outer_class, inner_class),
                expected_contains(inner_class, run),
            ),
            key=GraphEdge.sort_key,
        )
    )


def test_function_nested_inside_method_is_a_function() -> None:
    source = (
        "class Service:\n"
        "    def load(self):\n"
        "        def validate():\n"
        "            return True\n"
        "        return validate()\n"
    )

    result = PythonExtractor().extract(Path("service.py"), source)
    by_name = {node.qualified_name: node for node in result.nodes}

    method = by_name["service.Service.load"]
    nested = by_name["service.Service.load.validate"]
    assert method.kind is NodeKind.METHOD
    assert nested.kind is NodeKind.FUNCTION
    assert expected_contains(method, nested) in result.edges


def test_duplicate_bare_names_in_different_scopes_have_distinct_stable_ids() -> None:
    source = (
        "def first():\n"
        "    def duplicate():\n"
        "        pass\n"
        "\n"
        "def second():\n"
        "    def duplicate():\n"
        "        pass\n"
    )

    result = PythonExtractor().extract(Path("module.py"), source)
    duplicates = [node for node in result.nodes if node.label == "duplicate"]

    assert [node.qualified_name for node in duplicates] == [
        "module.first.duplicate",
        "module.second.duplicate",
    ]
    assert [node.id for node in duplicates] == [
        stable_node_id(
            NodeKind.FUNCTION,
            source_path="module.py",
            qualified_name="module.first.duplicate",
            start_line=2,
        ),
        stable_node_id(
            NodeKind.FUNCTION,
            source_path="module.py",
            qualified_name="module.second.duplicate",
            start_line=6,
        ),
    ]
    assert duplicates[0].id != duplicates[1].id


def test_python_extraction_is_repeatable() -> None:
    source = "class Service:\n    def load(self):\n        return 1\n"
    extractor = PythonExtractor()

    first = extractor.extract(Path("service.py"), source)
    second = extractor.extract(Path("service.py"), source)

    assert first == second


def test_invalid_python_returns_one_deterministic_diagnostic_without_nodes() -> None:
    extractor = PythonExtractor()

    first = extractor.extract(Path("broken.py"), ")")
    second = extractor.extract(Path("broken.py"), ")")

    assert first == second
    assert first == ExtractionResult(diagnostics=("python_syntax_error:broken.py:1:0",))


def test_python_extraction_does_not_import_or_execute_source(
    tmp_path: Path,
) -> None:
    sentinel = tmp_path / "executed.txt"
    source = (
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('executed', encoding='utf-8')\n"
    )

    result = PythonExtractor().extract(Path("danger.py"), source)

    assert tuple(node.kind for node in result.nodes) == (NodeKind.MODULE,)
    assert result.edges == ()
    assert not sentinel.exists()
