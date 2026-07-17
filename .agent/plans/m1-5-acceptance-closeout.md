# Milestone 1.5 — Fixture Gold, Deterministic Acceptance, and Closeout

## Purpose and user-visible outcome

Milestone 1.5 proves the complete Milestone 1 repository-indexing contract against small,
reviewable fixture repositories. It adds committed canonical `RepositoryIndexResult` gold,
semantic acceptance assertions authored independently from production output, byte-level
repeatability checks, graph-integrity checks, security/non-execution checks, representative
diagnostic checks, and closeout documentation. When all local checks pass, Milestone 1 is
locally complete and `repolens index PATH` has a reproducible acceptance record.

## Scope and non-goals

In scope are acceptance tests, separate M1 canonical gold for selected existing fixtures,
an explicit gold update/check helper, harness documentation, CI coverage review, validation,
and Milestone 1 documentation closeout. Production code may change only if an acceptance
test first demonstrates a concrete violation of an authoritative M1 criterion.

Out of scope are import or call resolution, JavaScript/TypeScript/JSX/TSX source extraction,
lockfile parsing, overview/query/impact generation, MCP, caching, and any new parser or graph
relationship. Existing future-looking harness `gold.json` files remain unchanged.

## Current state

- Baseline on `Python-definition-extractor` is clean: 170 tests pass, 3 real-symlink tests
  skip on Windows privilege error 1314, total coverage is 92%, and Mypy reports no issues
  in 32 source files.
- `repolens index PATH` writes a canonical complete `RepositoryIndexResult` to
  `repolens-out/graph.json` and prunes that output directory from later scans.
- Unit and integration tests prove each M1 feature individually, but no selected harness
  fixture is compared with current-schema committed canonical output.
- Existing fixture `gold.json` files describe future resolved calls, tests, documents,
  paths, ambiguity, queries, and impact. They are valid evaluation contracts but are not
  current M1 production snapshots and must not be overwritten.
- Linux CI runs `make check`, which covers format check, lint, Mypy, full pytest, and
  harness smoke. `doctor` is healthy locally but is not yet explicit in the workflow.

## Acceptance criteria

1. Selected Python, Markdown, and metadata fixtures index successfully through the public
   CLI and parse back as `RepositoryIndexResult`.
2. Independently authored semantic expectations prove required structural, Python,
   Markdown, metadata, unresolved-import, and diagnostic facts.
3. Every selected result has unique node IDs and normalized edges; every edge endpoint
   exists; every source path is repository-relative POSIX text; schema version is present;
   canonical collection ordering holds; and no absolute fixture path or runtime timestamp
   appears.
4. Each selected fixture matches a committed canonical M1 gold file byte-for-byte.
5. Two consecutive CLI indexes of each selected fixture produce identical bytes and
   SHA-256 values. Reordered internal collections and controlled filesystem enumeration
   produce the same canonical meaning/bytes where the public contract says order is
   irrelevant.
6. Generated output never re-enters the graph.
7. Harmless sentinels prove indexing does not execute/import Python source, package scripts,
   fenced Markdown, build declarations, Node/npm/TypeScript, shell commands, or network
   access.
8. Invalid Python, malformed metadata, oversized/ignored files, source decode/read failure,
   and escaping symlink behavior retain deterministic policy. Non-fatal failures preserve a
   valid partial graph and CLI exit 0; fatal invalid-root behavior remains non-zero.
9. Existing scanner, extractor, Markdown, metadata, indexer, CLI, model, evaluation, and
   harness tests remain green.
10. Local validation records exact results without claiming GitHub Actions passed during
    this run. Windows real-link skips and pending post-push Linux verification remain clear.

## Milestone phases

### Phase 1 — Plan and acceptance architecture

Record the 16-criterion proof matrix, gaps, selected fixtures, separate-gold decision,
expected file set, and bug/coverage/future-scope distinction before behavioral edits.

### Phase 2 — Explicit gold helper and committed canonical output

Add a small developer-invoked helper under `scripts/` with explicit check/update modes.
It indexes only the four selected fixture `repo/` directories, validates each result through
`parse_index_json()`, and compares or explicitly updates canonical M1 gold. Tests never
overwrite gold. Store M1 gold separately from each fixture's future `gold.json`.

### Phase 3 — Focused acceptance tests

Add `tests/test_milestone1_acceptance.py`. Compare public CLI output with committed bytes,
assert manually authored semantic subsets, validate graph integrity/path privacy, run every
fixture twice, test controlled ordering, prove non-execution, and cover partial/fatal
diagnostics. Expected values must not be constructed by calling production ID or serializer
helpers inside assertion construction.

### Phase 4 — CI and documentation closeout

Make `doctor` explicit in the existing Linux workflow without adding a second workflow.
Document gold commands and semantic differences in `harness/README.md`. Only after all local
acceptance passes, mark M1.1–M1.5 and Milestone 1 locally complete in `CODEX.md` and
`README.md`, add learning questions, preserve the Windows symlink limitation, and name M2
as the next active milestone.

### Phase 5 — Full validation and deterministic transcript

Run every requested command sequentially. For each selected fixture, remove previous
generated output, index twice, record both SHA-256 values, equality, node/edge/import/
diagnostic counts, and remove generated output. Inspect status, diff, and whitespace for
scope growth. Do not commit or push.

## Invariants and contracts

- The canonical serializer and `RepositoryIndexResult` remain the only output/model
  contracts; acceptance adds no second serializer.
- Existing future evaluation gold remains authoritative for future resolver/query/impact
  work. M1 gold is a separate complete canonical current-output artifact.
- Gold updates require explicit developer action and review. Ordinary tests and check mode
  are read-only.
- All expected semantic facts in acceptance assertions are literal, reviewable values.
  Generated gold records full canonical bytes but does not generate the semantic oracle.
- Stable bytes are promised for unchanged source, pinned dependencies/schema/ID namespace,
  and canonical serialization rules—not across intentional schema/parser-version changes.
- Source-backed paths are repository-relative POSIX paths. No clock, random value,
  filesystem root, temporary path, or installed-package state enters output.
- Diagnostics stay in their existing channels and retain existing fatal/non-fatal policy.
- JavaScript and TypeScript fixture source remains structural-excluded in M1; supported
  manifests are metadata inputs only.

## Test and harness plan

Selected fixtures are `python_service`, `markdown_documented_project`,
`fullstack_fastapi_react`, and `typescript_frontend`. Together they cover Python structure
and imports, Markdown hierarchy/facts, `pyproject.toml`, `package.json`, and `tsconfig.json`.

The focused acceptance suite covers successful indexing, model round-trip, committed byte
gold, independently authored semantic gold, structural completeness, edge integrity,
unique IDs, no absolute paths, output pruning, non-fatal partial output, fatal invalid root,
non-execution, repeated bytes, meaningful mismatch reporting, and controlled order
variation. Existing specialized tests remain the detailed proof for resource and parser
edge cases.

## Progress

- [x] 2026-07-17: Verified branch and clean baseline; pytest, Mypy, harness smoke, and
  doctor passed with the documented Windows symlink skips.
- [x] 2026-07-17: Read governing docs, all M1 plans, production contracts, extractor files,
  tests, fixture manifests/repositories/gold, harness docs, and Linux CI.
- [x] 2026-07-17: Reported the authoritative 16-criterion acceptance matrix, proof gaps,
  fixture selection, expected files, and strict coverage/bug/future-scope classification.
- [x] 2026-07-17: Added the explicit check/update helper and four committed canonical M1
  fixture results; normal check mode reports all four match.
- [x] 2026-07-17: Added 12 focused acceptance tests covering the required fixture,
  semantic, integrity, byte, ordering, security, and diagnostic behaviors.
- [x] 2026-07-17: Added explicit Linux CI doctor coverage and completed M1/M2-handoff
  documentation after the local acceptance gate passed.
- [x] 2026-07-17: Ran the complete validation set, recorded four two-run SHA-256 proofs,
  removed generated fixture output, and audited the final scope.

## Decisions

- **2026-07-17 — Keep M1 gold separate from future evaluation gold.** Existing `gold.json`
  files intentionally contain resolver/query/impact expectations beyond M1. Replacing them
  would destroy future acceptance data; separate canonical M1 result files make the current
  compiler output reviewable without changing that contract.
- **2026-07-17 — Use four existing fixtures.** Python and Markdown fixtures are mandatory;
  full-stack supplies pyproject/package metadata and TypeScript frontend supplies tsconfig.
  No JavaScript/TypeScript source extractor or new fixture is required.
- **2026-07-17 — Pair complete byte gold with literal semantic assertions.** Canonical gold
  catches any output drift, while handwritten subsets explain which changes matter and
  avoid a self-generated oracle.
- **2026-07-17 — Treat CI doctor coverage as acceptance plumbing.** Adding the existing
  network-free command to the current workflow changes no product behavior.
- **2026-07-17 — No production repair is planned.** The baseline demonstrates no failing M1
  criterion. Any production edit requires a focused failing regression first.

## Discoveries and surprises

- The existing Markdown fixture has an ignored generated `repolens-out/graph.json` outside
  its `repo/` directory from a prior manual run. It is not tracked or scanned when the
  manifest's repository path is indexed; M1.5 will clean generated outputs before evidence
  runs.
- Existing `make check` already executes the full pytest suite, so adding the focused test
  file automatically places M1 acceptance in Linux CI. Only explicit doctor coverage is
  missing from the workflow.

## Validation transcript

Baseline on 2026-07-17 with Python 3.11.15:

- `git branch --show-current` — `Python-definition-extractor`.
- `git status --short` — no output.
- `uv run pytest` — 170 passed, 3 skipped because Windows could not create real symlinks
  (error 1314), total coverage 92%.
- `uv run mypy src tests` — success, no issues in 32 source files.
- `uv run repolens harness-smoke` — 5 fixtures, 5 questions, 5 diff cases valid.
- `uv run repolens doctor` — Python 3.11.15 and package 0.1.0 healthy; network not required.

Final M1.5 validation on 2026-07-17:

- `uv sync --dev --locked` — exit 0; 27 packages resolved and 26 checked.
- `uv run ruff format .` — exit 0; 48 files left unchanged.
- `uv run ruff format --check .` — exit 0; 48 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 33 source files.
- `uv run pytest tests/test_milestone1_acceptance.py -v` — exit 0; 12 passed.
- `uv run pytest tests/test_scanner.py -v` — exit 0; 33 passed and 3 real-symlink
  integrations skipped because Windows returned privilege error 1314.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 36 passed.
- `uv run pytest tests/test_markdown_extractor.py -v` — exit 0; 24 passed.
- `uv run pytest tests/test_metadata_extractor.py -v` — exit 0; 17 passed.
- `uv run pytest tests/test_indexer.py -v` — exit 0; 24 passed.
- `uv run pytest tests/test_cli.py -v` — exit 0; 19 passed.
- `uv run pytest` — exit 0; 182 passed, the same 3 Windows real-symlink integrations
  skipped, and total coverage was 92%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 healthy; no network
  required.
- `uv run python scripts/update_m1_acceptance_gold.py` — exit 0; M1 gold matched for all
  4 selected fixtures.
- `git diff --check` — exit 0; no whitespace errors; only working-copy LF-to-CRLF notices.

Manual CLI two-run fixture evidence, recorded after removing previous generated output:

- `python_service`: SHA-256
  `00fbfa010fdf255f4438dc84606eab8c9af30c8bc41c8c81400a7f9aee11fdab` on both
  runs; bytes equal; 14 nodes, 13 edges, 2 imports, 0 diagnostics.
- `markdown_documented_project`: SHA-256
  `6b313491589c5e3bba0cf071ac6043baa8396070a68440e1d3d6cd3d2761d574` on both
  runs; bytes equal; 10 nodes, 9 edges, 0 imports, 0 diagnostics.
- `fullstack_fastapi_react`: SHA-256
  `8af42c916a3ede5fc68386fd76e9e7525c335cfb7c7c6d53a995b078fa18b9c4` on both
  runs; bytes equal; 26 nodes, 25 edges, 9 imports, 0 diagnostics.
- `typescript_frontend`: SHA-256
  `761554305f6e4d06cf6329569e30c5292c7ff4ec90762438ec9675e1b7c8d549` on both
  runs; bytes equal; 2 nodes, 1 edge, 0 imports, 0 diagnostics.

Every generated fixture `repolens-out` directory was removed after recording evidence.
GNU Make was not invoked and this plan does not claim `make check` ran. GitHub Actions was
not run during this local session; fresh Linux CI verification remains pending after push.

## Learning checkpoint

The developer must explain how a fixture repository becomes a complete canonical
`RepositoryIndexResult`; why handwritten semantic expectations and generated full-byte gold
serve different purposes; how model normalization plus canonical encoding stabilizes bytes;
how endpoint/path/integrity checks reject corrupt graphs; how sentinels prove parsing is not
execution; how diagnostics preserve a valid partial index; and why M1 is a syntax/direct-
fact graph rather than a resolved dependency or call graph.

## Outcome and follow-ups

Milestone 1 is locally complete. Four selected fixtures have committed current-schema gold,
literal semantic review points, graph-integrity validation, non-execution and diagnostic
acceptance, controlled-order stability, and repeated byte proof. No production defect or
production-code change was required. Commit, push, and fresh Linux CI verification remain
developer actions. The next active milestone is Milestone 2 — JavaScript, TypeScript, JSX,
and TSX extraction.
