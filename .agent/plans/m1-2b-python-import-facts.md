# Milestone 1.2B — Unresolved Python Import Fact Extraction

## Purpose and user-visible outcome

Given one repository-relative Python path and its decoded source, RepoLens will preserve
every syntactic `import` and `from ... import ...` alias as a deterministic unresolved fact.
Facts retain syntax kind, module, imported member, alias, relative level, explicit star
state, POSIX source path, and AST span. Extraction remains side-effect free and performs no
resolution.

## Scope and non-goals

This slice adds the smallest missing unresolved-import fact contract to the extractor
boundary, extends `PythonExtractor` to populate it, adds manually authored expectations to
`tests/test_extractors.py`, and updates project/learning documentation. It does not resolve
imports, inspect packages or repository targets, create module targets or cross-file edges,
extract calls/inheritance/decorator meaning, build a graph, orchestrate scanner output,
implement CLI index, or add Markdown/JavaScript/TypeScript behavior. Existing M1.2A nodes
and containment edges must compare unchanged for the same source.

## Current state

- `ExtractionResult` currently has only `nodes`, `edges`, and `diagnostics`; no existing
  model or field can represent an unresolved import fact.
- `GraphEdge(IMPORTS)` is not compatible: an edge requires a target node and would falsely
  claim resolution, which M1.2B explicitly forbids.
- `GraphNode` is also not compatible because import syntax is neither a declared symbol nor
  a target module established by evidence.
- `SourceSpan` already provides the required AST coordinate contract.
- `PythonExtractor` already performs one complete `ast.NodeVisitor` walk, including nested
  definitions and control-flow bodies, so import collection belongs in that same visitor.
- Baseline on `Python-definition-extractor`: focused extractor tests 17 passed, full suite
  67 passed with 3 existing Windows scanner-symlink skips, total coverage 92%, and Mypy
  reported no issues in 26 source files.

## Acceptance criteria

1. The extractor contract exposes `imports: tuple[UnresolvedImportFact, ...]` without
   changing existing node, edge, or diagnostic meanings.
2. `ImportFactKind.IMPORT` represents each alias in `ast.Import`; `module` is the alias
   name, `imported_member` is `None`, level is zero, and star is false.
3. `ImportFactKind.FROM_IMPORT` represents each alias in `ast.ImportFrom`; `module` is the
   statement module (nullable), `imported_member` is the alias name, level is copied, and
   `is_star` is exactly true for `*`.
4. `from . import local` uses `module=None`, `imported_member="local"`, and level 1.
5. `from ..shared import config` preserves module `shared`, member `config`, and level 2;
   it is not converted to an absolute module.
6. One statement with several `ast.alias` entries produces one fact per alias. Repeated
   identical statements remain repeated facts.
7. Imports are collected at every syntactic nesting point reached by the AST visitor,
   including module, class, function/method, conditional, and try bodies.
8. Each fact uses the alias node's AST span and the file's normalized relative POSIX path.
9. Facts are explicitly sorted and repeat extraction compares equal.
10. Parsing never imports or executes a referenced module; invalid syntax still returns
    only the existing deterministic diagnostic.
11. All M1.2A node/edge expectations and the full offline validation set remain green.

## Milestone phases

### Phase 1 — Contract decision and executable plan

Document why no existing model is compatible, define the smallest shared fact model and
result field, specify exact syntax mapping and ordering, and report the decision before
production edits.

### Phase 2 — Import fact contract

Add `ImportFactKind` and frozen `UnresolvedImportFact` to
`src/repolens/extractors/base.py`, add an immutable `imports` tuple to `ExtractionResult`,
and export the new public contract from `src/repolens/extractors/__init__.py`. Do not alter
graph models or IDs.

### Phase 3 — AST collection

Extend the existing private visitor in `src/repolens/extractors/python.py` with
`visit_Import` and `visit_ImportFrom`. Build one fact per `ast.alias`, retain alias-node
coordinates, do not deduplicate, and sort facts before returning.

### Phase 4 — Tests, documentation, and validation

Add manual expectations for every requested syntax/scope/ordering/security case, preserve
M1.2A expectations, update `CODEX.md`, `README.md`, interview questions, and this plan, then
run and record the complete requested validation set.

## Invariants and contracts

### Extractor API and smallest model change

The existing protocol remains `extract(path, source) -> ExtractionResult`. The result gains
one default-empty field:

```text
imports: tuple[UnresolvedImportFact, ...] = ()
```

The generic extractor-boundary fact is the smallest compatible addition because imports
are unresolved syntax output shared in concept across language adapters. Adding it to graph
models would imply graph membership; adding a Python-only duplicate would fragment the
common extraction contract.

### Fact representation

`UnresolvedImportFact` is frozen and forbids extra fields:

- `kind: ImportFactKind`, either `import` or `from_import`;
- `module: str | None`, the direct imported name or `ImportFrom.module`;
- `imported_member: str | None`, populated only for from-import aliases;
- `alias: str | None`, copied from `ast.alias.asname`;
- `relative_level: int >= 0`, zero for direct imports and copied for from-imports;
- `is_star: bool`, true exactly when the imported member is `*`;
- `source_path: str`, the existing normalized repository-relative POSIX path;
- `span: SourceSpan`, copied from the individual `ast.alias` node.

For `from . import local`, Python supplies `ImportFrom.module=None`; M1.2B preserves that
nullable convention rather than replacing it with an empty string or guessed package.

### Source spans

One statement can produce multiple facts, so each fact copies its own `ast.alias.lineno`,
`end_lineno`, `col_offset`, and `end_col_offset`. Lines retain AST's 1-based convention;
columns remain zero-based UTF-8 byte offsets with exclusive ends. The statement keywords
(`import`, `from`) are therefore outside an alias fact's span.

### Deterministic ordering

`UnresolvedImportFact.sort_key()` is:

```text
(
  source_path,
  span.start_line,
  span.start_column,
  kind.value,
  module or "",
  imported_member or "",
  alias or "",
  relative_level,
  is_star,
)
```

The extractor returns `tuple(sorted(visitor.imports, key=UnresolvedImportFact.sort_key))`.
No set or deduplication step is allowed, so identical syntax at different spans survives.

### Strict resolution and execution boundary

`ast.Import` and `ast.ImportFrom` are syntax nodes; visiting them does not invoke Python's
import machinery. M1.2B never calls `importlib`, `__import__`, package metadata, filesystem
target lookup, or repository search. It does not label an import standard-library,
third-party, or local, expand a star, or create a target/edge.

### Exact expected file set

Only these eight paths are expected to change:

- `.agent/plans/m1-2b-python-import-facts.md`;
- `src/repolens/extractors/base.py`;
- `src/repolens/extractors/python.py`;
- `src/repolens/extractors/__init__.py`;
- `tests/test_extractors.py`;
- `CODEX.md`;
- `README.md`;
- `docs/INTERVIEW_QUESTIONS.md`.

## Test and harness plan

Manually constructed facts in `tests/test_extractors.py` cover simple, dotted, aliased,
and multi-alias direct imports; basic, aliased, and multi-member from-imports; dot-relative,
multi-level relative, and star imports; imports inside function, class/method, conditional,
and try bodies; repeated facts; deterministic sorting; relative POSIX paths; alias spans;
non-execution; invalid syntax; and unchanged M1.2A nodes/edges. Production serialization is
not copied into expected values.

Harness gold remains unchanged because it expects resolved future graph relationships, not
isolated unresolved import facts. `harness-smoke` must remain green.

## Progress

- [x] 2026-07-16: Verified the requested branch and clean worktree, read all required
  contracts, and ran the baseline validation.
- [x] 2026-07-16: Determined that no existing model/result field is compatible and defined
  the smallest generic extractor-boundary addition in this plan.
- [x] 2026-07-16: Added the import-fact contract and `ExtractionResult.imports` field.
- [x] 2026-07-16: Extended the Python AST visitor without changing M1.2A definition output.
- [x] 2026-07-16: Added manual tests and project/learning documentation; all 34 focused
  tests passed, base contract coverage was 100%, and Python extractor coverage was 96%.
- [x] 2026-07-16: Ran and recorded the full validation set and inspected the complete diff.

## Decisions

- **2026-07-16 — Facts, not graph edges.** An `IMPORTS` edge requires a known target node;
  emitting one during syntax extraction would promote unresolved text into a resolved
  relationship.
- **2026-07-16 — Generic extractor-boundary model.** A shared `UnresolvedImportFact` in
  `extractors/base.py` avoids a Python-only duplicate while keeping unresolved syntax out of
  normalized graph models.
- **2026-07-16 — Nullable module for module-less relative imports.** Preserve
  `ast.ImportFrom.module is None` for `from . import local`; do not guess package context.
- **2026-07-16 — Alias-node spans.** One import statement may yield several facts, so the
  individual alias is the narrowest repeatable evidence span.

## Discoveries and surprises

- **2026-07-16:** The living extraction contract says extractors return unresolved syntax
  facts, but `ExtractionResult` had no field for them. M1.2B supplies that missing channel.
- **2026-07-16:** Running focused and full pytest concurrently on Windows caused both
  processes to contend for `.coverage`; sequential reruns passed. Final pytest validation
  must remain sequential.
- **2026-07-16:** All 34 focused tests passed with 100% coverage for the import-fact contract
  and 96% for the Python extractor. The full suite passed 84 tests with 3 unchanged Windows
  scanner-symlink skips and 92% total coverage.

## Validation transcript

Run sequentially from `C:\RepoLens` without network access:

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

M1.2B validation on 2026-07-16, Python 3.11.15:

- `uv run ruff format .` — exit 0; 40 files left unchanged.
- `uv run ruff format --check .` — exit 0; 40 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 26 source files.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 34 passed in 0.19 seconds; import
  contract coverage was 100% and Python extractor coverage was 96%.
- `uv run pytest` — exit 0; 84 passed and 3 existing scanner-symlink integrations skipped
  in 0.39 seconds; total coverage was 92%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.
- `git diff --check` — exit 0; only LF-to-CRLF working-copy warnings were printed.
- `git status --short` — exactly the eight planned M1.2B paths were modified or untracked.

GNU Make is unavailable in the documented Windows shell. This record does not claim
`make check` ran. The three skips are the existing Windows error 1314 scanner integration
limitation; every M1.2B extractor test ran and passed.

## Learning checkpoint

The developer must explain in their own words how `ast.Import` differs from
`ast.ImportFrom`; why one statement creates one fact per alias; how aliases and relative
levels are preserved without resolution; why `*` remains explicit and unexpanded; how alias
spans and sorting keep repeated facts deterministic; and why parsing never executes an
import.

Prompt: “Trace `from ..shared import config as settings` from AST fields to one unresolved
fact. Which fields are direct syntax evidence, what does level 2 mean, and which target or
environment claims are deliberately absent?”

## Outcome and follow-ups

M1.2B delivers deterministic unresolved import facts for all requested direct, from,
relative, aliased, multi-member, nested, repeated, and star syntax. Facts retain alias-node
spans and normalized paths, and parsing neither resolves nor executes imports. Cross-file
targets/edges, calls, inheritance, graph building, scanner orchestration, and CLI indexing
remain later work.
