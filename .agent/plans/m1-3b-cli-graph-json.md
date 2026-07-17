# Milestone 1.3B — CLI Index Command and Deterministic graph.json

## Purpose and user-visible outcome

`repolens index PATH` will run the existing in-memory repository indexer, create the
configured output directory, and atomically write a complete deterministic `graph.json`.
The command reports compact counts, succeeds when only file-level diagnostics occur, and
returns a non-zero exit code for invalid invocation or fatal indexing/output failures.

## Scope and non-goals

This slice replaces the `index` placeholder, adds canonical serialization for
`RepositoryIndexResult`, atomically writes `graph.json`, prevents the configured output
directory from entering scanner results when it is inside the repository, adds focused
CLI/serialization/scanner tests, and updates project documentation.

It does not generate `CODEBASE_OVERVIEW.md`, resolve imports, add import/call/inheritance
edges, extract Markdown semantics, add JavaScript/TypeScript, introduce CLI configuration
options, clean output directories, cache or incrementally index, start MCP, or change the
process working directory.

## Current state

- Typer exposes one `app`, an eager version callback, implemented `doctor` and
  `harness-smoke` commands, and explicit placeholders for later commands.
- `index(path: Path)` accepts an unvalidated path and always calls `_unfinished("index", 1)`,
  which prints an error and exits 2.
- `index_repository()` already returns a deterministic frozen `RepositoryIndexResult`
  containing a normalized `GraphSnapshot`, unresolved imports, scanner diagnostics, and
  extractor/source-loading diagnostics.
- `canonical_graph_json()` and `parse_graph_json()` handle only `GraphSnapshot`. They use
  Pydantic JSON-mode dumping, recursively ordered dictionaries, sorted JSON keys, compact
  separators, UTF-8-safe text, finite numbers, and a final newline.
- `RuntimeConfig.output_directory` is an unrestricted `Path` defaulting to
  `repolens-out`. Therefore relative and absolute configured paths are supported by the
  current model, but their anchoring is not yet implemented.
- The scanner prunes fixed source-control/environment directories and root ignore matches,
  but does not prune the configured output directory. Although generated `graph.json` has
  an unsupported suffix, other preserved files inside the output directory could otherwise
  enter scans and resource accounting.
- Baseline on branch `Python-definition-extractor`: 105 tests passed, 3 real-symlink
  scanner integrations skipped because Windows returned privilege error 1314, total
  coverage was 92%, and Mypy reported no issues in 28 source files.

## Acceptance criteria

1. `repolens index PATH` accepts relative, absolute, and current-directory repository paths
   without changing the process working directory.
2. Typer rejects a missing path or regular-file argument with exit code 2 before indexing.
3. The command uses `RuntimeConfig()` defaults and writes default output to
   `<resolved-repository>/repolens-out/graph.json`.
4. A relative configured output path is anchored beneath the resolved repository root; an
   absolute configured path is used as-is. Missing parents are created without deleting or
   cleaning existing output content.
5. When the configured output directory is a strict descendant of the repository root,
   scanner traversal prunes that exact directory before descent and resource accounting.
   An absolute output outside the root has no scanner effect; output equal to the root does
   not prune the entire repository.
6. `graph.json` serializes the complete `RepositoryIndexResult`: nested versioned graph,
   nodes, edges, unresolved imports, scanner diagnostics, and extractor diagnostics.
7. Canonical encoding uses normalized model collections, recursively stable dictionaries,
   sorted keys, compact separators, `ensure_ascii=False`, finite numbers, and one final
   newline. Repeated unchanged runs produce byte-identical output.
8. Writing is atomic at the file boundary: serialize fully, write/flush/fsync a deterministic
   temporary sibling, close it, then `Path.replace()` the final file. Expected failure
   attempts temporary cleanup and never reports success.
9. File-level scanner/extractor diagnostics remain non-fatal: they are serialized, included
   in a warning count, and the command exits 0. Root-level scanner diagnostics, output
   directory creation failure, serialization/write failure, and unexpected top-level
   indexing failure exit non-zero and do not claim success.
10. Success output reports the caller's display path, accepted file-node count, graph node
    and edge counts, unresolved import count, combined diagnostic count, and usable output
    path without dumping JSON or source.
11. Generated JSON contains no source contents, absolute repository identity, timestamp,
    UUID, or machine metadata and validates back into `RepositoryIndexResult`.
12. All twenty requested CLI/output behaviors and existing command regressions pass; the
    full offline validation and manual two-run smoke check pass.

## Milestone phases

### Phase 1 — Contract and plan

Record CLI structure, placeholder, serialization/result boundary, output resolution,
diagnostic/exit policy, determinism, atomic writing, and exact files before production
edits.

### Phase 2 — Complete result serialization and output exclusion

Extend `src/repolens/graph/serialization.py` with canonical parse/serialize helpers for
`RepositoryIndexResult`, reusing the existing encoder. Make the scanner prune only the
configured output directory when it is a strict descendant of the resolved root.

### Phase 3 — CLI orchestration and atomic write

Replace the placeholder in `src/repolens/cli.py` with a Typer-validated repository
argument, default `RuntimeConfig`, M1.3A indexing, fatal-root checking, output resolution,
directory creation, atomic write, deterministic success counts, and concise fatal errors.

### Phase 4 — Focused tests

Extend CLI tests for successful content, determinism, diagnostics, output pruning, fatal
paths, mkdir/write failures, temporary cleanup, and non-execution. Extend model tests for
complete-result canonical round-trip and scanner tests for output-directory pruning before
accounting.

### Phase 5 — Documentation, validation, and smoke

Update `CODEX.md`, `README.md`, interview questions, and this plan. Run every requested
command sequentially, perform a manual two-run CLI smoke against a temporary repository,
inspect JSON/counts/path leakage, and audit the final diff.

## Invariants and contracts

### Typer CLI and exit codes

The command signature uses `Annotated[Path, typer.Argument(exists=True,
file_okay=False, dir_okay=True, readable=True, resolve_path=False)]`. Typer handles
invocation errors with exit 2. Runtime fatal failures print one concise `Error:` message to
stderr and exit 1. Successful indexes, including those with non-fatal diagnostics, exit 0.
No speculative CLI option is added.

### Complete graph.json model

The serialized root object is exactly `RepositoryIndexResult`, not a parallel dictionary:

```text
{
  "extractor_diagnostics": [...],
  "graph": {
    "edges": [...],
    "metadata": {...},
    "nodes": [...],
    "schema_version": 1
  },
  "imports": [...],
  "scanner_diagnostics": [...]
}
```

Optional `None` fields are omitted consistently with the existing graph serializer. The
nested graph owns the existing schema version. `parse_index_json()` validates the full file
back into `RepositoryIndexResult`, including graph endpoints and duplicate invariants.

### Output-directory resolution and exclusion

Resolve the repository root without changing `cwd`. If `config.output_directory` is
absolute, use it directly. Otherwise join it beneath the resolved root. The final path is
`output_directory / "graph.json"`.

Before walking, the scanner resolves the same configured output path without requiring it
to exist. If it is a strict descendant of the resolved repository root, compare its exact
repository-relative path while filtering top-down `dirnames` and prune it before descent.
This is one configured-output boundary, not a general generated-file framework. Existing
files in that directory are preserved; they are simply excluded from scanning.

### Fatal and non-fatal diagnostics

Typer handles nonexistent/non-directory arguments. After indexing, any scanner diagnostic
whose `path is None` is a fatal root failure; the CLI emits its stable message and writes
nothing. Per-file scanner diagnostics and every extractor/source-loading diagnostic are
non-fatal and remain in JSON. The displayed diagnostic count is the sum of both channels.

### Canonical JSON

Both graph-only and complete-result serializers call one internal canonical model encoder.
Pydantic models normalize node, edge, import, and diagnostic collections before dumping.
The encoder recursively orders mapping keys and calls `json.dumps()` with
`ensure_ascii=False`, `allow_nan=False`, `sort_keys=True`, and compact separators, then
adds exactly one newline. No runtime path or timestamp is added.

### Atomic output

Use the sibling `<output>/.graph.json.tmp`. Serialize before opening it. Write UTF-8 with
LF newlines, flush, call `os.fsync()`, close through the context manager, then atomically
replace `graph.json`. If write, flush, sync, or replace raises `OSError`, attempt
`unlink(missing_ok=True)` on the temporary path while preserving the original failure.
Never delete an existing final graph before replacement.

### Success output

Print one compact line containing `Indexed <display-path>`, file/node/edge/import/diagnostic
counts, and `graph.json: <display-output-path>`. The display output uses the caller's path
plus a relative configured output when possible; absolute configured output remains a
usable absolute path only in terminal output and never enters JSON.

## Test and harness plan

`tests/test_cli.py` uses `CliRunner` and temporary repositories to cover empty success,
default directory/file creation, Python definitions/imports, diagnostics, Markdown
structure, ignore behavior, output pruning on repeat, byte equality, absolute-path
non-leakage, useful counts, missing/file arguments, mkdir failure, write/replace failure,
temporary cleanup, non-fatal syntax, non-execution, and unchanged doctor/harness behavior.

`tests/test_models.py` manually constructs a `RepositoryIndexResult`, verifies canonical
round-trip, final newline, stable key/collection ordering, and nested graph validation.
`tests/test_scanner.py` verifies configured output pruning occurs before `stat()` and limit
accounting while leaving the output directory and its unrelated files untouched.

Harness gold remains unchanged because it describes future resolved graph expectations;
M1.3B only persists the current result. `harness-smoke` remains a regression check.

## Progress

- [x] 2026-07-16: Verified the requested branch and clean worktree; baseline pytest and
  Mypy passed with the documented Windows symlink skips.
- [x] 2026-07-16: Read the governing docs, M1.3A plan, CLI, config, indexer, graph,
  serializer, scanner, tests, and README.
- [x] 2026-07-16: Defined acceptance criteria and the ten requested design decisions before
  production edits.
- [x] 2026-07-16: Implemented result serialization, configured-output pruning, CLI
  orchestration, and atomic writing.
- [x] 2026-07-16: Added focused CLI, serialization, and scanner tests; 16 CLI tests and 7
  model tests passed, while 31 scanner tests passed with 3 Windows symlink skips.
- [x] 2026-07-16: Updated project documentation, the working CLI example, and learning
  questions with the Markdown-extraction handoff.
- [x] 2026-07-16: Ran and recorded validation and the manual two-run smoke; final diff and
  status inspection confirmed exactly the ten planned paths.

## Decisions

- **2026-07-16 — Serialize `RepositoryIndexResult` as the root.** Writing only
  `GraphSnapshot` would drop unresolved imports and diagnostics; a handwritten payload
  would duplicate Pydantic contracts.
- **2026-07-16 — Reuse one canonical encoder.** Graph-only compatibility remains while the
  complete-result serializer gets identical JSON rules and final-newline behavior.
- **2026-07-16 — Prune the configured output in the scanner.** Post-scan filtering could
  let output files consume limits and exclude real source. Exact top-down pruning is the
  smallest correct compatibility change.
- **2026-07-16 — Absolute configured output is supported.** `RuntimeConfig` accepts any
  `Path`; relative paths anchor at the repository and absolute paths retain their meaning.
- **2026-07-16 — One deterministic sibling temporary file.** Concurrency is out of scope;
  a fixed sibling makes cleanup and failure tests transparent while `replace()` protects
  an existing final file from partial writes.

## Discoveries and surprises

- **2026-07-16:** Generated `graph.json` itself is already ignored by suffix, but the output
  directory is not pruned. Preserved `.py`/`.md` files there could enter scans and consume
  limits, so relying on suffix filtering is insufficient.
- **2026-07-16:** The authoritative Milestone 1 contract still requires deterministic
  Markdown hierarchy/link/code-reference extraction. Therefore M1.3B cannot mark all of
  Milestone 1 complete, and overview generation is not yet the honest next slice.
- **2026-07-16:** Prior validation found concurrent pytest processes contend for `.coverage`
  on Windows. All pytest commands will run sequentially.
- **2026-07-16:** The first smoke-inspection script used the newer static
  `SHA256.HashData()` API unavailable in this Windows PowerShell runtime. Both CLI runs and
  cleanup completed; the inspection was rerun successfully using direct Base64 byte-array
  comparison, with no production change required.

## Validation transcript

Run sequentially from `C:\RepoLens` without network access:

```text
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest tests/test_cli.py -v
uv run pytest tests/test_indexer.py -v
uv run pytest tests/test_extractors.py -v
uv run pytest tests/test_scanner.py -v
uv run pytest
uv run repolens harness-smoke
uv run repolens doctor
git diff --check
git status --short
```

Baseline before production edits: `uv run pytest` passed 105 tests and skipped 3 existing
real-symlink scanner integrations because Windows returned privilege error 1314; total
coverage was 92%. `uv run mypy src tests` reported no issues in 28 source files. Final
M1.3B results:

- `uv run ruff format .` — exit 0; final run reformatted 1 file and left 41 unchanged.
- `uv run ruff format --check .` — exit 0; 42 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 28 source files.
- `uv run pytest tests/test_cli.py -v` — exit 0; 16 passed; CLI coverage was 84%.
- `uv run pytest tests/test_indexer.py -v` — exit 0; 21 passed; indexer coverage was 92%.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 34 passed; Python extractor
  coverage was 96%.
- `uv run pytest tests/test_scanner.py -v` — exit 0; 31 passed and 3 Windows real-symlink
  tests skipped with privilege error 1314; scanner coverage was 96%.
- `uv run pytest` — exit 0; 119 passed and the same 3 scanner integrations skipped; total
  coverage was 92%, serialization coverage was 100%, CLI coverage was 84%, and indexer
  coverage was 92%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.
- `git diff --check` — exit 0; only LF-to-CRLF working-copy warnings were printed for six
  modified tracked files.
- `git status --short` — exactly the ten planned M1.3B paths were modified or untracked.

Manual smoke: two `uv run repolens index <temporary-path>` runs each reported 2 files, 5
nodes, 4 edges, 1 unresolved import, and 0 warnings. The second `graph.json` parsed with no
diagnostics; bytes matched the first run, the temporary absolute repository path was absent,
and the final newline was present. Verified cleanup removed the temporary repository.

GNU Make is unavailable and this plan does not claim `make check` ran. The three skips are
unchanged M1.1 Windows symlink-privilege limitations; every M1.3B test ran and passed.

## Learning checkpoint

The developer must explain in their own words how Typer validates and passes a repository
path; how `RuntimeConfig` resolves output and scanner exclusion; how the complete in-memory
result becomes canonical JSON; why model sorting precedes encoding; how sibling replacement
prevents partial output; why file-level diagnostics still succeed; and why repeated indexing
cannot consume generated output.

Prompt: “Trace `repolens index sample` from Typer argument validation through scanning,
configured-output pruning, extraction, complete-result serialization, temporary-file write,
atomic replacement, warning counts, and exit status. Which failures prevent any success
claim, and which remain recorded non-fatal facts?”

## Outcome and follow-ups

M1.3B now delivers a working `repolens index PATH`, complete canonical `graph.json`, atomic
replacement, explicit fatal/non-fatal behavior, and configured-output pruning. The
authoritative Milestone 1 contract still requires Markdown hierarchy/link/code-reference
extraction, so Milestone 1 remains active. The next slice is Milestone 1.4A — Basic
deterministic Markdown extraction rather than `CODEBASE_OVERVIEW.md` generation.
