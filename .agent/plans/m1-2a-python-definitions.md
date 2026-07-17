# Milestone 1.2A — Basic Python Definition Extraction

## Purpose and user-visible outcome

Given one repository-relative `.py` path and its source text, RepoLens will use Python's
standard-library `ast` module to return deterministic direct syntax facts for the module,
classes, functions, async functions, methods, nested definitions, their source spans and
qualified names, stable IDs, and lexical `contains` edges. Extraction never imports or
executes target code.

## Scope and non-goals

This slice adds `src/repolens/extractors/python.py`, exports its extractor through the
existing extractor package, extends `tests/test_extractors.py`, records interview questions,
and updates this plan and `CODEX.md`. It does not add imports, calls, inheritance, decorator
meaning, endpoints, Markdown, a graph builder, `graph.json`, scanner orchestration, CLI
indexing, JavaScript/TypeScript, or cross-file resolution. Harness gold remains unchanged:
its current IDs and resolver edges describe later integrated graph behavior, while M1.2A
returns isolated per-file syntax facts only.

## Current state

- `Extractor` already requires `extensions` and `extract(path, source) -> ExtractionResult`.
- `ExtractionResult` contains immutable tuples of `GraphNode`, `GraphEdge`, and diagnostic
  strings; no shared-model change is required.
- `NodeKind`, `EdgeKind`, `EvidenceKind`, `SourceSpan`, and `stable_node_id()` already cover
  every M1.2A output.
- The registry normalizes declared extensions but has no global default registry; M1.2A
  exports `PythonExtractor` without adding scanner-to-extractor orchestration.
- The `python_service` harness has readable Python examples, but its gold includes later
  call/test resolution and intentionally is not migrated in this isolated extractor slice.
- Baseline on branch `Python-definition-extractor`: 53 tests passed, 3 real-symlink tests
  skipped on Windows, total coverage was 91%, and Mypy found no issues in 25 source files.

## Acceptance criteria

1. `PythonExtractor.extensions == frozenset({".py"})` and it satisfies `Extractor`.
2. `extract()` accepts a repository-relative `Path` and source string and returns the
   existing `ExtractionResult` without file I/O or execution.
3. Every valid file returns exactly one module node plus all class, `def`, and `async def`
   definitions at any lexical nesting depth.
4. Direct class-scope functions are `METHOD`; functions whose nearest definition parent is
   a function or method are `FUNCTION`. Classes are always `CLASS`.
5. Qualified names contain the derived module name and every enclosing definition name.
6. Nodes use normalized repository-relative POSIX `source_path` values and AST line/column
   coordinates. IDs come only from `stable_node_id()`.
7. Every non-module definition has one syntax-direct, confidence-1.0 `contains` edge from
   its nearest lexical module/class/function/method parent.
8. Invalid syntax returns no nodes or edges and one fixed-format diagnostic based on the
   normalized path and syntax-error location.
9. Repeated extraction compares equal, expected nodes/edges are hand-authored in tests, and
   the full offline validation set passes.

## Milestone phases

### Phase 1 — Contract and naming decisions

Define module naming, scope classification, span mapping, ID inputs, containment, ordering,
and syntax-error behavior here before production code.

### Phase 2 — Minimal AST extractor

Add `PythonExtractor` in `src/repolens/extractors/python.py`. Parse with `ast.parse()` only,
walk definition nodes with a small lexical scope stack, build existing graph contracts, and
export the class from `src/repolens/extractors/__init__.py`.

### Phase 3 — Focused executable expectations

Extend `tests/test_extractors.py` with manually specified nodes and edges covering module
naming, sync/async functions, classes/methods, nested definitions, IDs, parents, paths,
spans, determinism, invalid syntax, extensions, and non-execution.

### Phase 4 — Review, learning, and validation

Add M1.2A interview questions, update `CODEX.md`, run every requested command, inspect the
complete diff for scope growth, and record exact results and limitations.

## Invariants and contracts

### Extractor API

`PythonExtractor` is stateless. Its public surface is:

```text
extensions -> frozenset({".py"})
extract(path: Path, source: str) -> ExtractionResult
```

The caller supplies decoded source; encoding and file reads remain outside the extractor.

### Module-name derivation

Normalize the input with `normalize_repo_path(path.as_posix())`, remove `.py`, and join path
parts with dots. For `__init__.py`, remove the final `__init__` component: therefore
`app.py -> app`, `services/user.py -> services.user`, and
`services/__init__.py -> services`. A repository-root `__init__.py` has no discoverable
package name, so its deterministic qualified name and label are the explicit sentinel
`<root>` rather than a guessed repository name.

### Scope-stack and classification rules

Start the stack with the module. On `ClassDef`, create a `CLASS`, attach it to the current
scope, push it, visit its body, then pop it. Handle `FunctionDef` and `AsyncFunctionDef`
identically: classify the node as `METHOD` only when the nearest definition scope on the
stack is a class; otherwise classify it as `FUNCTION`. Push the new function/method while
visiting its body. Thus a function nested inside a method is a `FUNCTION`, not a method,
because syntax establishes lexical nesting but does not prove runtime binding semantics.
Control-flow statements do not create named scopes, so a definition inside one attaches to
the nearest module/class/function/method scope.

### Qualified names

Append each definition's bare name to its parent's qualified name with `.`. Examples are
`services.user`, `services.user.UserService`, `services.user.UserService.load`,
`services.user.load_config`, `services.user.outer.inner`, and
`services.user.Outer.Inner`. Bare names never serve as identity by themselves.

### SourceSpan mapping

Definition nodes copy `lineno`, `end_lineno`, `col_offset`, and `end_col_offset` into
`start_line`, `end_line`, `start_column`, and `end_column`. Lines are AST's 1-based inclusive
line coordinates; columns retain AST's 0-based UTF-8 byte-offset convention and exclusive
end. The module span is deterministic file coverage: line 1, column 0 through the final
physical content line and its UTF-8 byte length; an empty source is `1:0-1:0`.

### Stable-ID inputs

Every node calls the existing `stable_node_id(kind, source_path=normalized_path,
qualified_name=qualified_name, start_line=span.start_line)`. No second identity algorithm or
mutable label input is introduced. Qualified scope paths distinguish duplicate bare names;
the start line disambiguates repeated declarations with the same qualified name.

### Contains edges

The module has no parent edge. Every definition gets exactly one edge from the nearest
lexical definition scope using `EdgeKind.CONTAINS`, `EvidenceKind.SYNTAX_DIRECT`, confidence
`1.0`, the normalized source path, and the child definition's span. No other edge kind is
emitted.

### Syntax errors and deterministic output

Catch only `SyntaxError` from `ast.parse()`. Return no nodes or edges and one diagnostic:
`python_syntax_error:<path>:<line>:<zero-based-column>`. Do not use exception prose or
partially interpret an invalid tree. Valid nodes are sorted by source position, qualified
name, kind, and ID; edges use `GraphEdge.sort_key()`. No filesystem order, hash iteration,
absolute path, timestamp, or target-code side effect enters output.

## Test and harness plan

`tests/test_extractors.py` will use compact source strings and manually authored expected
`GraphNode`/`GraphEdge` instances. Cases cover one module; top-level sync and async
functions; classes; one and multiple methods; nested function and class qualified names;
duplicate bare names in distinct scopes; exact containment parents; normalized POSIX paths;
AST spans; repeated equality; syntax errors; `.py`-only declaration; root and package
`__init__.py`; registry compatibility; and source that would write a sentinel if executed.

Harness gold is not changed because M1.2A neither builds a snapshot nor implements its
expected calls/tests edges. `harness-smoke` must remain green to prove no schema regression.
Regression risks are accidental source execution, method over-classification, dropping
nested definitions, unstable ordering, incorrect `__init__` naming, and off-by-one columns.

## Progress

- [x] 2026-07-16: Verified the branch, clean worktree, required contracts, fixture, and
  baseline tests/types.
- [x] 2026-07-16: Defined acceptance criteria and all requested M1.2A behavior in this plan.
- [x] 2026-07-16: Implemented the AST extractor and public package export.
- [x] 2026-07-16: Added focused tests with manual expected nodes and edges; 17 focused tests
  passed and the extractor module reported 96% coverage.
- [x] 2026-07-16: Added interview questions and updated `CODEX.md` and `README.md`.
- [x] 2026-07-16: Ran and recorded the complete requested validation set.

## Decisions

- **2026-07-16 — Use existing graph contracts directly.** Alternative: add extractor-only
  fact models. The requested facts map exactly to existing nodes and edges, so another model
  layer would add conversion work without preserving new meaning.
- **2026-07-16 — Root `__init__.py` is `<root>`.** Alternative: infer a repository/package
  name unavailable to this per-file API. The sentinel is explicit, stable, and cannot be
  confused with an ordinary Python identifier.
- **2026-07-16 — Nearest definition scope controls classification and containment.**
  Alternative: remember any enclosing class and label all descendants methods. That would
  misrepresent a nested function inside a method as a class member.
- **2026-07-16 — Preserve raw AST column offsets.** Alternative: convert byte offsets to
  characters or inclusive ends. Raw offsets directly satisfy the extraction contract and
  avoid lossy or encoding-dependent reinterpretation.

## Discoveries and surprises

- **2026-07-16:** `ExtractionResult.diagnostics` is a tuple of strings rather than a typed
  diagnostic model. M1.2A therefore uses a fixed machine-readable string and does not widen
  the shared contract.
- **2026-07-16:** Existing harness IDs are readable future gold IDs, not the current
  `stable_node_id()` digests, and harness edges require later resolution. Updating them now
  would falsely imply scanner orchestration and graph construction.
- **2026-07-16:** The focused suite passed 17 tests with 96% extractor coverage. The full
  suite passed 67 tests with 3 unchanged Windows scanner-symlink skips and 92% total
  coverage; no M1.2A test was skipped.

## Validation transcript

Run from `C:\RepoLens` without network access:

```text
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest tests/test_extractors.py -v
uv run pytest
uv run repolens harness-smoke
uv run repolens doctor
git diff --check
git status --short
```

M1.2A validation on 2026-07-16, Python 3.11.15:

- `uv run ruff format .` — exit 0; 40 files left unchanged.
- `uv run ruff format --check .` — exit 0; 40 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 26 source files.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 17 passed in 0.18 seconds; the
  Python extractor module reported 96% coverage.
- `uv run pytest` — exit 0; 67 passed and 3 existing real-symlink scanner integrations
  skipped in 0.42 seconds; total coverage was 92%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.
- `git diff --check` — exit 0; only LF-to-CRLF working-copy warnings were printed.
- `git status --short` — seven intended M1.2A paths modified or untracked.

GNU Make is unavailable in the documented Windows shell. This record does not claim
`make check` ran. The three skips are the existing Windows error 1314 scanner integration
limitation; all M1.2A extractor tests ran and passed.

## Learning checkpoint

The developer must explain in their own words how a path becomes a module name; how the
scope stack distinguishes methods from nested functions; why qualified names and start
lines both contribute to stable identity; how AST locations map to `SourceSpan`; why each
definition has one nearest-parent edge; and why parsing source text cannot execute it.

Prompt: “Trace `services/user.py` containing class `Outer`, method `load`, and nested
function `validate` from `ast.parse()` through scope pushes, qualified names, spans, stable
IDs, containment edges, and final sorting. Which facts are syntax-direct, and which facts
are deliberately absent?”

## Outcome and follow-ups

M1.2A delivers deterministic isolated Python module/class/function/method definition facts,
qualified names, AST spans, existing stable IDs, nearest-parent syntax-direct containment,
and fixed syntax-error diagnostics without importing or executing source. It stops before
imports, calls, inheritance, decorator meaning, graph construction, scanner orchestration,
and CLI indexing; those remain explicit later work.
