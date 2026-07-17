# Milestone 1.4A — Basic Deterministic Markdown Extraction

## Purpose and user-visible outcome

`repolens index PATH` will include direct Markdown structure and syntax facts for every
accepted `.md` file. The complete deterministic `graph.json` will contain one Markdown
document node, heading section nodes and their containment hierarchy, plus unresolved link,
fenced-code, and inline-code facts with repository-relative evidence. No Markdown content is
executed, fetched, summarized, or resolved to another graph node.

## Scope and non-goals

This slice adds one CommonMark-based Markdown extractor, a typed unresolved Markdown fact
contract, default registry integration, file-to-document containment, complete-result
serialization through the existing model boundary, focused tests, and documentation.

It does not summarize prose, resolve links or code references, validate anchors, create
cross-file reference edges, parse fenced code as source, extract project metadata, resolve
Python imports, extract calls or inheritance, add JavaScript/TypeScript support, generate an
overview/context pack, change MCP behavior, or implement change impact.

## Current state

- `NodeKind` already includes `MARKDOWN_DOCUMENT` and `MARKDOWN_SECTION`; `EdgeKind`
  includes `CONTAINS` and `REFERENCES`; `EvidenceKind.SYNTAX_DIRECT` represents direct
  syntax with confidence `1.0`.
- `Extractor` declares extensions and returns `ExtractionResult` containing graph nodes,
  graph edges, unresolved Python imports, and diagnostics. No unresolved Markdown contract
  exists.
- `GraphEdge` requires both endpoints to exist, so an unresolved link or inline-code token
  cannot honestly be represented as a `REFERENCES` edge. Fabricating target nodes would
  violate the graph contract.
- The indexer selects extractors through `ExtractorRegistry`, loads only supported files,
  and currently registers only `PythonExtractor`. It adds file containment only for module
  roots. Its existing contained source loader can read UTF-8 Markdown without adding
  suffix-specific extractor selection.
- `RepositoryIndexResult` serializes graph nodes/edges, unresolved imports, scanner
  diagnostics, and extractor diagnostics. A new normalized Markdown-fact collection is the
  smallest addition needed for `graph.json` preservation.
- The `markdown_documented_project` fixture contains ATX headings, one relative link, one
  inline-code reference, and one fenced Python block. Its gold includes future resolved
  `documents` behavior that remains outside this direct-syntax slice.
- Baseline on branch `Python-definition-extractor`: the worktree was clean; 119 tests passed,
  3 real-symlink scanner integrations skipped because Windows returned privilege error
  1314; total coverage was 92%; Mypy reported no issues in 28 source files.

## Acceptance criteria

1. `MarkdownExtractor.extensions` is exactly `{'.md'}` and repeated extraction of the same
   repository-relative path and source returns equal, explicitly sorted results.
2. Every successfully parsed Markdown file produces exactly one `MARKDOWN_DOCUMENT` node
   spanning the document and using its POSIX path, filename label, Markdown language, and
   stable path-based identity.
3. ATX and reliably tokenized Setext headings produce `MARKDOWN_SECTION` nodes containing
   visible token text, heading level metadata, line-level spans, qualified section paths,
   and IDs disambiguated by declaration line.
4. A heading stack attaches each section to the nearest preceding lower-level heading, or
   to the document when none exists. Same-level/deeper scopes close before attachment;
   skipped levels work without invented nodes.
5. Markdown links preserve label, raw target, optional title, evidence, occurrence order,
   and nearest section association as unresolved facts. They create no graph edge because
   no target endpoint has been resolved.
6. Fenced backtick and tilde blocks preserve the full info string, derived first info word
   as language when present, fence marker, bounded content line count, line span,
   occurrence, and nearest section, but never the block contents.
7. Inline code preserves exact token content, conservative containing-block line span,
   occurrence, and nearest section without guessing whether it names a symbol, path,
   command, or literal.
8. Block token maps are converted from zero-based half-open lines to 1-based inclusive
   `SourceSpan` lines. Document columns are exact UTF-8 byte offsets; heading/fence and
   inline/link columns remain `None` because the parser does not expose reliable columns.
9. Malformed CommonMark recovers normally. A parser-level `ValueError` or `RuntimeError`
   returns a deterministic extractor diagnostic with no semantic Markdown nodes or facts;
   repository indexing retains the structural file node and continues.
10. The default registry includes fresh Python and Markdown extractors. The indexer adds
    file-to-module and file-to-Markdown-document containment through a small root-kind rule,
    without suffix-specific extractor selection or Python behavior changes.
11. `RepositoryIndexResult.markdown_facts` is validated, sorted, canonically serialized,
    parsed back, and included in byte-identical repeated CLI output without absolute paths.
12. All thirty requested behaviors, existing extractor/indexer/CLI regressions, the full
    suite, harness smoke, doctor, and manual two-run fixture smoke pass.

## Milestone phases

### Phase 1 — Contract and dependency

Add `MarkdownFactKind` and `UnresolvedMarkdownFact` to
`src/repolens/extractors/base.py`, extend `ExtractionResult` and
`RepositoryIndexResult`, export the contract, add `markdown-it-py>=4.2,<5` directly to
`pyproject.toml`, and update `uv.lock` only with `uv lock`.

### Phase 2 — Markdown extraction

Create `src/repolens/extractors/markdown.py`. Parse CommonMark tokens, create the document
and section graph, maintain a heading stack, extract link/fence/inline-code facts, retain
nearest-section IDs, translate line maps conservatively, normalize paths, and sort every
collection explicitly.

### Phase 3 — Registry and indexer integration

Register `MarkdownExtractor` in the fresh default registry. Merge Markdown facts into the
repository result and extend file-root containment from modules to Markdown documents.
Preserve containment revalidation, source diagnostics, scanner behavior, Python extraction,
and canonical serialization.

### Phase 4 — Focused tests

Add `tests/test_markdown_extractor.py` for extension, document, hierarchy, Setext, repeat
headings, links, fences, inline code, association, spans, determinism, malformed input, and
non-execution. Extend `tests/test_indexer.py` and `tests/test_cli.py` for graph integration,
ignored Markdown, complete facts, byte identity, and path privacy. Existing
`tests/test_extractors.py` remains the Python regression suite.

### Phase 5 — Documentation, validation, and smoke

Update `CODEX.md`, `README.md`, `docs/INTERVIEW_QUESTIONS.md`, and this plan. Run every
requested command sequentially, index the Markdown fixture twice, inspect semantic facts
and hierarchy, compare output bytes, check path leakage, then audit the final diff and
worktree. Do not alter fixture gold unless the existing harness requires it.

## Invariants and contracts

### Unresolved Markdown facts

`UnresolvedMarkdownFact` is a frozen Pydantic model with a discriminating `kind` (`link`,
`fenced_code`, or `inline_code`), repository-relative `source_path`, `SourceSpan`, stable
zero-based source `occurrence`, and optional `section_id`. Kind-specific fields are
validated: links require text and target; inline code requires text; fenced code requires a
marker and nonnegative line count and may carry info/language. No fact contains full fenced
source, absolute paths, timestamps, target node IDs, or inferred semantics.

`ExtractionResult.markdown_facts` and `RepositoryIndexResult.markdown_facts` are explicit
tuples sorted by source path, span, occurrence, kind, and direct syntax fields. These facts
remain outside `GraphSnapshot` for the same reason unresolved imports do: they are syntax
evidence without defensible graph endpoints.

### Parser and dependency

Use `markdown-it-py>=4.2,<5` with the `commonmark` preset and no optional plugins. The
runtime dependency is justified because its structured block/inline token stream recognizes
ATX/Setext headings, links, backtick/tilde fences, and code spans and exposes block line maps.
A handwritten regex parser would be larger, less conformant, and more likely to assign
repeated syntax to the wrong occurrence. The upper bound protects token API assumptions;
the lockfile records the exact resolved version.

### Document and section graph

The document qualified name is its normalized source path; its label is the filename. Its
ID uses kind, path, qualified name, and start line 1. Its exact document span follows the
existing Python module convention.

Each section label is the parser's visible inline heading text. Its qualified name is the
document path followed by the active ancestor labels and current label, joined with `/`.
Its ID uses kind, source path, qualified name, and heading start line, so repeated names are
distinct. Metadata contains only `level`. Every heading receives exactly one syntax-direct
`contains` edge from its nearest lower-level heading or the document.

### Heading stack

Before a new level `L` is attached, pop while the stack top has level greater than or equal
to `L`. The remaining top is the nearest preceding lower-level parent; an empty stack uses
the document. Push the new `(level, section)` after creating its edge. This handles sibling
headings and skipped levels without inventing missing sections.

### Links and code syntax

Inline child tokens are walked in parser order. A `link_open` starts one unresolved link;
the matching `link_close` bounds its label tokens. The raw `href` and optional `title` come
from parser attributes. `code_inline` yields one unresolved exact-text fact. Both use their
containing inline block's line map because child tokens do not expose exact coordinates.

A `fence` block token yields one fenced-code fact using token `info`, the first info word as
language, token `markup` as marker, token `map` as span, and a content line count. Token
content itself is discarded. Indented code blocks are not fenced blocks and are not facts.

### Evidence, spans, IDs, and ordering

All graph containment is `SYNTAX_DIRECT` with confidence `1.0`. Unresolved syntax facts do
not claim an evidence class or target edge. Token maps `[start, end)` become inclusive
`start + 1` through `max(start + 1, end)`. No global text search is used. Columns remain
unset unless computed exactly for the whole document.

Nodes sort by source position, qualified name, kind, and ID; edges use
`GraphEdge.sort_key`; facts use their model sort key; diagnostics sort lexically. Canonical
model serialization then sorts the complete index and JSON keys. No result depends on set
iteration, wall time, absolute roots, randomness, or parser rendering.

## Test and harness plan

`tests/test_markdown_extractor.py` will use small authored strings to cover requested cases
1–22. Assertions will identify semantic fields rather than copy generated JSON. Parser
failure behavior will be exercised through a narrowly injected or patched parser failure,
while malformed Markdown verifies ordinary recovery and non-execution.

`tests/test_indexer.py` will cover cases 23–25 and 28: structural file plus document,
file-to-document containment, heading hierarchy, ignored Markdown, and unchanged Python.
`tests/test_cli.py` will cover cases 26–27 and 29–30: serialized links/code facts, repeated
byte identity, and no absolute root. Existing complete-result round-trip coverage will be
extended if its explicit fixture requires the new collection.

The existing `markdown_documented_project` is the manual smoke input. Harness gold remains
unchanged because its current validator describes later resolved relationships and does not
compare production index output. If tests show the harness requires a direct-syntax field,
only that minimum authored expectation will be added and recorded here.

## Progress

- [x] 2026-07-17: Verified branch, clean worktree, baseline tests, and Mypy.
- [x] 2026-07-17: Read governing docs, prior ExecPlan, contracts, implementation, tests,
  fixture, interview questions, and dependency files.
- [x] 2026-07-17: Defined acceptance criteria and the fourteen requested design decisions
  before production edits.
- [x] 2026-07-17: Added the unresolved Markdown fact contract and locked parser dependency.
- [x] 2026-07-17: Implemented Markdown extraction and repository integration.
- [x] 2026-07-17: Added focused extractor, indexer, and CLI tests.
- [x] 2026-07-17: Updated project documentation and learning questions.
- [x] 2026-07-17: Ran full validation, manual smoke, and final scope audit.

## Decisions

- **2026-07-17 — Use `markdown-it-py` CommonMark tokens.** The parser supplies structured
  headings, inline children, links, fences, and block line maps. A custom regex parser would
  duplicate grammar behavior and weaken repeated-occurrence evidence.
- **2026-07-17 — Add one typed unresolved Markdown fact model.** Existing graph edges cannot
  represent an unresolved target because endpoint validation is mandatory. One discriminated
  fact model is smaller than three parallel collections and keeps direct syntax explicit.
- **2026-07-17 — Associate facts by section ID without creating edges.** The containing
  section is a known local node and useful provenance, while the referenced target remains
  unknown. This records lexical context without pretending resolution.
- **2026-07-17 — Use conservative line spans for inline syntax.** Inline parser children do
  not expose reliable columns. The containing inline block map is deterministic and honest;
  source searching could mismatch repeated syntax.
- **2026-07-17 — Keep fixture gold unchanged unless required.** Its `documents` edge is a
  future resolver result, not a direct Markdown extraction claim.

## Discoveries and surprises

- **2026-07-17:** The graph enum already anticipates `REFERENCES`, but endpoint validation
  correctly prevents its use for unresolved Markdown links and code tokens.
- **2026-07-17:** The existing shared source loader uses `tokenize.open()`. It reads ordinary
  UTF-8 Markdown and preserves current containment/diagnostic behavior, so M1.4A needs no
  suffix branch in indexer selection or loading.
- **2026-07-17:** PyPI identifies `markdown-it-py` 4.2.0 as the current stable release with
  Python 3.11 support. The direct `>=4.2,<5` constraint matches the token API used here.
- **2026-07-17:** Concurrent pytest processes are known to contend for `.coverage` on this
  Windows checkout, so all validation test commands will run sequentially.

## Validation transcript

Baseline before production edits:

- `git branch --show-current` — `Python-definition-extractor`.
- `git status --short` — no output.
- `uv run pytest` — 119 passed, 3 skipped for Windows symlink privilege error 1314; total
  coverage 92%.
- `uv run mypy src tests` — success, no issues in 28 source files.

Final M1.4A results:

- `uv sync --dev --locked` — exit 0; 26 packages resolved and 25 packages checked.
- `uv run ruff format .` — exit 0; 44 files left unchanged.
- `uv run ruff format --check .` — exit 0; 44 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 30 source files.
- `uv run pytest tests/test_markdown_extractor.py -v` — exit 0; 24 passed; Markdown
  extractor coverage was 93%.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 34 passed; Python extractor
  coverage was 96%.
- `uv run pytest tests/test_indexer.py -v` — exit 0; 21 passed; indexer coverage was 92%.
- `uv run pytest tests/test_cli.py -v` — exit 0; 17 passed; CLI coverage was 84%.
- `uv run pytest` — exit 0; 144 passed and 3 existing scanner integrations skipped
  because Windows returned symlink privilege error 1314; total coverage was 92%, Markdown
  extractor coverage was 93%, and complete-result serialization coverage was 100%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.

Manual fixture smoke ran `uv run repolens index
harness/fixtures/markdown_documented_project` twice. Each run reported 2 files, 11 nodes,
10 edges, 0 unresolved imports, and 0 warnings. Inspection found 1 Markdown document, 3
sections, 3 Markdown hierarchy edges, and `inline_code`, `link`, and `fenced_code` facts.
The outputs were byte-identical, contained no absolute fixture path, and ended with one
newline. The generated `repolens-out` directory was verified and removed afterward.

- `git diff --check` — exit 0; no whitespace errors.
- `git status --short` — exactly 13 planned M1.4A paths were modified or untracked: the
  ExecPlan, dependency files, extractor contract/export/implementation, indexer, three test
  files, and three project documentation files.

GNU Make is unavailable in this Windows environment and this plan does not claim
`make check` ran.

## Learning checkpoint

The developer must explain how CommonMark block and inline tokens differ; how the heading
stack handles siblings and skipped levels; why heading positions disambiguate repeated
labels; why graph endpoint invariants keep links unresolved; why fenced code is neither
executed nor recursively parsed; why inline code is syntax rather than a resolved symbol;
why line-only spans are more truthful than guessed columns; and how extractor facts flow
through `RepositoryIndexResult` into canonical `graph.json`.

## Outcome and follow-ups

M1.4A now provides deterministic direct Markdown document/section structure and unresolved
link, fenced-code, and inline-code facts in canonical `graph.json`. Target resolution,
recursive fenced-code parsing, and natural-language understanding remain explicit and
deferred. Milestone 1 remains active. The next slice is Milestone 1.4B — Deterministic
project metadata extraction.
