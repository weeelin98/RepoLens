# Milestone 1.4B — Deterministic Project Metadata Extraction

## Purpose and user-visible outcome

`repolens index PATH` will discover and parse exactly `pyproject.toml`, `package.json`, and
`tsconfig.json`, retain only documented direct structural fields as immutable metadata
facts, and serialize them in the existing deterministic `RepositoryIndexResult` and
`graph.json`. Arbitrary JSON/TOML, lockfiles, generated output, scripts, entry points,
build backends, installed packages, and TypeScript configuration are never executed or
resolved.

## Scope and non-goals

This slice adds exact-basename discovery alongside suffix discovery, exact-basename
extractor registration, one typed project-metadata fact contract, standard TOML/JSON
parsing, constrained JSONC parsing, default indexer integration, focused tests, and project
documentation.

It does not parse arbitrary `.json`/`.toml`, lockfiles, inspect installed dependencies,
resolve versions/exports/entry points/tsconfig paths or `extends`, create dependency nodes
or edges, execute scripts/build code, extract JavaScript/TypeScript source, resolve imports,
generate an overview/context pack, change MCP, or close Milestone 1.

## Current state

- Scanner eligibility is a normalized suffix membership check against `.py` and `.md`.
  Ignore matching, symlink containment, output pruning, `stat()`, and resource accounting
  happen after that eligibility check.
- `SourceFile` can already represent the three metadata files because their suffixes are
  `.toml` or `.json`, but accepting those suffixes globally would expose arbitrary and
  potentially secret configuration files.
- `ExtractorRegistry` maps normalized extensions to extractors. The protocol and registry
  require at least one extension and have no exact-filename selector.
- `ExtractionResult` and `RepositoryIndexResult` already keep immutable unresolved imports
  and Markdown facts outside `GraphSnapshot`; this is the compatible pattern for direct
  metadata that has no graph endpoint.
- `GraphNode.metadata` could enrich a structural file, but would mix discovery metadata
  with parsed manifest semantics. `EXTERNAL_DEPENDENCY` nodes could be deterministic, but
  would imply graph materialization and complicate group/source traceability before a
  resolver exists.
- Python 3.11 provides `tomllib`; standard `json` handles strict `package.json`. No JSONC
  dependency exists. PyPI reports `json-with-comments` 1.2.10 as a pure-Python parser layer
  supporting single/block comments and trailing commas on Python 3.11.
- Existing harness repositories already contain all three target basenames: the full-stack
  fixture has `pyproject.toml` and `package.json`; the TypeScript fixture has
  `tsconfig.json`. No new fixture is needed for direct extraction smoke coverage.
- Baseline on branch `Python-definition-extractor`: the worktree was clean; 144 tests
  passed, 3 scanner symlink integrations skipped because Windows returned privilege error
  1314; total coverage was 92%; Mypy reported no issues in 30 source files.

## Acceptance criteria

1. Default scanning accepts `.py`, `.md`, and files whose basename is exactly
   `pyproject.toml`, `package.json`, or `tsconfig.json`; it rejects every other `.json` and
   `.toml`, including lockfiles, while preserving all ignore, containment, pruning, and
   resource-limit behavior.
2. A shared immutable filename constant in `config.py` is the sole default list used by
   scanner discovery and the metadata extractor; filename conditions are not repeated in
   the indexer or CLI.
3. `Extractor` exposes both extension and exact-filename selectors. Registry lookup checks
   exact filename first, then extension, rejects conflicts per selector, and still supports
   fresh default and authoritative injected registries.
4. `ProjectMetadataExtractor` declares no extensions and exactly the three supported
   filenames. It parses source without importing, executing, resolving, fetching, or
   invoking any declared value.
5. `ProjectMetadataFact` is frozen and contains ecosystem, documented dotted field name,
   recursively normalized JSON-compatible value, repository-relative POSIX source path,
   and optional `SourceSpan` (unset in this slice).
6. `pyproject.toml` uses `tomllib` and retains the documented `[project]` fields,
   `project.dynamic`, and `[build-system]` fields only. Dependency strings remain exact;
   dynamic values are named but never evaluated.
7. `package.json` uses strict standard JSON and retains only the documented package fields.
   Nested values remain JSON-compatible; scripts are data and are never run.
8. `tsconfig.json` uses constrained `json-with-comments>=1.2.10,<2`, retains only the four
   root structural fields and selected compiler options, and never resolves paths,
   `extends`, aliases, projects, or installed types.
9. Malformed TOML, JSON, or JSONC yields exactly one deterministic extractor diagnostic,
   no facts for that file, preserves its structural file node, permits later files, and is
   a non-fatal CLI warning.
10. Facts and complete repository results normalize deterministically; mappings sort by
    key, set-like string arrays sort where explicitly safe, semantically meaningful arrays
    retain declaration order, and fact ordering uses source path, ecosystem, field, and
    canonical value.
11. Repeated extraction and CLI indexing are equal/byte-identical, contain no absolute
    roots or source bodies, and all requested focused/full validation and manual smoke pass.

## Milestone phases

### Phase 1 — Exact selector and fact contracts

Add the shared `PROJECT_METADATA_FILENAMES` constant to `src/repolens/config.py`; extend
scanner eligibility in `src/repolens/scanner.py`; extend the extractor protocol and
registry for exact filenames; add `MetadataEcosystem` and `ProjectMetadataFact` plus a
`metadata_facts` result channel in `src/repolens/extractors/base.py`.

### Phase 2 — Metadata parsing

Add `src/repolens/extractors/metadata.py`. Dispatch only from the exact basename, parse
TOML/JSON/JSONC with their chosen parsers, select documented fields, normalize direct
values, catch only expected parse/value errors, and return sorted source-path-only facts.
Add `json-with-comments>=1.2.10,<2` directly to `pyproject.toml` and update `uv.lock` only
through `uv lock`.

### Phase 3 — Registry and indexer integration

Add empty filename selectors to Python and Markdown extractors, export/register the
metadata extractor, merge `metadata_facts` into `RepositoryIndexResult`, and leave graph
nodes/edges unchanged beyond the structural file nodes already produced by indexing.

### Phase 4 — Focused tests

Create `tests/test_metadata_extractor.py`. Extend scanner tests for exact selection and
limits, registry tests for filename lookup/conflicts, indexer tests for structural/fact and
failure behavior, and CLI tests for canonical metadata output and repeated bytes. Run the
existing Python and Markdown suites unchanged as regressions.

### Phase 5 — Documentation, validation, and smoke

Update `CODEX.md`, `README.md`, `docs/INTERVIEW_QUESTIONS.md`, and this plan. Run every
requested command sequentially. Build a temporary repository containing the three target
files plus arbitrary JSON/TOML, index it twice, inspect facts/non-execution/path privacy,
compare bytes, remove it, and audit the final diff/status. Existing harness fixture content
is sufficient and gold remains a later M1.5 closeout concern.

## Invariants and contracts

### Exact file discovery

`scan_repository(..., supported_filenames=PROJECT_METADATA_FILENAMES)` accepts a file when
either its normalized supported suffix matches or its basename exactly matches the supplied
filename set. Exact filename matching is case-sensitive and basename-only. Eligibility is
checked before ignore/containment/stat/limits, while every eligible metadata file then
passes through the same safety/accounting pipeline as source files.

The scanner does not accept `.json` or `.toml` as suffixes. Thus `package-lock.json`,
`secret.json`, `config.toml`, and any other non-target basename are not read, counted, or
represented. Output-directory pruning remains top-down before filename examination.

### Registry selection

`Extractor` exposes frozen `extensions` and `filenames` sets. The registry stores separate
normalized extension and exact filename maps, requires at least one selector total, and
rejects conflicts within each map. `for_path()` prefers an exact basename match over a
suffix match. This supports future specialized manifests without filename checks in the
indexer and preserves current extension adapters.

### Metadata fact model

`MetadataEcosystem` values are `python_project`, `node_package`, and `typescript_config`.
`ProjectMetadataFact` fields are `ecosystem`, dotted `field`, direct `value`, `source_path`,
and optional `span`. A validator recursively orders string-keyed mappings, preserves lists
unless a field extractor deliberately treats them as set-like, and rejects non-finite or
non-JSON-compatible values. `sort_key()` uses a compact canonical JSON value string.

Facts live in `ExtractionResult.metadata_facts` and
`RepositoryIndexResult.metadata_facts`. They do not enrich structural file nodes or create
`EXTERNAL_DEPENDENCY` nodes/edges. This mirrors unresolved imports/Markdown facts, retains
ecosystem/field/group provenance, and avoids implying installation or resolution.

### Parsed field policy

Pyproject facts use dotted names under `project.*` and `build-system.*`. Dependency arrays,
dynamic field names, optional-dependency group arrays, and build requirements are sorted
because their order is not semantic. Script/GUI/entry-point mappings are recursively key
sorted. Dependency strings are never parsed or rewritten.

Package facts use their documented JSON spellings. Dependency/script/engine/export maps
are recursively key sorted. Workspace arrays are sorted when they are plain strings;
structured workspace objects preserve their nested direct shape. Other documented arrays
retain their declaration order.

Tsconfig facts use `extends`, `files`, `include`, `exclude`, and
`compilerOptions.<name>`. Pattern/file/type/lib arrays are preserved as declared because
future TypeScript behavior may depend on precedence or user intent; `paths` maps sort alias
keys while preserving each target array order.

### Parser and failure policy

`tomllib.loads()` parses pyproject TOML without importing Python or invoking build hooks.
`json.loads()` parses package JSON with duplicate-key and non-finite-constant rejection.
`jsonc.loads()` from `json-with-comments` removes JSONC comments/trailing commas and delegates
to the same strict JSON hooks. Parser results must be objects.

Catch only `tomllib.TOMLDecodeError`, `json.JSONDecodeError`, and expected `ValueError` or
`TypeError` from JSONC/shape/value validation. Return
`metadata_parse_error:<source-path>:<format>` with no facts. Files already remain in the
structural graph and later scanned files continue.

### Source evidence

All three formats retain normalized repository-relative source paths. `tomllib`, standard
JSON, and the chosen JSONC layer do not expose reliable per-field token positions. Facts
therefore use `span=None`; no global key search or guessed line/column is performed.

### Determinism and security

Facts sort by source path, ecosystem, field, and canonical normalized value. The repository
result sorts them again before canonical serialization recursively sorts JSON keys. No
absolute roots, clocks, random identifiers, installed state, environment contents, source
bodies, or network data enter facts.

Parsing treats scripts, entry points, backends, exports, dependencies, and paths only as
data. It never imports a project, invokes subprocesses, evaluates JavaScript, reads
`node_modules`, resolves filesystem targets, or accesses the network.

## Test and harness plan

`tests/test_metadata_extractor.py` will use manually authored strings for all documented
pyproject/package/tsconfig fields, dynamic metadata, JSONC comments/trailing commas,
malformed formats, deterministic normalization, relative paths, and non-execution.

`tests/test_scanner.py` will verify the three basenames are eligible while arbitrary
JSON/TOML/locks are not, ignored/output files remain excluded, and file/byte limits apply
before extraction. `tests/test_extractors.py` will verify filename registration, exact
precedence, conflicts, and current extension behavior.

`tests/test_indexer.py` will verify facts plus structural nodes, ignored metadata, malformed
continuation, authoritative injection, and path privacy. `tests/test_cli.py` will verify
complete `graph.json`, warnings, byte equality, and non-execution. Existing Python and
Markdown tests remain regression suites.

Existing harness repositories already provide all target filenames. `harness-smoke` remains
a schema regression check; production fixture-gold comparison and byte closeout remain
M1.5, so no harness file is expected to change.

## Progress

- [x] 2026-07-17: Verified the requested branch and clean worktree; baseline pytest and
  Mypy passed with the documented Windows symlink skips.
- [x] 2026-07-17: Read the governing docs, M1.4A plan, contracts, scanner, registry,
  extractors, indexer, CLI, serializer, tests, dependencies, fixtures, and interview notes.
- [x] 2026-07-17: Defined acceptance criteria and the eleven requested design decisions
  before production edits.
- [x] 2026-07-17: Added exact-filename and metadata-fact contracts.
- [x] 2026-07-17: Implemented parsers and repository integration.
- [x] 2026-07-17: Added focused scanner/extractor/indexer/CLI tests.
- [x] 2026-07-17: Updated project documentation and learning questions.
- [x] 2026-07-17: Ran full validation, manual smoke, and final scope audit.

## Decisions

- **2026-07-17 — Exact basenames supplement suffixes.** Broad `.json`/`.toml` support would
  read unrelated, generated, or secret files. A shared three-name set gives the scanner and
  registry one auditable selection boundary.
- **2026-07-17 — Metadata remains typed unresolved facts.** Structural file metadata is a
  discovery concern, while external nodes would imply graph materialization. A dedicated
  fact channel preserves direct values and provenance without a resolution claim.
- **2026-07-17 — Use standard TOML/JSON and one constrained JSONC dependency.** `tomllib`
  and `json` already cover two formats. `json-with-comments` 1.2.10 is small, pure Python,
  supports the required comments/trailing commas, and avoids fragile regex preprocessing in
  RepoLens.
- **2026-07-17 — Use path-only source evidence.** None of the chosen parsers exposes field
  token positions. Searching repeated keys across nested objects could attach false spans,
  so `span=None` is the honest contract.
- **2026-07-17 — Preserve dependencies as declarations.** Values and groups remain direct
  metadata; no version parsing, installed lookup, target node, or dependency edge is added.

## Discoveries and surprises

- **2026-07-17:** Scanner suffix filtering occurs before `.gitignore`, symlink checks,
  `stat()`, and limits. Adding exact filename eligibility at that same point automatically
  preserves all downstream safety behavior.
- **2026-07-17:** Registry selection currently occurs after scanning and before source
  loading. Exact filename lookup therefore needs no indexer filename branch and maintains
  the rule that unmatched accepted files remain structural-only.
- **2026-07-17:** The harness already contains all three target manifests, so adding fixture
  content solely for M1.4B would duplicate existing examples.
- **2026-07-17:** Concurrent pytest processes can contend for `.coverage` on Windows; all
  validation test commands will run sequentially.

## Validation transcript

Baseline before production edits:

- `git branch --show-current` — `Python-definition-extractor`.
- `git status --short` — no output.
- `uv run pytest` — 144 passed, 3 skipped for Windows symlink privilege error 1314; total
  coverage 92%.
- `uv run mypy src tests` — success, no issues in 30 source files.

Final M1.4B results:

- `uv sync --dev --locked` — exit 0; 27 packages resolved and 26 checked.
- `uv run ruff format .` — exit 0; 46 files left unchanged.
- `uv run ruff format --check .` — exit 0; 46 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 32 source files.
- `uv run pytest tests/test_metadata_extractor.py -v` — exit 0; 17 passed; metadata
  extractor coverage was 94%.
- `uv run pytest tests/test_markdown_extractor.py -v` — exit 0; 24 passed; Markdown
  extractor coverage was 92% in the focused run.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 36 passed; Python extractor
  coverage was 97% and registry coverage was 95%.
- `uv run pytest tests/test_indexer.py -v` — exit 0; 24 passed; indexer coverage was 93%.
- `uv run pytest tests/test_cli.py -v` — exit 0; 19 passed; CLI coverage was 84%.
- Additional focused `uv run pytest tests/test_scanner.py -v` — exit 0; 33 passed and the
  3 existing Windows real-symlink integrations skipped; scanner coverage was 96%.
- `uv run pytest` — exit 0; 170 passed and the same 3 scanner integrations skipped because
  Windows returned symlink privilege error 1314; total coverage was 92%, metadata extractor
  coverage was 94%, serialization coverage was 100%, and indexer coverage was 93%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 healthy; no network
  required.
- `git diff --check` — exit 0; no whitespace errors.
- `git status --short` — exactly 20 planned M1.4B paths modified or untracked.

Manual smoke created a temporary repository with the three supported manifests plus
`secret.json` and `config.toml`, then ran `repolens index` twice. Both runs reported 3
files, 4 nodes, 3 edges, 0 imports, and 0 warnings. Inspection found 10 metadata facts from
only `package.json`, `pyproject.toml`, and `tsconfig.json`; arbitrary values did not leak,
the declared package script did not execute, bytes matched, no absolute root appeared, and
the output ended with a newline. The verified temporary repository was removed.

GNU Make is unavailable in this Windows environment and this plan does not claim
`make check` ran.

## Learning checkpoint

The developer must explain why basename eligibility is safer than `.json`/`.toml` suffix
support; how `tomllib` parses data without importing Python; why package scripts remain inert
strings; why tsconfig paths/extends are unresolved; why metadata evidence has less source
precision than AST/Markdown tokens; how facts flow through `RepositoryIndexResult` into
canonical JSON; and where deterministic mapping/array/fact ordering is enforced.

## Outcome and follow-ups

M1.4B now provides deterministic direct project metadata for exactly three manifest
basenames while leaving dependency/configuration resolution explicit and deferred.
Milestone 1 remains active. The next slice is Milestone 1.5 — Fixture gold, byte
determinism, acceptance validation, and Milestone 1 closeout.
