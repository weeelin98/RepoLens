# Milestone 1.3A — In-memory Repository Graph Assembly

## Purpose and user-visible outcome

Given a repository root and `RuntimeConfig`, RepoLens will connect the completed scanner
and Python extractor into one deterministic, in-memory result. The result contains a
validated structural/symbol graph, unresolved import facts, scanner diagnostics, and
extractor/source-loading diagnostics. No command writes files in this slice.

## Scope and non-goals

M1.3A adds repository, directory, and file nodes; structural `contains` edges; safe source
loading for accepted Python files; registry-based extraction; and immutable result
assembly. It preserves Python module/definition nodes, extractor containment, unresolved
imports, and diagnostics.

This slice does not implement `repolens index`, output-directory creation, `graph.json`,
Markdown extraction, import resolution or import edges, calls, inheritance, JavaScript or
TypeScript, incremental indexing, caching, traversal, reports, MCP, or runtime execution.
The scanner and Python extractor remain separate focused layers.

## Current state

- `scan_repository()` returns only accepted `SourceFile` metadata, scanner diagnostics,
  and accepted byte totals. Its public paths are normalized repository-relative POSIX
  paths and its limits/ignore/symlink decisions are already complete.
- `PythonExtractor.extract(path, source)` returns module/definition nodes, syntax-direct
  containment, unresolved import facts, and deterministic string diagnostics.
- `ExtractorRegistry` maps normalized suffixes to extractor instances but deliberately has
  no global default registry.
- `GraphSnapshot` already sorts nodes by ID and edges by `GraphEdge.sort_key()`, rejects
  duplicate node IDs and equivalent edges, and rejects missing endpoints.
- No existing result can carry a graph plus unresolved imports plus both diagnostic
  channels. `ExtractionResult` is per-file and `ScanResult` is discovery-only.
- Baseline on branch `Python-definition-extractor`: 84 tests passed, 3 real-symlink scanner
  integrations skipped because Windows returned privilege error 1314, total coverage was
  92%, and Mypy reported no issues in 26 source files.

## Acceptance criteria

1. `index_repository(root, config, registry=None)` returns one immutable
   `RepositoryIndexResult` and performs no writes.
2. An empty valid repository yields exactly one repository node whose identity contains no
   absolute machine path.
3. Every accepted file has one file node; only the parent directories needed by accepted
   files have directory nodes. The repository node represents the root, so no duplicate
   root-directory node exists.
4. Structural nodes and edges use repository-relative POSIX paths, existing stable IDs,
   `CONTAINS`, `SYNTAX_DIRECT`, and confidence 1.0.
5. The default registry contains only `PythonExtractor`. A caller-supplied registry is used
   as supplied. No extractor is not an error.
6. Accepted Python is loaded with `tokenize.open()` so encoding cookies are honored;
   Markdown and other unsupported registry paths are not read.
7. Source loading resolves the lexical scanner path beneath the resolved root, rechecks
   containment, catches only expected permission/filesystem/decode/encoding failures,
   preserves the file node, emits a stable relative-path diagnostic, and continues.
8. Successful extraction merges all extractor nodes, edges, imports, and diagnostics and
   adds one file-to-each-module structural edge without mutating extractor results.
9. Invalid Python preserves its file node and extractor diagnostic without fabricating a
   module. Imports remain unresolved facts and never become graph edges.
10. The result explicitly sorts imports and both diagnostic channels; `GraphSnapshot`
    enforces graph ordering, unique node IDs, unique equivalent edges, and endpoints.
11. Repeated indexing of unchanged contents compares equal, no absolute root leaks through
    model serialization, and parsed source is never imported or executed.
12. Focused tests cover all twenty requested graph, source-loading, safety, limits,
    duplicate, and determinism behaviors; the existing suites remain green.

## Milestone phases

### Phase 1 — Plan and contract boundary

Record the existing-model analysis, structural naming/ID policy, contains rules, source
loading policy, registry default, result ordering, and exact file set before production
edits.

### Phase 2 — Minimal in-memory indexer

Add `src/repolens/indexer.py` with `RepositoryIndexResult` and `index_repository()`. Build
structural nodes from accepted scanner records, load only registry-supported files, merge
extractor output, and construct `GraphSnapshot` as the validation boundary.

### Phase 3 — Focused executable expectations

Add `tests/test_indexer.py` with small temporary repositories and manually authored or
semantic expectations for the requested twenty cases. Monkeypatch the source open at the
indexer boundary for platform-independent read-failure tests.

### Phase 4 — Documentation and validation

Update `CODEX.md`, `README.md`, interview questions, and this plan. Run the requested Ruff,
Mypy, focused pytest, full pytest, harness, doctor, and Git checks sequentially; record the
exact results and inspect the diff for scope growth.

## Invariants and contracts

### Public API and result

The new public module is `repolens.indexer`:

```text
class RepositoryIndexResult(BaseModel):
    graph: GraphSnapshot
    imports: tuple[UnresolvedImportFact, ...]
    scanner_diagnostics: tuple[ScanDiagnostic, ...]
    extractor_diagnostics: tuple[str, ...]

def index_repository(
    repository_root: Path,
    config: RuntimeConfig,
    registry: ExtractorRegistry | None = None,
) -> RepositoryIndexResult
```

The result is frozen and forbids extra fields. It sorts imports with
`UnresolvedImportFact.sort_key()`, scanner diagnostics by path/code/message, and extractor
diagnostics lexically. `GraphSnapshot` remains the sole graph normalization/integrity
boundary rather than duplicating those rules in a second graph model.

### Structural naming and stable IDs

- The repository node uses label and qualified-name sentinel `<repository>`, source path
  `.`, and `stable_node_id(REPOSITORY, source_path=".", qualified_name="<repository>")`.
- A directory node uses its final path component as label and its full relative POSIX path
  as `source_path`; its ID uses kind plus that source path. It has no symbol qualified name.
- A file node uses its basename as label and full relative POSIX path as `source_path`; its
  ID uses kind plus that source path. It records normalized suffix and observed byte size
  in metadata, and `python`/`markdown` language for the two scanner defaults.
- Structural nodes have no source spans. Extractor-created source-backed nodes retain their
  existing spans and qualified names. Absolute roots are never ID or model inputs.

### Directory hierarchy and contains edges

Derive the complete parent-directory set only from accepted `SourceFile.relative_path`
values. Sort directories by depth and path while constructing them. The repository node is
the root parent; do not add a second root-directory node.

Add repository-to-top-level-directory, repository-to-root-file,
directory-to-direct-directory, and directory-to-direct-file edges. After successful
extraction, add file-to-module for every returned module node. Every structural edge uses
`EdgeKind.CONTAINS`, `EvidenceKind.SYNTAX_DIRECT`, confidence 1.0, and the child's relative
source path; file-to-module also retains the module span. Extractor edges are copied
unchanged. `GraphSnapshot` rejects any duplicate equivalent edge or missing endpoint.

### Source loading and registry selection

Create a fresh default registry per call and register one `PythonExtractor`. If a registry
is supplied, use it unchanged. For each accepted source file, call `registry.for_path()`;
when it returns `None`, keep only the file structure and do not read content.

For a supported path, join the scanner's validated POSIX components beneath the resolved
root, resolve the candidate strictly, and verify the resolved target remains beneath the
root before reading. Use `tokenize.open()` and `read()` so Python encoding cookies work.
Convert `PermissionError`, other `OSError`, `UnicodeDecodeError`, and Python encoding
detection `SyntaxError`/`LookupError` into fixed `source_load_error:<path>:<reason>` strings.
A post-scan containment failure receives `outside_repository`. Preserve the structural
file node, add no extractor output for that file, and continue. Do not catch `Exception`.

### Extraction merge and deterministic ordering

Append extractor nodes, edges, imports, and diagnostics into new assembly lists; never
mutate an `ExtractionResult`. Add the file-to-module edge only for returned `MODULE` nodes.
Do not invent a module when extraction is invalid or loading failed, and do not resolve
imports.

`GraphSnapshot` sorts nodes by ID and edges by their semantic key. The top-level result
sorts all other collections explicitly. Source-file iteration uses scanner order, directory
construction uses `(depth, path)`, and no public ordering relies on dict/set iteration.

## Test and harness plan

`tests/test_indexer.py` will cover: empty repository; root Python structure; nested
directories; Markdown-only structure; definition merge; extractor-edge preservation;
file-to-module; unresolved imports; root ignore; scanner limits; POSIX paths; absolute-path
non-leakage; encoding cookies; invalid Python; read failure; failure isolation; endpoint
integrity; duplicate-node rejection; repeat equality; and non-execution/non-import.

Expected paths, kinds, stable IDs, and relationship endpoints are literal or manually
constructed from documented inputs. Tests must not serialize production output to create
their own oracle. Existing harness gold is unchanged because M1.3A neither resolves its
future edges nor writes graph artifacts; `harness-smoke` remains a regression check.

## Progress

- [x] 2026-07-16: Verified the requested branch and clean worktree; baseline pytest and
  Mypy passed with the documented Windows symlink skips.
- [x] 2026-07-16: Read the governing docs, prior plans, scanner/extractor/graph contracts,
  serialization, and all requested tests.
- [x] 2026-07-16: Defined acceptance criteria and the eleven requested design decisions
  before production edits.
- [x] 2026-07-16: Implemented the minimal in-memory indexer and result model.
- [x] 2026-07-16: Added 21 focused M1.3A tests; all passed and indexer focused coverage
  was 92%.
- [x] 2026-07-16: Updated project and learning documentation for the M1.3A boundary and
  M1.3B handoff.
- [x] 2026-07-16: Ran and recorded the complete requested validation set; final diff and
  status inspection confirmed exactly the six planned paths.

## Decisions

- **2026-07-16 — Reuse `GraphSnapshot` inside one orchestration result.** Alternatives were
  widening `GraphSnapshot` with non-graph facts or placing graph lists directly on a new
  model. Keeping the validated graph intact avoids contract duplication while the wrapper
  carries imports and diagnostics.
- **2026-07-16 — Repository node is the only root concept.** A separate root directory
  would duplicate identity and add a meaningless mandatory edge. Nested directories remain
  explicit.
- **2026-07-16 — Structural identity is semantic and relative.** Repository uses an
  explicit sentinel; directories/files use kind plus relative path. Machine roots, labels,
  timestamps, and traversal order do not participate.
- **2026-07-16 — Source failures use extractor diagnostic strings.** The existing scanner
  typed diagnostics describe discovery/metadata states, while `ExtractionResult` already
  uses strings for parse diagnostics. Fixed path-bearing source-load strings are the
  smallest compatible orchestration behavior and avoid redesigning scanner diagnostics.
- **2026-07-16 — Supplied registries are authoritative.** A default registry registers
  Python, while an injected registry is not silently mutated. This makes selection tests
  honest and allows later callers to control supported extractors.

## Discoveries and surprises

- **2026-07-16:** The graph contract already performs every requested graph integrity check,
  so M1.3A needs a wrapper result rather than new node/edge containers.
- **2026-07-16:** Scanner paths are safe lexical identities, but content can change after
  scanning. The loader therefore repeats strict resolution/containment immediately before
  open and reports a stable failure rather than trusting stale filesystem state.
- **2026-07-16:** Prior work found concurrent pytest processes contend for `.coverage` on
  Windows. All focused and full pytest validation in this plan will run sequentially.

## Validation transcript

Run sequentially from `C:\RepoLens` without network access:

```text
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest tests/test_indexer.py -v
uv run pytest tests/test_extractors.py -v
uv run pytest tests/test_scanner.py -v
uv run pytest
uv run repolens harness-smoke
uv run repolens doctor
git diff --check
git status --short
```

Baseline before production edits: `uv run pytest` passed 84 tests and skipped 3 existing
real-symlink scanner integrations because Windows returned privilege error 1314; total
coverage was 92%. `uv run mypy src tests` reported no issues in 26 source files. Final
M1.3A validation results:

- `uv run ruff format .` — exit 0; 42 files left unchanged.
- `uv run ruff format --check .` — exit 0; 42 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 28 source files.
- `uv run pytest tests/test_indexer.py -v` — exit 0; 21 passed; indexer coverage was 92%.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 34 passed; import-contract coverage
  was 100% and Python extractor coverage was 96%.
- `uv run pytest tests/test_scanner.py -v` — exit 0; 30 passed and 3 real-symlink tests
  skipped because Windows returned privilege error 1314; scanner coverage was 97%.
- `uv run pytest` — exit 0; 105 passed and the same 3 scanner integrations skipped; total
  coverage and indexer coverage were both 92%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.
- `git diff --check` — exit 0; only LF-to-CRLF working-copy warnings were printed for the
  three modified Markdown documentation files.
- `git status --short` — exactly the six planned M1.3A paths were modified or untracked.

GNU Make is unavailable and this plan does not claim `make check` ran. The three skips are
unchanged M1.1 Windows symlink-privilege limitations; every M1.3A test ran and passed.

## Learning checkpoint

The developer must explain in their own words how an accepted lexical `SourceFile` becomes
a structural file node; how parent directories and structural edges are derived; why source
loading happens only after registry selection; how `tokenize.open()` and containment
rechecks protect correctness; how extractor facts merge without becoming resolved import
edges; and where deterministic ordering and graph integrity are enforced.

Prompt: “Trace `services/api/user.py` from scanner acceptance through directory/file nodes,
safe source loading, registry selection, Python module/definition extraction, file-to-module
and internal contains edges, unresolved imports, diagnostics, and final result sorting. What
is direct evidence, and what remains deliberately unresolved?”

## Outcome and follow-ups

M1.3A now delivers an in-memory deterministic repository index connecting accepted scanner
metadata to portable structure, safe Python loading, direct extracted graph facts,
unresolved imports, and separate diagnostic channels. It writes no artifacts and resolves
no relationships. The next expected slice is Milestone 1.3B — CLI index command and
deterministic `graph.json` output. Milestone 1 remains active.
