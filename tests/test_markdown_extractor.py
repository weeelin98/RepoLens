from __future__ import annotations

from pathlib import Path

import pytest

import repolens.extractors.markdown as markdown_module
from repolens.extractors import (
    ExtractionResult,
    MarkdownExtractor,
    MarkdownFactKind,
    PythonExtractor,
)
from repolens.models import EdgeKind, EvidenceKind, GraphNode, NodeKind, SourceSpan


def extract(source: str, path: str = "docs/guide.md") -> ExtractionResult:
    return MarkdownExtractor().extract(Path(path), source)


def nodes_of_kind(source: str, kind: NodeKind) -> tuple[GraphNode, ...]:
    return tuple(node for node in extract(source).nodes if node.kind is kind)


def test_extractor_declares_only_markdown_extension() -> None:
    assert MarkdownExtractor().extensions == frozenset({".md"})


def test_one_document_node_preserves_path_label_language_and_span() -> None:
    result = extract("# Guide\n\nText\n", r"docs\guide.md")
    documents = tuple(node for node in result.nodes if node.kind is NodeKind.MARKDOWN_DOCUMENT)

    assert len(documents) == 1
    assert documents[0].label == "guide.md"
    assert documents[0].qualified_name == "docs/guide.md"
    assert documents[0].language == "markdown"
    assert documents[0].source_path == "docs/guide.md"
    assert documents[0].span == SourceSpan(
        start_line=1,
        end_line=3,
        start_column=0,
        end_column=4,
    )


def test_top_level_heading_is_section_contained_by_document() -> None:
    result = extract("# Guide\n")
    document = next(node for node in result.nodes if node.kind is NodeKind.MARKDOWN_DOCUMENT)
    section = next(node for node in result.nodes if node.kind is NodeKind.MARKDOWN_SECTION)

    assert section.label == "Guide"
    assert section.metadata == {"level": 1}
    assert section.span == SourceSpan(start_line=1, end_line=1)
    assert [(edge.source_id, edge.target_id) for edge in result.edges] == [
        (document.id, section.id)
    ]
    assert result.edges[0].relation is EdgeKind.CONTAINS
    assert result.edges[0].evidence_kind is EvidenceKind.SYNTAX_DIRECT
    assert result.edges[0].confidence == 1.0


def test_nested_heading_hierarchy_uses_nearest_lower_level() -> None:
    result = extract("# API\n## Users\n### Create\n")
    by_label = {node.label: node for node in result.nodes}
    pairs = {(edge.source_id, edge.target_id) for edge in result.edges}

    assert (by_label["API"].id, by_label["Users"].id) in pairs
    assert (by_label["Users"].id, by_label["Create"].id) in pairs


def test_same_level_headings_are_siblings() -> None:
    result = extract("# Guide\n## One\n## Two\n")
    by_label = {node.label: node for node in result.nodes}
    parents = {edge.target_id: edge.source_id for edge in result.edges}

    assert parents[by_label["One"].id] == by_label["Guide"].id
    assert parents[by_label["Two"].id] == by_label["Guide"].id


def test_skipped_heading_level_uses_nearest_lower_heading() -> None:
    result = extract("# API\n### Create\n")
    by_label = {node.label: node for node in result.nodes}

    assert any(
        edge.source_id == by_label["API"].id and edge.target_id == by_label["Create"].id
        for edge in result.edges
    )


def test_repeated_heading_names_have_distinct_position_disambiguated_ids() -> None:
    sections = nodes_of_kind("# Guide\n## Repeat\n## Repeat\n", NodeKind.MARKDOWN_SECTION)
    repeated = [node for node in sections if node.label == "Repeat"]

    assert len(repeated) == 2
    assert repeated[0].id != repeated[1].id
    assert {node.span.start_line for node in repeated if node.span} == {2, 3}


def test_setext_headings_preserve_level_and_two_line_span() -> None:
    sections = nodes_of_kind("Title\n=====\n\nInstall\n-------\n", NodeKind.MARKDOWN_SECTION)

    assert [(node.label, node.metadata["level"], node.span) for node in sections] == [
        ("Title", 1, SourceSpan(start_line=1, end_line=2)),
        ("Install", 2, SourceSpan(start_line=4, end_line=5)),
    ]


@pytest.mark.parametrize(
    ("syntax", "label", "target"),
    [
        ("[OpenAI](https://example.com)", "OpenAI", "https://example.com"),
        ("[Guide](../guide.md)", "Guide", "../guide.md"),
        ("[Install](#installation)", "Install", "#installation"),
    ],
)
def test_links_preserve_direct_syntax(syntax: str, label: str, target: str) -> None:
    fact = extract(f"# Docs\n\n{syntax}\n").markdown_facts[0]

    assert fact.kind is MarkdownFactKind.LINK
    assert fact.text == label
    assert fact.target == target
    assert fact.span == SourceSpan(start_line=3, end_line=3)
    assert fact.section_id is not None


def test_link_title_is_preserved_when_exposed() -> None:
    fact = extract('[Guide](guide.md "Read this")\n').markdown_facts[0]

    assert fact.title == "Read this"


def test_multiple_identical_links_remain_distinct_in_source_order() -> None:
    facts = extract("[Guide](a.md) and [Guide](a.md)\n").markdown_facts

    assert len(facts) == 2
    assert [fact.occurrence for fact in facts] == [0, 1]
    assert all(fact.target == "a.md" for fact in facts)


def test_fenced_code_preserves_info_language_marker_line_count_and_section() -> None:
    fact = extract("# Examples\n\n~~~python linenums\nprint('ok')\n~~~\n").markdown_facts[0]

    assert fact.kind is MarkdownFactKind.FENCED_CODE
    assert fact.info == "python linenums"
    assert fact.language == "python"
    assert fact.fence_marker == "~~~"
    assert fact.line_count == 1
    assert fact.span == SourceSpan(start_line=3, end_line=5)
    assert fact.section_id is not None
    assert fact.text is None


def test_fenced_code_without_language_has_safe_empty_metadata() -> None:
    fact = extract("```\none\ntwo\n```\n").markdown_facts[0]

    assert fact.info is None
    assert fact.language is None
    assert fact.fence_marker == "```"
    assert fact.line_count == 2


def test_inline_code_preserves_exact_text_and_conservative_block_span() -> None:
    facts = extract("# Use\n\nCall `UserService.load()` from `services/user.py`.\n").markdown_facts

    assert [fact.kind for fact in facts] == [
        MarkdownFactKind.INLINE_CODE,
        MarkdownFactKind.INLINE_CODE,
    ]
    assert [fact.text for fact in facts] == ["UserService.load()", "services/user.py"]
    assert all(fact.span == SourceSpan(start_line=3, end_line=3) for fact in facts)
    assert all(fact.span.start_column is None for fact in facts)


def test_facts_associate_with_the_nearest_enclosing_section() -> None:
    result = extract("# One\n\n`first`\n\n## Two\n\n`second`\n")
    sections = {node.label: node for node in result.nodes if node.kind is NodeKind.MARKDOWN_SECTION}

    assert [fact.section_id for fact in result.markdown_facts] == [
        sections["One"].id,
        sections["Two"].id,
    ]


def test_all_markdown_evidence_paths_are_repository_relative_posix() -> None:
    result = extract("# Guide\n\n[Link](target.md) and `code`.\n", r"docs\nested\guide.md")

    assert {node.source_path for node in result.nodes} == {"docs/nested/guide.md"}
    assert {fact.source_path for fact in result.markdown_facts} == {"docs/nested/guide.md"}


def test_repeated_extraction_is_equal_and_explicitly_ordered() -> None:
    source = "# Guide\n\n`code` [link](target.md)\n\n```py\npass\n```\n"

    first = extract(source)
    second = extract(source)

    assert first == second
    assert [fact.occurrence for fact in first.markdown_facts] == [0, 1, 2]


def test_malformed_markdown_recovers_without_crashing() -> None:
    result = extract("# Guide\n\n[unfinished link\n\n```python\nunterminated\n")

    assert any(node.kind is NodeKind.MARKDOWN_DOCUMENT for node in result.nodes)
    assert any(node.kind is NodeKind.MARKDOWN_SECTION for node in result.nodes)
    assert result.diagnostics == ()


def test_empty_heading_is_represented_without_fabricating_visible_text() -> None:
    section = nodes_of_kind("#\n", NodeKind.MARKDOWN_SECTION)[0]

    assert section.label == "<untitled>"
    assert section.metadata == {"level": 1, "raw_text": ""}


def test_fatal_parser_failure_returns_diagnostic_without_semantic_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailedParser:
        def parse(self, source: str) -> list[object]:
            raise RuntimeError(source)

    monkeypatch.setattr(markdown_module, "_PARSER", FailedParser())
    result = extract("# Guide\n")

    assert result.nodes == ()
    assert result.edges == ()
    assert result.markdown_facts == ()
    assert result.diagnostics == ("markdown_parse_error:docs/guide.md",)


def test_markdown_text_and_fenced_code_are_never_executed(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed.txt"
    source = f"```python\nPath({str(sentinel)!r}).write_text('executed')\n```\n"

    result = extract(source)

    assert result.markdown_facts[0].line_count == 1
    assert not sentinel.exists()


def test_python_extractor_behavior_remains_unchanged() -> None:
    result = PythonExtractor().extract(Path("service.py"), "def load():\n    pass\n")

    assert {node.kind for node in result.nodes} == {NodeKind.MODULE, NodeKind.FUNCTION}
    assert result.markdown_facts == ()
