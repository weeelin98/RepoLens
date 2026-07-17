"""Direct Markdown structure and unresolved syntax facts from CommonMark tokens."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from markdown_it import MarkdownIt
from markdown_it.token import Token

from repolens.extractors.base import (
    ExtractionResult,
    MarkdownFactKind,
    UnresolvedMarkdownFact,
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

_PARSER = MarkdownIt("commonmark")


def _normalized_source_path(path: Path) -> str:
    rendered = path.as_posix()
    if path.is_absolute() or PureWindowsPath(rendered).is_absolute():
        raise ValueError("extractor paths must be repository-relative")
    normalized = normalize_repo_path(rendered)
    if normalized == ".":
        raise ValueError("extractor path must name a file")
    return normalized


def _document_span(source: str) -> SourceSpan:
    lines = source.splitlines()
    if not lines:
        return SourceSpan(start_line=1, end_line=1, start_column=0, end_column=0)
    return SourceSpan(
        start_line=1,
        end_line=len(lines),
        start_column=0,
        end_column=len(lines[-1].encode("utf-8")),
    )


def _token_span(token: Token) -> SourceSpan:
    if token.map is None:
        raise ValueError(f"Markdown token {token.type!r} has no block line map")
    start, end = token.map
    return SourceSpan(start_line=start + 1, end_line=max(start + 1, end))


def _inline_text(tokens: list[Token]) -> str:
    pieces: list[str] = []
    for token in tokens:
        if token.type in {"text", "code_inline", "html_inline", "image"}:
            pieces.append(token.content)
        elif token.type in {"softbreak", "hardbreak"}:
            pieces.append("\n")
    return "".join(pieces)


def _node_sort_key(node: GraphNode) -> tuple[object, ...]:
    span = node.span
    return (
        span.start_line if span else 0,
        span.start_column if span and span.start_column is not None else -1,
        node.qualified_name or "",
        node.kind.value,
        node.id,
    )


def _contains_edge(parent: GraphNode, child: GraphNode) -> GraphEdge:
    return GraphEdge(
        source_id=parent.id,
        target_id=child.id,
        relation=EdgeKind.CONTAINS,
        evidence_kind=EvidenceKind.SYNTAX_DIRECT,
        confidence=1.0,
        source_path=child.source_path,
        span=child.span,
    )


class MarkdownExtractor:
    """Extract Markdown hierarchy and unresolved syntax without resolving targets."""

    @property
    def extensions(self) -> frozenset[str]:
        return frozenset({".md"})

    @property
    def filenames(self) -> frozenset[str]:
        return frozenset()

    def extract(self, path: Path, source: str) -> ExtractionResult:
        source_path = _normalized_source_path(path)
        try:
            tokens = _PARSER.parse(source)
        except (RuntimeError, ValueError):
            return ExtractionResult(diagnostics=(f"markdown_parse_error:{source_path}",))

        document_span = _document_span(source)
        document = GraphNode(
            id=stable_node_id(
                NodeKind.MARKDOWN_DOCUMENT,
                source_path=source_path,
                qualified_name=source_path,
                start_line=document_span.start_line,
            ),
            kind=NodeKind.MARKDOWN_DOCUMENT,
            label=PurePosixPath(source_path).name,
            language="markdown",
            source_path=source_path,
            span=document_span,
            qualified_name=source_path,
        )

        nodes = [document]
        edges: list[GraphEdge] = []
        facts: list[UnresolvedMarkdownFact] = []
        heading_stack: list[tuple[int, GraphNode]] = []
        current_section: GraphNode | None = None
        occurrence = 0

        for index, token in enumerate(tokens):
            if token.type == "heading_open":
                level = int(token.tag.removeprefix("h"))
                inline = tokens[index + 1]
                if inline.type != "inline":
                    return ExtractionResult(diagnostics=(f"markdown_parse_error:{source_path}",))
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                visible_text = _inline_text(inline.children or []) or inline.content
                label = visible_text or "<untitled>"
                span = _token_span(token)
                section_path = "/".join(
                    [source_path, *(node.label for _, node in heading_stack), label]
                )
                section = GraphNode(
                    id=stable_node_id(
                        NodeKind.MARKDOWN_SECTION,
                        source_path=source_path,
                        qualified_name=section_path,
                        start_line=span.start_line,
                    ),
                    kind=NodeKind.MARKDOWN_SECTION,
                    label=label,
                    language="markdown",
                    source_path=source_path,
                    span=span,
                    qualified_name=section_path,
                    metadata=(
                        {"level": level}
                        if visible_text
                        else {"level": level, "raw_text": visible_text}
                    ),
                )
                parent = heading_stack[-1][1] if heading_stack else document
                nodes.append(section)
                edges.append(_contains_edge(parent, section))
                heading_stack.append((level, section))
                current_section = section
                continue

            if token.type == "fence":
                info = token.info.strip()
                facts.append(
                    UnresolvedMarkdownFact(
                        kind=MarkdownFactKind.FENCED_CODE,
                        source_path=source_path,
                        span=_token_span(token),
                        occurrence=occurrence,
                        section_id=current_section.id if current_section else None,
                        info=info or None,
                        language=info.split(maxsplit=1)[0] if info else None,
                        fence_marker=token.markup,
                        line_count=len(token.content.splitlines()),
                    )
                )
                occurrence += 1
                continue

            if token.type != "inline":
                continue

            children = token.children or []
            child_index = 0
            while child_index < len(children):
                child = children[child_index]
                if child.type == "code_inline":
                    facts.append(
                        UnresolvedMarkdownFact(
                            kind=MarkdownFactKind.INLINE_CODE,
                            source_path=source_path,
                            span=_token_span(token),
                            occurrence=occurrence,
                            section_id=current_section.id if current_section else None,
                            text=child.content,
                        )
                    )
                    occurrence += 1
                elif child.type == "link_open":
                    close_index = child_index + 1
                    while (
                        close_index < len(children) and children[close_index].type != "link_close"
                    ):
                        close_index += 1
                    facts.append(
                        UnresolvedMarkdownFact(
                            kind=MarkdownFactKind.LINK,
                            source_path=source_path,
                            span=_token_span(token),
                            occurrence=occurrence,
                            section_id=current_section.id if current_section else None,
                            text=_inline_text(children[child_index + 1 : close_index]),
                            target=child.attrGet("href") or "",
                            title=child.attrGet("title"),
                        )
                    )
                    occurrence += 1
                child_index += 1

        return ExtractionResult(
            nodes=tuple(sorted(nodes, key=_node_sort_key)),
            edges=tuple(sorted(edges, key=GraphEdge.sort_key)),
            markdown_facts=tuple(sorted(facts, key=UnresolvedMarkdownFact.sort_key)),
        )
