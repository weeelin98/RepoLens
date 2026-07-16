# Milestone 1.1 — Repository Scanner

This ExecPlan is the source of truth for the repository-discovery slice of Milestone 1. It
is self-contained and must be updated as implementation evidence changes. The central
traversal and resource-limit logic is reserved for the developer.

## Purpose and user-visible outcome

Given a local repository directory and `RuntimeConfig`, RepoLens returns a deterministic
`ScanResult` containing metadata for eligible Python and Markdown files plus explicit,
stable diagnostics for files it could not include. This slice makes later extraction
possible without parsing files, creating graph objects, or executing repository code.

The finished slice is a library capability. `repolens index` remains an explicit
Milestone 1 placeholder until a later slice connects scanning, extraction, and graph
creation.

## Scope and non-goals

In scope are repository-root validation, recursive discovery, `.py` and `.md` suffixes,
default ignored-directory pruning, one root `.gitignore`, safe symlink handling, metadata
collection with `stat()`, three resource limits, deterministic ordering, stable diagnostics,
and unit tests.

Explicit non-goals are Python AST extraction, import extraction, Markdown parsing, content
decoding, graph nodes or edges, extractor-registry integration, CLI orchestration, output
files, nested `.gitignore` semantics, JavaScript/TypeScript discovery, MCP behavior, and
Milestone 1.2. The scanner never returns file contents.

## Current state

- `src/repolens/config.py` already defines positive `maximum_file_bytes`,
  `maximum_repository_bytes`, and `maximum_file_count` values.
- `src/repolens/ids.py` provides `normalize_repo_path()` for safe POSIX repository paths.
- `src/repolens/models.py` contains graph contracts; scanner contracts must not use them.
- `src/repolens/extractors/base.py` accepts paths plus decoded source; scanning remains an
  earlier independent stage.
- `src/repolens/cli.py` intentionally fails `index` with a Milestone 1 message.
- The five harness corpora validate schema/reference integrity only; none is a scanner gold
  corpus.
- M1.1C declares `pathspec>=1.1,<2` directly in `pyproject.toml`; `uv.lock` resolves
  pathspec 1.1.1 for root ignore matching.
- Before this slice there was no `src/repolens/scanner.py` or `tests/test_scanner.py`.
- At the start of M1.1A on 2026-07-16, `git branch --show-current` reported
  `Python-definition-extractor`, matching the implementation request. An earlier
  contracts-only session had reported `main`; no branch was created or switched by Codex.

## Acceptance criteria

1. `scan_repository(root, config)` finds nested `.py` and `.md` files without reading or
   decoding them and accepts uppercase variants case-insensitively.
2. Extensionless and unsupported files are absent without diagnostics.
3. `.git`, `.venv`, `venv`, and `__pycache__` are pruned before descent.
4. Root `.gitignore` patterns and ordinary file negation are honored; nested ignore files
   are explicitly out of scope.
5. Every returned path is repository-relative POSIX text with no absolute prefix or `..`.
6. Files and diagnostics have documented stable sort orders; repeated scans compare equal.
7. Oversized files are skipped with `file_too_large`; scanning continues.
8. The first eligible file that would exceed file-count or repository-byte limits is not
   included, receives one limit diagnostic, and ends the scan without silent truncation.
9. Missing, non-directory, and inaccessible roots produce empty results with explicit
   diagnostics rather than expected filesystem exceptions.
10. Directory symlinks are not traversed. In-repository file symlinks are included under
    the link path; file symlinks resolving outside the root are excluded with a diagnostic.
11. Scanning never imports or executes target code and never exposes an absolute path in a
    returned model or deterministic message.
12. The 23 Milestone 0 tests continue to pass normally. Unimplemented M1.1 behavioral tests
    are strict xfails naming Milestone 1.1, not hidden regressions.
13. Formatting, lint, strict Mypy, pytest, harness smoke, doctor, and `git diff --check` pass
    using the commands in the Validation transcript section.
14. No production traversal, ignore matching, or resource-limit behavior is implemented in
    the contracts-only run that created this plan.

## Milestone phases

### Phase 0 — Contracts and executable expectations (complete)

Create `src/repolens/scanner.py` with frozen metadata/result contracts and an explicit
developer-owned placeholder. Create `tests/test_scanner.py` with hand-written expected
paths and diagnostics under strict M1.1 xfails. Do not implement traversal. Validate all
existing behavior and record exact results here and in `CODEX.md`.

### Phase 1 — Root, suffix, and deterministic walk (M1.1A, complete)

Implement the public function in `src/repolens/scanner.py`. Validate and resolve the root
internally, walk top-down with `os.walk(..., followlinks=False)`, sort names, prune the four
default directories, accept case-folded `.py`/`.md`, and return relative POSIX metadata.
Make only the discovery/path/default-ignore tests pass; leave later xfails intact. This
phase was implemented as the explicitly authorized M1.1A slice on 2026-07-16.

### Phase 2 — Root `.gitignore` (M1.1C, complete)

Declare `pathspec>=1.1,<2` as a direct runtime dependency in `pyproject.toml`, update
`uv.lock`, compile only the root `.gitignore` with pathspec's current `gitignore` pattern
factory and Git wildmatch semantics, and apply it to repository-relative POSIX paths.
Preserve negation and prune ignored directories when Git semantics permit pruning. This
phase was implemented as the explicitly authorized M1.1C slice on 2026-07-16.

### Phase 3 — Symlinks and filesystem failures (M1.1D, complete)

Reject symlinked directories from `dirnames`, resolve file symlinks for containment, and
collect size with `Path.stat()` before inclusion. Convert expected permission/stat failures
to stable diagnostics without embedding OS-specific exception text. Make symlink and
filesystem-failure tests pass, with safe platform skips where link creation is unavailable.
M1.1D implemented this phase on 2026-07-16; Linux GitHub Actions later verified the real
symlink integrations that Windows could not create.

### Phase 4 — Resource limits (M1.1B, complete)

Apply per-file, accepted-file-count, and accepted-byte limits in deterministic encounter
order. Continue after per-file oversize; stop with a single diagnostic at the first
count/aggregate breach. Sort public collections before returning. M1.1B implemented this
phase on 2026-07-16 without changing the existing root ignore behavior.

### Phase 5 — Integration review (complete)

Remove xfails only from behavior that is actually implemented. Run every validation
command, inspect `git diff --stat`, `git diff --check`, and `git status --short`, update this
plan and `CODEX.md`, and ask the developer to answer the learning checkpoint in their own
words. Do not wire `index` or start extraction.

## Invariants and contracts

### Proposed public API

The finalized API is:

```python
DEFAULT_SUPPORTED_SUFFIXES = frozenset({".md", ".py"})

class SourceFile(BaseModel):
    relative_path: str
    suffix: str
    size_bytes: int

class ScanDiagnosticCode(StrEnum):
    ...

class ScanDiagnostic(BaseModel):
    path: str | None
    code: ScanDiagnosticCode
    message: str

class ScanResult(BaseModel):
    files: tuple[SourceFile, ...]
    diagnostics: tuple[ScanDiagnostic, ...]
    total_bytes: int

def scan_repository(
    repository_root: Path,
    config: RuntimeConfig,
    *,
    supported_suffixes: frozenset[str] = DEFAULT_SUPPORTED_SUFFIXES,
) -> ScanResult:
    ...
```

All models are frozen and reject extra fields. Changes from the suggested contract are:

- `absolute_path` is removed from `SourceFile`. The scanner can reconstruct a working path
  internally from the resolved root and relative path; public metadata stays portable and
  serialization-safe.
- `ScanDiagnostic.code` is a `StrEnum`, not arbitrary text, so callers cannot accidentally
  invent unstable machine codes.
- Defaults are named constants, making suffix and ignored-directory policy directly
  testable without introducing a configuration abstraction for future languages.
- Invalid roots return an empty `ScanResult` with a diagnostic. There is no second custom
  exception channel for ordinary filesystem states.
- Suffixes are normalized with `casefold()` and stored with the leading dot. Paths reuse
  `normalize_repo_path()`.

### Internal data models

No additional production model is required. During implementation, local variables may
hold the resolved root, compiled root ignore specification, accepted files, diagnostics,
accepted byte count, and a stop flag. Do not create graph, extractor, filesystem-framework,
or future-language abstractions.

### Supported suffix rules

The default allowlist is exactly `.py` and `.md`. Compare `Path.suffix.casefold()` against a
case-folded caller-provided allowlist. Return the normalized lowercase suffix. `.PY` and
`.MD` are accepted; extensionless files and every other suffix are silently excluded. A
multi-suffix filename is classified by its final suffix. `.gitignore` is control input, not
a returned source file.

### Default ignored-directory rules

Directory base names `.git`, `.venv`, `venv`, and `__pycache__` are unconditionally ignored
at every depth. In top-down `os.walk`, remove them from mutable `dirnames` before descent.
They cannot be re-enabled by `.gitignore` negation because they are security/resource
defaults rather than repository-authored patterns.

### `.gitignore`, nested files, and negation

M1.1 reads at most `<resolved-root>/.gitignore` as UTF-8 with replacement for malformed
bytes; this is the sole scanner control file that may be decoded. No `.gitignore` means an
empty specification and otherwise identical behavior. The control file is never returned.

Use the `pathspec` library's Git-compatible matching instead of hand-rolling wildmatch.
Paths passed to it are relative POSIX paths; directory probes include a trailing `/`.
Ordinary last-match-wins negation such as `*.py` followed by `!important.py` is supported.
Git's parent rule remains: a file inside an excluded directory cannot be re-included unless
the directory path is also re-included, so an actually excluded directory may be pruned.

Nested `.gitignore` files are not loaded and have no matching effect in M1.1. Full stacked
per-directory Git semantics require separate acceptance tests and are deferred rather than
partially emulated. Root `.gitignore` symlinks are not read, avoiding a control-file read
outside the repository boundary.

### Repository-root validation

Interpret a relative input relative to the process working directory, then keep one
resolved absolute root internally. If the path does not exist, return only
`repository_not_found`; if it is not a directory, return only
`repository_not_directory`. If root inspection or traversal is denied, return only
`permission_denied`. The public diagnostic path is `None` for root failures. Expected
filesystem failures do not escape; programmer errors and Pydantic-invalid configuration
may raise normally.

### Relative POSIX path normalization

For an encountered path, derive its lexical path beneath the walk root with
`path.relative_to(resolved_root).as_posix()`, then validate it through
`normalize_repo_path()`. Public paths are the lexical repository location, including the
link name for an allowed file symlink—not the resolved target. No model or message contains
the absolute root.

### Symlink behavior

Use `followlinks=False` and also remove symlinked directories from `dirnames`; do not rely
on one platform-specific `os.walk` detail. For a file symlink, resolve its target and test
containment with `resolved_target.relative_to(resolved_root)`. Exclude escapes with
`outside_repository_symlink`. Include a symlink whose target remains in the repository,
using the symlink's relative path and the target size returned by normal `stat()`. Broken
links become `stat_failed`. Tests skip only when the platform cannot create the needed link.

### File metadata and encoding behavior

Call `Path.stat()` and use `st_size`; zero-byte files are valid. Do not open, read, decode,
import, execute, hash, or inspect modification times for source files. Encoding policy is
owned by later parser/extractor slices. Diagnostic messages are fixed RepoLens text, not
raw exception strings, to avoid nondeterminism and machine paths.

### Per-file byte-limit behavior

After successful stat, if `st_size > maximum_file_bytes`, omit the file, append
`file_too_large` at its relative path, and continue. Equality is allowed. The scanner never
reads an oversized source file merely to measure it.

### Repository byte-limit behavior

`total_bytes` is the sum of returned files only. Before including an otherwise eligible
file, if `total_bytes + st_size > maximum_repository_bytes`, omit it, append exactly one
`repository_size_limit_reached` diagnostic naming that first excluded path, and stop the
walk. Equality is allowed. Already accepted files form a valid partial result.

### File-count-limit behavior

The count is the number of returned files, not visited, unsupported, ignored, failed, or
oversized entries. Before including an otherwise eligible file, if the accepted count is
already `maximum_file_count`, omit it, append exactly one `file_count_limit_reached`
diagnostic naming that first excluded path, and stop. Do not silently truncate.

### Deterministic traversal and result ordering

Walk top-down. Sort `dirnames` and `filenames` with Python's ordinary case-sensitive string
order after pruning. Limit decisions therefore use a stable encounter order. Before
building `ScanResult`, sort files by `relative_path` and diagnostics by
`(path or "", code.value, message)`. Do not expose set iteration, filesystem enumeration
order, timestamps, absolute roots, or raw OS errors. Repeated unchanged scans compare equal.

### Diagnostic codes

The complete M1.1 set is:

- `repository_not_found`: input root does not exist.
- `repository_not_directory`: input root exists but is not a directory.
- `file_too_large`: one supported file exceeds its individual limit.
- `file_count_limit_reached`: the first otherwise eligible file exceeds accepted count.
- `repository_size_limit_reached`: the first otherwise eligible file exceeds byte total.
- `outside_repository_symlink`: a file link resolves beyond the root.
- `stat_failed`: metadata lookup failed for a reason other than permission denial.
- `permission_denied`: root traversal or entry metadata was denied.

Do not add a diagnostic for unsupported suffixes, default ignores, `.gitignore` matches,
directory symlinks, or a missing root `.gitignore`.

### Error versus partial-result decisions

Invalid roots yield empty results. Entry-level `stat_failed`, `permission_denied`,
`outside_repository_symlink`, and `file_too_large` omit that entry and continue. File-count
and aggregate-byte breaches return the accepted prefix and stop because continuing would
make truncation policy surprising. Unexpected programming errors are not converted into
diagnostics.

### Security constraints

Never execute/import repository modules, follow directory links, include external file-link
targets, return contents, leak absolute paths, invoke Git, access the network, or write into
the target repository. Scanner work is read-only except for test-created temporary trees.

## Test and harness plan

`tests/test_scanner.py` uses `tmp_path` so each expected tree is readable beside its
assertions. Expected paths and diagnostics are literal, never generated from production
output. The contracts cover:

1. nested `.py` and `.md`, uppercase acceptance, unsupported and extensionless exclusion;
2. repository-relative POSIX paths, lowercase suffix metadata, stable sorting, repeat scan;
3. each of `.git`, `.venv`, `venv`, and `__pycache__` as a pruned directory;
4. root ignore patterns, ignored directory, and `!important.py` negation;
5. missing root ignore behavior, nested ignore non-application, pre-`stat()` file exclusion,
   and pre-descent ignored-directory pruning;
6. oversized-file skip/continue and accepted-byte total;
7. deterministic first-excluded file-count behavior;
8. deterministic first-excluded repository-byte behavior;
9. missing root and regular-file root rejection codes;
10. a Python file with a visible side effect that must never execute;
11. non-traversal of a directory symlink;
12. rejection and stable diagnostic for an escaping file symlink; and
13. the exact stable diagnostic-code vocabulary.

Permission and generic stat failure will be added in the developer implementation phase
using focused monkeypatching, because making real permissions fail is unreliable on Windows.
An in-repository file-link test will accompany symlink implementation. Every unfinished
behavioral test is `xfail(strict=True)` and names Milestone 1.1. The diagnostic vocabulary
test passes now because it tests the contract, not traversal.

No new harness fixture or gold change is warranted for the contracts-only run: `tmp_path`
expresses ignore, limit, and symlink boundary cases more clearly, while graph gold would
prematurely couple scanning to later stages. After implementation, run read-only scan tests
against `harness/fixtures/python_service/repo` and
`harness/fixtures/markdown_documented_project/repo`; do not change graph gold until graph
behavior exists. `harness-smoke` must remain 5 fixtures, 5 questions, and 5 diff cases.

Regression risks are accidental graph coupling, treating traversal order as filesystem
order, leaking Windows separators, decoding source, following link escapes, counting
skipped files toward limits, and allowing xfails to hide Milestone 0 failures.

## Known edge cases

- Case-only path collisions are distinct lexical files on case-sensitive systems but may
  be impossible on Windows; ordering remains string-based.
- A file may change between `stat()` and a later extractor read. The scanner records the
  observed metadata only; later stages must report their own failure.
- Broken links and transient deletion become `stat_failed`.
- Mount points and Windows junctions need the same no-directory-link intent; platform tests
  may need targeted additions after observing `Path.is_symlink()` behavior.
- Git patterns requiring nested `.gitignore` context are deferred explicitly.
- Git cannot re-include a file beneath a still-excluded parent directory.
- A symlink to an in-root file can produce two `SourceFile` records under two lexical paths;
  deduplicating by inode is not part of M1.1.
- A root itself supplied through a symlink resolves to its target and becomes the internal
  containment boundary.
- Aggregate limit precedence is file-size, then file-count, then repository bytes for one
  candidate; only the first applicable diagnostic is emitted.

## Phased manual implementation sequence

The exact developer-owned function is the public function already declared in
`src/repolens/scanner.py`:

```python
def scan_repository(
    repository_root: Path,
    config: RuntimeConfig,
    *,
    supported_suffixes: frozenset[str] = DEFAULT_SUPPORTED_SUFFIXES,
) -> ScanResult:
    ...
```

Inputs are a possibly relative repository directory, validated limits, and an optional
suffix allowlist. Output is one deterministic `ScanResult`. Required invariants are no
content reads, no execution, no directory-link traversal, no external file-link inclusion,
portable relative paths, stable ordering/codes, and returned totals/counts within limits.

Plain-language algorithm: validate and internally resolve the root; load the one root
ignore file; walk top-down in sorted order; prune default, symlinked, and ignored
directories; classify supported files; derive a safe relative path; validate file-link
containment; stat metadata; apply individual and aggregate limits; collect metadata or a
stable diagnostic; stop only at aggregate limits; sort both public collections; return the
accepted-byte sum.

Pseudocode only:

```text
normalize caller suffixes
validate root; on expected root failure return empty result plus one diagnostic
resolve root internally
compile root ignore rules, or an empty rule set
initialize files, diagnostics, total_bytes, stop = false

for each top-down walk directory:
    sort and mutate dirnames to remove defaults, links, and safely prunable ignores
    for each sorted filename:
        if suffix unsupported or path ignored: continue
        derive relative POSIX path from the lexical path
        if file link resolves outside root: diagnose and continue
        stat before inclusion; on expected failure diagnose and continue
        if individual size too large: diagnose and continue
        if accepted count would exceed limit: diagnose, set stop, break
        if accepted bytes would exceed limit: diagnose, set stop, break
        append SourceFile and add observed size
    if stop: break

sort files and diagnostics by their documented keys
return ScanResult
```

Three focused hints:

1. With top-down `os.walk`, assigning `dirnames[:] = kept_names` controls which directories
   are visited; filtering only after descent wastes work and violates the pruning contract.
2. Keep the lexical candidate path for output, then use
   `candidate.relative_to(resolved_root).as_posix()`; use a separately resolved path only
   for symlink containment.
3. Call `candidate.stat()` before constructing `SourceFile`. Its `st_size` decides the
   per-file and aggregate checks without opening or decoding the file.

Study `pathlib.Path`, `os.walk` top-down behavior, mutable list slice assignment,
`Path.relative_to`, `Path.as_posix`, `Path.resolve`, `Path.is_symlink`, `Path.stat`, symlink
containment, `sorted`, tuples, frozen Pydantic models, `StrEnum`, and Git ignore/negation
semantics.

The first manual implementation task is deliberately small: implement root validation,
internal resolution, sorted top-down traversal, unconditional default-directory pruning,
case-insensitive suffix filtering, and relative POSIX `SourceFile` metadata with `stat()`.
Do not add `.gitignore` or limits until those basic tests and Milestone 0 tests are green.

## Progress

- [x] 2026-07-16: Read project contract, ExecPlan convention, requested source files, all
  existing tests, and harness structure.
- [x] 2026-07-16: Stated observable acceptance criteria before behavior.
- [x] 2026-07-16: Finalized public contracts and explicit scanning semantics.
- [x] 2026-07-16: Added the placeholder models/API and hand-written strict-xfail tests.
- [x] 2026-07-16: Ran and recorded the full contracts-only validation set.
- [x] 2026-07-16: Implemented M1.1A root validation, deterministic traversal, default and
  directory-symlink pruning, suffix filtering, relative metadata, and byte totals.
- [x] 2026-07-16: Removed xfails only from behavior fully delivered by M1.1A and added a
  focused `supported_suffixes` override test.
- [x] 2026-07-16: Implemented M1.1C root-only Git ignore matching, negation, ignored-directory
  pruning, and pre-`stat()` ignored-file exclusion with pathspec 1.1.1.
- [x] 2026-07-16: Implemented file-symlink containment with strict resolution and
  `Path.relative_to`, lexical link-path output, and focused filesystem diagnostics before
  limit accounting.
- [x] 2026-07-16: Implemented M1.1B deterministic individual-file, accepted-file-count,
  and accepted-repository-byte limits with stable diagnostics and aggregate stop behavior.
- [x] 2026-07-16: Added exact-boundary, ignored/unsupported accounting, rejected-total,
  first-excluded, single-diagnostic, and repeat-scan resource tests.
- [x] 2026-07-16: Linux GitHub Actions passed after push and verified the real directory,
  escaping-file, and contained-file symlink integrations.
- [x] 2026-07-16: Closed Milestone 1.1 with M1.1A, M1.1B, M1.1C, and M1.1D complete;
  Milestone 1 remains active and M1.2A is next.

## Decisions

- **2026-07-16 — Remove public absolute paths.** Alternative: retain `absolute_path` but
  exclude it from serialization. Rationale: later callers can join the internal root and
  relative path; removing it makes portability and non-leakage structural. Consequence:
  scanner output is safe to compare and serialize directly.
- **2026-07-16 — One result channel for expected filesystem states.** Alternative: custom
  exceptions for root errors. Rationale: callers already need partial diagnostics and a
  second error schema adds complexity. Consequence: invalid roots return empty diagnosed
  results; programming/config errors may still raise.
- **2026-07-16 — Root `.gitignore` only.** Alternative: stacked nested rules. Rationale:
  nested Git semantics materially complicate pruning and have no requested behavioral test
  in this slice. Consequence: nested control is explicitly deferred, not approximated.
- **2026-07-16 — Use pathspec 1.1 for root ignore behavior.** Alternative: custom matching.
  Rationale: Git wildmatch and negation are subtle, and pathspec 1.1.1 was already resolved
  in the lock. Consequence: `pathspec>=1.1,<2` is now a direct runtime dependency and the
  non-deprecated `gitignore` pattern factory is used.
- **2026-07-16 — Include safe file symlinks by lexical link path.** Alternative: exclude all
  links. Rationale: the security boundary only requires excluding escapes, while a safe
  link is a legitimate repository entry. Consequence: duplicate target content under
  distinct paths is allowed.
- **2026-07-16 — Stop on aggregate limits, continue on per-file oversize.** Alternative:
  continue searching for smaller later files. Rationale: a deterministic accepted prefix
  is simpler to explain and makes reaching a global bound explicit. Consequence: exactly
  one aggregate-limit diagnostic names the stopping candidate.
- **2026-07-16 — M1.1A implements only the basic scan prefix.** Alternative: satisfy every
  existing scanner xfail at once. Rationale: the implementation request explicitly reserves
  ignore matching, limits, file-symlink containment, and filesystem recovery for later
  phases. Consequence: those strict xfails remain executable scope markers.
- **2026-07-16 — Resource checks precede mutation.** Alternative: append then roll back on a
  limit breach. Rationale: checking individual size, accepted count, and proposed bytes
  before `SourceFile` construction makes rejected files structurally unable to affect count
  or totals. Consequence: individual oversize continues, while aggregate limits add one
  diagnostic and stop the deterministic walk.

- **2026-07-16 — Containment uses resolved paths; output uses lexical paths.** Alternative:
  compare path strings or emit the resolved target. Rationale: `Path.relative_to` enforces
  path-component containment without prefix ambiguity, while the link name is the stable
  repository identity. Consequence: external targets are diagnosed without leaking them,
  and contained links can coexist with their targets under distinct lexical paths.

## Discoveries and surprises

- **2026-07-16:** The worktree reports branch `main`, not the branch named in the request,
  and `git branch --list` shows no alternative. This plan records actual state; no branch
  mutation was inferred.
- **2026-07-16:** `pathspec` appears in `uv.lock` but not `pyproject.toml`. Production code
  cannot rely on that transitive development dependency, so declaration is deferred to the
  phase that imports it.
- **2026-07-16:** Existing harness gold describes future graph facts, not scanner output.
  Temporary unit trees are the focused contract vehicle; changing gold now would broaden
  scope.
- **2026-07-16:** At M1.1A start, the active branch was `Python-definition-extractor`, even
  though the earlier contracts-only session had observed `main`. Codex did not perform a
  branch operation in either session.
- **2026-07-16:** The focused M1.1A scanner run passed 11 tests, kept 4 later behaviors as
  strict xfails, and skipped 2 symlink tests because Windows denied link creation. Scanner
  module coverage was 91% in that focused run.
- **2026-07-16:** The M1.1C prompt stated M1.1B limits were complete, but the local scanner
  contained no limit enforcement and all three limit tests remained strict xfails. M1.1C
  preserved that local state rather than broadening scope into limits.
- **2026-07-16:** `uv lock --offline` could not resolve uncached metadata for every supported
  Python split. An approved online `uv lock` completed, changing only lock revision and the
  direct RepoLens pathspec dependency records.
- **2026-07-16:** Pathspec 1.1.1 warns that the legacy `gitwildmatch` factory name is
  deprecated. The current `gitignore` factory provides the required Git ignore/wildmatch
  semantics without warnings.
- **2026-07-16:** M1.1B was implemented after M1.1C in this worktree. The label order differs
  from execution chronology, but the scanner flow remains suffix → root ignore → stat →
  individual limit → count limit → proposed repository bytes → append/account.
- **2026-07-16:** The focused M1.1B run passed all 24 reachable scanner tests and skipped
  both symlink tests because Windows denied link creation. Scanner module coverage was 96%.
- **2026-07-16:** Windows denied all three real-symlink test creations with error 1314.
  Focused monkeypatch-backed tests cover the same pruning, containment, resolution-failure,
  and metadata-failure decisions locally. Linux GitHub Actions later passed after push and
  verified the real directory, escaping-file, and contained-file symlink integrations.

## Validation transcript

Run from `C:\RepoLens` without network access:

```text
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run repolens harness-smoke
uv run repolens doctor
git diff --check
```

GNU Make is unavailable in the documented Windows environment. Do not claim `make check`
ran unless that changes. Record normally passing tests, strict M1.1 xfails, coverage, and
platform symlink skips separately after execution.

Contracts-only validation on 2026-07-16, Python 3.11.15:

- `uv run ruff format --check .` — exit 0; 39 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 25 source files.
- `uv run pytest` — exit 0; 25 passed normally, 12 strict M1.1 xfailed, and 2
  symlink tests skipped in 0.35 seconds; total coverage was 89%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff
  cases were valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy;
  no network is required.
- `git diff --check` — exit 0; only line-ending conversion warnings were printed for
  three already tracked Markdown files.

The 25 normal passes comprise all 23 pre-existing Milestone 0 tests plus two scanner
contract tests. The 12 xfails cover unfinished non-symlink behavior. The two symlink tests
skipped before reaching the placeholder because Windows returned error 1314 when creating
links; on a link-capable host they remain strict xfails until implementation. GNU Make was
not invoked and this record does not claim `make check` ran.

M1.1A validation on 2026-07-16, Python 3.11.15:

- `uv run ruff format src/repolens/scanner.py tests/test_scanner.py` — exit 0; both files
  were unchanged in the final run.
- `uv run ruff format --check .` — exit 0; 39 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 25 source files.
- `uv run pytest tests/test_scanner.py -v` — exit 0; 11 passed, 4 strict xfailed, and
  2 symlink tests skipped in 0.24 seconds; scanner module coverage was 91%.
- `uv run pytest` — exit 0; 34 passed normally, 4 strict xfailed, and 2 symlink tests
  skipped in 0.31 seconds; total coverage was 90%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases
  were valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy;
  no network is required.
- `git diff --check` — exit 0; only line-ending conversion warnings were printed.
- `git status --short` — five intended files modified: this plan, `CODEX.md`, `README.md`,
  `src/repolens/scanner.py`, and `tests/test_scanner.py`.

GNU Make was not invoked and this record does not claim `make check` ran.

M1.1C validation on 2026-07-16, Python 3.11.15:

- `uv lock --check` — exit 0; 26 packages resolved and the lock was current.
- `uv run ruff format src/repolens/scanner.py tests/test_scanner.py` — exit 0; both files
  were unchanged.
- `uv run ruff format --check .` — exit 0; 39 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 25 source files.
- `uv run pytest tests/test_scanner.py -v` — exit 0; 16 passed, 3 strict xfailed, and
  2 symlink tests skipped in 0.24 seconds; scanner module coverage was 93%.
- `uv run pytest` — exit 0; 39 passed normally, 3 strict xfailed, and 2 symlink tests
  skipped in 0.33 seconds; total coverage was 90%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases
  were valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy;
  no network is required.
- `git diff --check` — exit 0; only line-ending conversion warnings were printed.
- `git status --short` — seven intended files modified: this plan, `CODEX.md`, `README.md`,
  `pyproject.toml`, `src/repolens/scanner.py`, `tests/test_scanner.py`, and `uv.lock`.

GNU Make was not invoked and this record does not claim `make check` ran.

M1.1B validation on 2026-07-16, Python 3.11.15:

- `uv run ruff format src/repolens/scanner.py tests/test_scanner.py` — exit 0; both files
  were unchanged in the final run.
- `uv run ruff format --check .` — exit 0; 39 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 25 source files.
- `uv run pytest tests/test_scanner.py -v` — exit 0; 24 passed and 2 symlink tests
  skipped in 0.23 seconds; scanner module coverage was 96%.
- `uv run pytest` — exit 0; 47 passed normally and 2 symlink tests skipped in 0.33
  seconds; total coverage was 91%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases
  were valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy;
  no network is required.
- `git diff --check` — exit 0; only line-ending conversion warnings were printed.
- `git status --short` — five intended files modified: this plan, `CODEX.md`, `README.md`,
  `src/repolens/scanner.py`, and `tests/test_scanner.py`.

GNU Make was not invoked and this record does not claim `make check` ran.

M1.1D local validation on 2026-07-16, Python 3.11.15:

- `uv run ruff format .` — exit 0; 39 files left unchanged.
- `uv run ruff format --check .` — exit 0; 39 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 25 source files.
- `uv run pytest tests/test_scanner.py -v` — exit 0; 30 passed and 3 real-symlink
  integrations skipped; scanner module coverage was 97%.
- `uv run pytest` — exit 0; 53 passed and 3 real-symlink integrations skipped; total
  coverage was 91%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases
  were valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy;
  no network is required.
- `git diff --check` — exit 0.

Windows error 1314 prevented real symlink creation in all three integration tests.
Platform-independent focused tests passed locally. Linux GitHub Actions subsequently passed
after push and verified the real directory, external-file, and contained-file symlink
behaviors. GNU Make is unavailable, so this record does not claim `make check` ran.

## Learning checkpoint

The developer must explain in their own words: why discovery returns metadata rather than
contents; how mutating `dirnames` prevents traversal; why lexical and resolved paths serve
different purposes for symlinks; what each byte/count limit counts; why aggregate limits
stop while individual oversize continues; and why nested ignore semantics were deferred.

Prompt: “Trace one candidate file from `os.walk` through ignore checks, relative POSIX path
normalization, symlink containment, `stat()`, each resource limit, and final deterministic
sorting. At each step, state what can fail and whether scanning continues or stops.”

## Outcome and follow-ups

The contracts-only outcome established the typed scanner boundary and executable expected
behaviors. M1.1A implements the Phase 1 basic deterministic scan, M1.1C implements root
`.gitignore`, M1.1B enforces all three configured resource limits, and M1.1D implements
directory-link pruning, file-link containment, and focused filesystem diagnostics before
accounting. Linux GitHub Actions passed after push and verified the real symlink behavior
that Windows privilege error 1314 prevented from running locally. Milestone 1.1 is complete,
but Milestone 1 remains active. The next active slice is Milestone 1.2A — Basic Python
definition extraction; `index` remains unfinished and graph work remains out of scope.
