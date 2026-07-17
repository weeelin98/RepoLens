# Milestone 2.1A — Tree-sitter Foundation and Basic JavaScript/TypeScript Extraction

## Purpose and user-visible outcome

`repolens index PATH` will discover accepted `.js` and `.ts` files and add deterministic
syntax-direct JavaScript and TypeScript module, function, class, method, named-arrow,
static-ESM-import, and direct-ESM-export facts to canonical `graph.json`. Parsing uses pinned
Python tree-sitter wheels and never invokes Node, npm, a TypeScript compiler, target source,
or a network service.

## Scope and non-goals

This slice adds only `.js` and `.ts`. It creates one module per parsed file; named function
and async-function declarations; class declarations; ordinary named class methods; direct
identifier arrow assignments; nearest-named-parent containment; typed unresolved ESM import
and export facts; exact tree-sitter spans; and deterministic partial-parse diagnostics.

Out of scope are JSX, TSX, React components, CommonJS, re-exports, anonymous/default-
anonymous definitions, callbacks, object methods, constructors, accessors, interfaces,
types, enums, namespaces, overload signatures, declaration-file special cases, dynamic
imports, calls, optional chaining, resolution, tsconfig paths, installed dependencies,
endpoint linking, overview/context/impact output, caching, and MCP. Milestone 2 remains open.

## Current state

- Baseline branch `javascript-typescript-extractor` is clean and based on `main` at
  `8197b09`; 186 tests pass, 3 real-symlink tests skip on Windows error 1314, total coverage
  is 92%, Mypy reports no issues in 33 source files, and doctor is healthy.
- Scanner defaults accept `.py`, `.md`, and three exact metadata basenames. Eligibility
  precedes ignore, containment, `stat()`, limits, and output pruning.
- Registry lookup prefers an exact basename, then a lowercase suffix. A caller-supplied
  registry remains authoritative and is never mutated.
- Existing module/class/function/method nodes already carry kind, language, relative POSIX
  path, exact span, qualified name, and stable ID. `GraphSnapshot` normalizes graph output.
- `UnresolvedImportFact` encodes Python-only `import`/`from_import`, relative levels, and
  star semantics. Reusing it for ESM would make several fields misleading.
- `RepositoryIndexResult` already keeps unresolved Python imports, Markdown facts, metadata
  facts, and diagnostics outside the graph and canonically serializes the full result.
- The TypeScript and full-stack fixtures contain `.ts` plus unsupported `.tsx`. M1 gold
  must remain a byte-exact historical contract while M2.1A gets one separate partial-slice
  gold record.

## Acceptance criteria

1. Runtime dependencies resolve to tree-sitter 0.26.0, tree-sitter-javascript 0.25.0, and
   tree-sitter-typescript 0.23.2 under constrained compatible declarations.
2. `Language(tree_sitter_javascript.language())` and
   `Language(tree_sitter_typescript.language_typescript())`, each passed to `Parser`, parse
   real JS/TS without errors; ABI 15 runtime accepts JS ABI 15 and TS ABI 14.
3. Scanner defaults add exactly `.js` and `.ts`; `.jsx`, `.tsx`, `.mjs`, and `.cjs` remain
   unsupported, and all existing discovery safeguards remain unchanged.
4. One `JavaScriptTypeScriptExtractor` declares exactly `.js`/`.ts`, performs no I/O, and
   returns existing `ExtractionResult` plus typed ESM fact tuples.
5. Every parsed file has one module named only from its extensionless relative path:
   `src/utils.js -> src.utils`, `src/user.ts -> src.user`, `index.js -> index`.
6. Module/definition spans map tree-sitter zero-based rows to one-based lines while
   preserving zero-based UTF-8 byte columns and exclusive end coordinates.
7. Named function/async-function and class declarations, ordinary class methods, and direct
   identifier arrow declarators are extracted. Constructors, get/set accessors, object
   methods, destructuring, callbacks, and anonymous scopes are excluded.
8. Qualified names append each extracted name to the nearest extracted lexical parent.
   Unsupported anonymous scopes are barriers rather than silently skipped parents.
9. Stable IDs use kind, relative path, qualified name, start line, and start column as a
   disambiguator. Repeated same-name declarations on one line remain distinct.
10. Each definition has exactly one syntax-direct confidence-1.0 `contains` edge from its
    nearest extracted module/class/function/method parent.
11. Static side-effect, default, namespace, and named ESM imports become separate typed
    facts with module text, imported/local names, path, and narrow syntax spans. No target
    lookup or `IMPORTS` edge occurs.
12. Direct named declaration, named default declaration, arrow declaration, and local
    export-list syntax becomes typed export facts. Re-exports and `EXPORTS` edges are absent.
13. A tree containing ERROR or missing nodes yields one stable first-error diagnostic and
    a module plus facts only from top-level subtrees whose `has_error` is false. Erroneous
    subtrees and unsupported anonymous scope subtrees are not traversed for facts.
14. Nodes, edges, ESM imports, ESM exports, and diagnostics sort explicitly; repeated
    extraction and indexing compare equal and serialize byte-identically without absolute
    paths.
15. New empty ESM channels are omitted from canonical JSON, so all committed M1 gold bytes
    remain unchanged and old graph JSON parses with default-empty M2 collections.
16. The TypeScript frontend receives one separate M2.1A partial gold snapshot covering its
    `.ts` file and `tsconfig.json`; its `.tsx` file remains absent and the fixture is not
    claimed complete.
17. Focused cases 1–42 from the implementation request, existing regressions, full offline
    validation, and the two-run manual smoke all pass.

## Milestone phases

### Phase 1 — Dependency and contract proof

Verify maintained releases from primary package sources, construct both real parsers in an
isolated uv environment, record ABI/API results, define ESM fact models and partial-parse
policy, and report all requested decisions before production edits.

### Phase 2 — Tests and typed boundary

Add focused authored tests for extractor syntax, spans, IDs, facts, diagnostics, security,
and determinism. Add `EsmImportKind`, `EsmExportKind`, `UnresolvedEsmImportFact`, and
`UnresolvedEsmExportFact`; extend extraction/repository results with deterministic channels
that serialize only when nonempty.

### Phase 3 — Tree-sitter extractor and repository integration

Add `src/repolens/extractors/javascript_typescript.py`; extend scanner defaults; export and
register the extractor; merge ESM facts; label JS/TS file nodes; retain generic root-node
containment; and count both Python and ESM imports in CLI success output.

### Phase 4 — Historical M1 and partial M2 acceptance

Keep M1 gold files unchanged by making the M1 acceptance helper/test copy fixtures with
root ignore rules for post-M1 `.js`/`.ts` support. Add one `m2-1a-graph.json` for the
TypeScript frontend and assert that `.ts` is indexed while `.tsx` remains excluded.

### Phase 5 — Documentation, smoke, and validation

Update `CODEX.md`, `README.md`, interview questions, and this plan. Run all requested
commands sequentially, perform the two-run temporary repository smoke, remove generated
output, and audit the full diff/status. Do not commit or push.

## Invariants and contracts

### Dependencies and parser construction

Declare `tree-sitter>=0.26,<0.27`, `tree-sitter-javascript>=0.25,<0.26`, and
`tree-sitter-typescript>=0.23.2,<0.24`; regenerate `uv.lock` only through uv. Construct
languages with capsule APIs and instantiate a fresh parser per extraction:

```python
Parser(Language(tree_sitter_javascript.language()))
Parser(Language(tree_sitter_typescript.language_typescript()))
```

The exact verified lock candidates are runtime 0.26.0, JavaScript grammar 0.25.0, and
TypeScript grammar 0.23.2. The runtime supports grammar ABI 13–15; the installed grammars
report ABI 15 and 14 respectively.

### Typed ESM facts and backward-compatible serialization

Python `UnresolvedImportFact` remains unchanged. ESM uses separate frozen models:

```text
UnresolvedEsmImportFact(kind, module, imported_name, local_name, source_path, span)
UnresolvedEsmExportFact(kind, exported_name, local_name, is_default, source_path, span)
```

Import kinds are `side_effect`, `default`, `namespace`, and `named`; export kinds are
`declaration` and `list`. `ExtractionResult` and `RepositoryIndexResult` gain `esm_imports`
and `esm_exports`. Repository fields use Pydantic `exclude_if` for empty tuples, so M1 JSON
does not gain empty keys. This additive default-empty contract does not require a graph
schema-version change.

### Naming, spans, IDs, and containment

Normalize paths with the existing helper, remove only the final suffix, and dot-join parts.
Each definition appends its direct syntax name to its extracted parent. Tree-sitter points
map `(row, column)` to `(line=row+1, column=column)`; columns remain bytes and end points
remain exclusive. Arrow definition spans use the exact `variable_declarator`; other nodes
use their declaration node. Stable IDs use existing semantic fields plus a deterministic
`column:<start-column>` disambiguator. No parser node identity or traversal order enters IDs.

### Conservative partial trees

The program root may contain recoverable errors. Always emit the module for a returned
tree. Locate the first ERROR/missing node by byte position for
`tree_sitter_syntax_error:<path>:<line>:<column>`. Visit only root children and nested
declaration subtrees whose `has_error` is false. Never use regex fallback or exception
prose. Parser setup compatibility is a locked installation invariant, not hidden by a broad
catch.

### Exact expected file set

- `.agent/plans/m2-1a-tree-sitter-js-ts-foundation.md`
- `pyproject.toml`, `uv.lock`
- `src/repolens/scanner.py`, `src/repolens/indexer.py`, `src/repolens/cli.py`
- `src/repolens/extractors/base.py`, `src/repolens/extractors/__init__.py`
- `src/repolens/extractors/javascript_typescript.py`
- `tests/test_javascript_typescript_extractor.py`
- `tests/test_scanner.py`, `tests/test_indexer.py`, `tests/test_cli.py`
- `tests/test_milestone1_acceptance.py`, `scripts/update_m1_acceptance_gold.py`
- `harness/fixtures/typescript_frontend/m2-1a-graph.json`
- `CODEX.md`, `README.md`, `docs/INTERVIEW_QUESTIONS.md`

No M1 gold, future resolver/query gold, existing fixture source, CI, or production resolver
file is expected to change.

## Test and harness plan

`tests/test_javascript_typescript_extractor.py` covers extension declaration; JS/TS module
roots; all supported declarations; nesting/parents; exclusions; spans; literal stable IDs;
five import forms; direct/default/list exports; unresolved boundaries; malformed partial
trees; non-execution; determinism; and unsupported JSX/TSX. Existing scanner/indexer/CLI
tests gain only focused integration cases for eligibility, ignore, structure, canonical
facts, path privacy, output pruning, and repeated bytes.

The TypeScript frontend fixture supplies the minimal M2.1A partial gold. Its `.ts` source
and `tsconfig.json` are included; `.tsx` is deliberately absent. Full M2 fixture acceptance
waits for JSX/TSX. Existing M1 gold files and future `gold.json` remain unchanged.

## Progress

- [x] 2026-07-17: Verified branch, clean current-main ancestry, baseline tests/types, and
  doctor.
- [x] 2026-07-17: Read governing docs, relevant M1 plans, contracts, implementations,
  tests, fixtures, dependency files, interview questions, and CI.
- [x] 2026-07-17: Verified current package releases, parser construction, real JS/TS parses,
  and grammar ABI compatibility before production edits.
- [x] 2026-07-17: Defined acceptance criteria and all fifteen requested design decisions.
- [x] 2026-07-17: Added typed ESM contracts, locked dependencies, and focused tests.
- [x] 2026-07-17: Implemented extraction and scanner/registry/indexer/CLI integration.
- [x] 2026-07-17: Preserved M1 gold bytes and added the partial M2.1A gold check.
- [x] 2026-07-17: Completed documentation, two-run smoke, full validation, and scope audit.
- [x] 2026-07-17: Applied final review fixes for type-only ESM filtering and the Pydantic
  2.12 serialization dependency floor; repeated full validation without widening scope.

## Decisions

- **2026-07-17 — Use official per-language wheels with runtime 0.26.** This matches current
  maintained package releases, has Windows/Linux wheels, exposes capsule construction, and
  passed real ABI/parser smoke tests.
- **2026-07-17 — Separate ESM facts from Python import facts.** Python relative-level and
  star rules do not represent ESM accurately. Two typed ESM channels preserve direct syntax
  without weakening either contract or creating target edges.
- **2026-07-17 — Preserve M1 bytes with conditional empty-field serialization.** New facts
  are additive and absent from old outputs. M1 gold remains historical rather than being
  rewritten to include M2 behavior.
- **2026-07-17 — Treat erroneous and anonymous scopes as barriers.** Facts inside an ERROR,
  missing, callback, object-method, constructor, accessor, or unsupported anonymous scope
  cannot receive an honest nearest extracted parent in this slice.
- **2026-07-17 — Use source column in JS/TS ID disambiguation.** JavaScript permits repeated
  same-name declarations on one physical line; line-only identity could collide.
- **2026-07-17 — Omit type-only ESM syntax.** M2.1A has no type-relationship model or
  type-only discriminator, so erased TypeScript imports and exports cannot be represented as
  runtime ESM facts. Mixed clauses retain only their runtime specifiers.

## Discoveries and surprises

- Current latest maintained versions are not numerically aligned: runtime 0.26.0,
  JavaScript grammar 0.25.0, and TypeScript grammar 0.23.2. Their real ABI values are
  compatible despite different package versions.
- Adding `.ts` to default scanning makes historical M1 fixture runs see TypeScript source.
  M1 acceptance therefore needs an explicit historical source profile while retaining
  unchanged gold bytes.
- Pydantic 2.13.4 supports field-level `exclude_if`, allowing new nonempty M2 channels to
  serialize without inserting empty keys into M1 output. Because `exclude_if` was introduced
  in Pydantic 2.12, the declared runtime floor must also be 2.12 rather than 2.8.
- The TypeScript grammar marks statement-level and inline type-only syntax with an unnamed
  `type` token on the statement or individual specifier, enabling mixed clauses to be
  filtered without suppressing supported runtime specifiers.
- The TypeScript grammar represents declared class names as `type_identifier`, unlike the
  JavaScript grammar's `identifier`; accepting only the JS shape silently dropped TS
  classes and their direct export facts.
- Bare TypeScript namespaces/modules and JavaScript generator declarations need explicit
  scope barriers. Generic traversal otherwise finds nested declarations and assigns them a
  false module parent.
- An empty ESM module specifier parses successfully but cannot satisfy the deliberately
  nonempty unresolved-module contract, so it is conservatively ignored rather than
  crashing repository indexing.

## Validation transcript

Baseline on 2026-07-17:

- branch `javascript-typescript-extractor`; clean status; `main` is an ancestor.
- `uv sync --dev --locked` — 27 packages resolved, 26 checked.
- `uv run pytest` — 186 passed, 3 Windows error-1314 symlink skips, 92% coverage.
- `uv run mypy src tests` — no issues in 33 source files.
- `uv run repolens doctor` — Python 3.11.15/package 0.1.0 healthy; no network required.
- Isolated exact-version parser smoke — JS program parsed with ABI 15 and no error; TS
  program parsed with ABI 14 and no error under runtime ABI support 13–15.

Final validation on 2026-07-17 with Python 3.11.15:

- `uv sync --dev --locked` resolved 30 packages and checked 29.
- Ruff formatting/check and full lint passed; Mypy reported no issues in 35 source files.
- Focused suites passed: JS/TS extractor 36; existing extractors 36; scanner 35 plus 3
  Windows error-1314 symlink skips; indexer 29; CLI 21; M1 acceptance 16.
- Full pytest passed 231 tests, skipped the same 3 privileged symlink integrations, and
  reported 93% total coverage; the JS/TS extractor reported 96% coverage.
- Harness smoke validated 5 fixtures, 5 questions, and 5 diff cases. Doctor reported
  Python 3.11.15/package 0.1.0 healthy and no network requirement.
- Two CLI smoke indexes produced 13 nodes, 12 edges, 1 ESM import, 2 ESM exports, and 1
  expected partial-parse diagnostic. Both outputs had SHA-256
  `655dd2d175619d192c0befcc9a32e2cac719f507c29aa5dd67a0dae7bd185e45`; `.tsx` stayed
  excluded and the temporary absolute path did not enter JSON.
- All four M1 gold files remained byte-identical. The separate TypeScript frontend
  `m2-1a-graph.json` matched its `.ts`/tsconfig partial snapshot.

## Learning checkpoint

The developer must explain why Python AST cannot parse JS/TS; how the runtime/grammar ABI
contract differs from matching package version numbers; how byte-oriented tree-sitter
points map to `SourceSpan`; why ESM imports/exports remain facts rather than edges; how a
recoverable partial tree differs from Python `ast.parse()` failure; why stable IDs exclude
tree node identity/traversal order; and why JSX/TSX and calls require later explicit slices.

## Outcome and follow-ups

M2.1A is complete: `.js`/`.ts` modules, the bounded definition set, and unresolved direct
ESM facts flow deterministically through `graph.json` without target edges or M1 gold
changes. The planned next slice is Milestone 2.1B — CommonJS, re-exports, and additional
TypeScript declarations. Milestone 2 remains open.
