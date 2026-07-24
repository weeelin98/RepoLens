# Milestone 2 Complete Acceptance and Documentation Closeout

## Purpose and user-visible outcome

This documentation-only closeout independently verifies the complete Milestone 2 contract
after PR #6 merged. If every acceptance criterion is satisfied, `CODEX.md` and `README.md`
will describe Milestone 2 as complete and Linux-CI verified, while explicitly leaving
Milestone 3 inactive, unapproved, and unstarted.

No runtime behavior changes in this closeout. The user-visible index remains the merged
Milestone 2 result: deterministic JavaScript, JSX, TypeScript, and TSX modules, named
definitions, selected TypeScript declarations, conservative React components, bounded
unresolved import/export/CommonJS facts, and bounded unresolved direct-call occurrences.

## Scope and non-goals

In scope:

- independently review all Milestone 2 acceptance requirements and completed ExecPlans;
- inspect the merged scanner, registry, models, extraction contracts, shared JS-family
  extractor, indexer, serialization, CLI, tests, fixtures, gold helpers, and CI records;
- run the complete local acceptance and repeated-byte checks;
- record prior exact Linux CI evidence for PRs #3 through #6;
- update only `CODEX.md`, `README.md`, and this closeout ExecPlan.

Out of scope:

- production code, tests, fixtures, gold, dependencies, lockfiles, schemas, or CI changes;
- import/export or call resolution;
- graph traversal, overview, impact, query, context-pack, HTTP, FastAPI, frontend linking,
  or MCP behavior;
- Milestone 3 planning details or implementation;
- staging, committing, pushing, or creating a pull request.

## Current state

- The review started from a clean `main` with `HEAD == main == origin/main` at
  `477f8e1de3150535df22215c61c1a5afa1352c11`, the PR #6 merge commit.
- GitHub independently reported PR #6 merged and the same merge commit as the newest
  repository commit.
- M2.1A, M2.1B, M2.2A, and M2.2B were already marked individually complete and had
  required Linux `check` evidence.
- `CODEX.md` and `README.md` still described Milestone 2 as open pending this separate
  acceptance review.

## Acceptance criteria

1. Discovery accepts exactly `.js`, `.jsx`, `.ts`, and `.tsx` for the JS family and routes
   them to JavaScript, JavaScript-with-JSX, TypeScript, and TSX grammar capsules with exact
   `javascript`, `jsx`, `typescript`, and `tsx` labels.
2. Locked packages are tree-sitter 0.26.0, tree-sitter-javascript 0.25.0, and
   tree-sitter-typescript 0.23.2 with runtime/grammar ABI compatibility proven by tests.
3. The merged extractor preserves the documented named definitions, selected TypeScript
   declarations, direct exports, stable qualified names, exact spans, containment, and IDs.
4. React component classification remains conservative and single-node, with exact
   runtime React import, top-level identity, direct JSX return, class heritage, and
   partial-tree boundaries.
5. ESM, CommonJS, re-export, and direct-call output remains bounded unresolved occurrence
   data. Written aliases and optional-call syntax are preserved without target claims.
6. Partial parses emit deterministic first-error diagnostics and never promote facts from
   erroneous or unsupported subtrees; CommonJS/class audits retain their stricter
   whole-program safeguards.
7. Repeated extraction/indexing is byte-identical, paths are repository-relative, no
   timestamp or machine root enters canonical output, and indexed source is never executed.
8. M1, M2.1A, M2.1B, M2.2A, and M2.2B compatibility/gold checks pass without modifying
   committed gold. Historical projections remove only their documented additive channels.
9. No import/export/call/inheritance/HTTP semantic edge, resolution, traversal, report,
   query, context pack, impact, or MCP behavior is introduced.
10. PR #3, #4, #5, and #6 each have a successful required Linux `check` for the exact
    implementation commit.
11. The complete local acceptance commands pass, except that unavailable GNU Make is
    reported as an environment limitation and never represented as a local pass.
12. The final diff changes documentation only, passes `git diff --check`, marks Milestone 2
    complete, and leaves Milestone 3 inactive and unapproved.

## Milestone phases

### Phase 1 — Baseline and contract review

Confirm the clean synchronized PR #6 merge baseline. Read governing documentation and all
four completed Milestone 2 ExecPlans. Derive the complete acceptance matrix from the
repository rather than relying on prior summaries.

### Phase 2 — Implementation, fixture, and CI audit

Inspect production data flow, exact syntax boundaries, historical projections, fixture
ownership, source non-execution, and absence of later-milestone behavior. Verify PR #3–#6
merge and Actions records against GitHub.

### Phase 3 — Local acceptance

Run every requested local command sequentially. Repeat current gold and mixed-suffix CLI
generation, compare bytes and hashes, and verify privacy, source non-execution, language
labels, and semantic-edge absence.

### Phase 4 — Documentation-only closeout

Only after every criterion passes, create `m2-complete-closeout`, update `CODEX.md` and
`README.md`, create this required ExecPlan, run final diff/status checks, and stop without
publishing or beginning Milestone 3.

## Invariants and contracts

- The complete merged production contract is the subject of review; this closeout changes
  no code or serialized schema.
- Direct syntax facts remain outside `GraphSnapshot` until later resolvers can supply
  defensible endpoints and evidence.
- Existing stable IDs, source spans, ordering, and conditional empty-field omission remain
  unchanged.
- Historical compatibility is evidence, not a production filter. Normal current indexing
  continues to expose every current Milestone 2 fact.
- Local Windows results do not claim Linux execution. Linux evidence comes only from the
  exact GitHub Actions records.
- Milestone 3 remains inactive and unapproved after closeout.

## Test and harness plan

The complete suite covers scanner routing and safeguards, registry selection, graph and
fact models, shared extraction, React classification, call facts, index aggregation, CLI
serialization, M1 acceptance, compatibility projections, partial gold, privacy,
non-execution, and deterministic bytes.

The closeout additionally:

- hashes every committed M1/M2 graph file and confirms its Git blob matches `HEAD`;
- regenerates M2.2B twice in memory and compares exact bytes;
- indexes a disposable mixed `.js`/`.jsx`/`.ts`/`.tsx` repository twice through the CLI;
- checks exact language labels, absence of non-`contains` edges, no root/timestamp leakage,
  and an absent execution sentinel;
- verifies PR #3–#6 workflow/job conclusions, implementation SHAs, durations, and URLs.

## Progress

- [x] 2026-07-24: Confirmed clean synchronized `main` at
  `477f8e1de3150535df22215c61c1a5afa1352c11`.
- [x] 2026-07-24: Read `AGENTS.md`, `CODEX.md`, `README.md`, `.agent/PLANS.md`, and all four
  completed Milestone 2 ExecPlans in full.
- [x] 2026-07-24: Audited implementation, contracts, tests, fixtures, gold helpers, package
  pins, CI, and later-milestone scope boundaries.
- [x] 2026-07-24: Verified PR #3–#6 merge and exact successful Linux `check` records.
- [x] 2026-07-24: Completed all local acceptance, compatibility, determinism, privacy, and
  non-execution checks.
- [x] 2026-07-24: Concluded every Milestone 2 acceptance criterion is satisfied.
- [x] 2026-07-24: Created `m2-complete-closeout`.
- [x] 2026-07-24: Updated documentation only and left Milestone 3 inactive and unapproved.
- [x] 2026-07-24: Final `git diff --check`, complete diff, and working-tree status review
  passed with exactly the three authorized documentation paths and no staged files.

## Decisions

- **2026-07-24 — Close Milestone 2 only after a separate whole-milestone review.** Slice
  completion proved each increment; this review verifies their combined contract and
  compatibility.
- **2026-07-24 — Treat calls as unresolved syntax facts for Milestone 2.** A targetless
  `calls` edge would violate graph endpoint and evidence contracts. Resolution remains
  Milestone 3.
- **2026-07-24 — Retain exact historical projections.** M2.1A and M2.2A remove only named
  post-slice additions in tests; production remains unfiltered. M2.1B matches current
  indexing without projection.
- **2026-07-24 — Create a closeout ExecPlan.** The task spans multiple documentation files,
  contracts, CI records, and a material acceptance decision, so `.agent/PLANS.md` requires
  a maintained plan.

## Discoveries and surprises

- The prior documentation contained exact Linux records for PRs #4–#6 but not the complete
  PR #3 job record. GitHub verified PR #3 implementation
  `6d3ee2357a76e7e70e520068b8407f9b9d642692` in workflow `29599151101`, job
  `87946793668`, successful in 17 seconds.
- `SourceSpan` values for JS-family syntax retain tree-sitter's zero-based UTF-8 byte
  columns and exclusive end coordinates; literal Unicode/span tests confirm the behavior.
- GNU Make is still unavailable in the Windows shell. The direct constituent commands
  passed, and all four slice Linux jobs ran the real `make check`.
- Every committed `m1-graph.json` and M2 partial graph matched its `HEAD` Git blob before
  documentation edits.

## Validation transcript

Local Windows validation on 2026-07-24:

- `uv lock --check --offline` — exit 0; 30 packages resolved.
- `uv sync --dev --locked` — exit 0; 30 packages resolved, 29 checked.
- `uv run ruff format --check .` — exit 0; 55 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 37 source files.
- `uv run pytest` — exit 0; 333 collected, 330 passed, 3 Windows error-1314 symlink skips;
  93% total coverage and 95% JS-family extractor coverage.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, 5 diff cases.
- `uv run repolens doctor` — exit 0; Python 3.11.15/package 0.1.0 healthy; no network.
- M1, M2.1B, M2.2A, and M2.2B check-only gold helpers — exit 0.
- Repeated M2.2B generation — 6,654 identical bytes; SHA-256
  `6db66f57e197ed491236f530dd33a502bb7baa8e67330084dbb2c2d33f6335e6`.
- Repeated mixed CLI generation — 9,819 identical bytes; SHA-256
  `98a9d1465f441506c99fcad85e7a6250e821ad572a219e25b02facb43640a9c6`;
  16 nodes, 15 `contains` edges, 6 bounded calls; privacy, labels, non-execution, and
  semantic-edge absence passed.
- `make check` — exit 1 before execution; GNU Make command not found. Its constituents
  passed directly.
- Pre-closeout `git diff --check` — exit 0; pre-closeout status was clean `main`.
- Final documentation `git diff --check` — exit 0; the untracked ExecPlan has no trailing
  whitespace. Status contains only modified `CODEX.md`, modified `README.md`, and untracked
  `.agent/plans/m2-complete-closeout.md`; no path is staged.

Verified Linux CI:

| PR | Implementation commit | Workflow | Job | Result | Duration |
| --- | --- | --- | --- | --- | --- |
| #3 | `6d3ee2357a76e7e70e520068b8407f9b9d642692` | `29599151101` | [`87946793668`](https://github.com/weeelin98/RepoLens/actions/runs/29599151101/job/87946793668) | success | 17 seconds |
| #4 | `b680592a25409f5c7bb0abe9f70b24459298c0d0` | `29776458604` | [`88466891502`](https://github.com/weeelin98/RepoLens/actions/runs/29776458604/job/88466891502) | success | 18 seconds |
| #5 | `7ffb54879195f61a5c0823222b3c342378357bd4` | `29784583712` | [`88493214124`](https://github.com/weeelin98/RepoLens/actions/runs/29784583712/job/88493214124) | success | 16 seconds |
| #6 | `af8e3b01c9e1ef64384e87868350291bbb2dceb2` | `30110044291` | [`89537016292`](https://github.com/weeelin98/RepoLens/actions/runs/30110044291/job/89537016292) | success | 23 seconds |

## Learning checkpoint

The developer should be able to explain:

1. Why `.jsx` uses the JavaScript grammar while `.tsx` requires the TSX capsule.
2. How tree-sitter partial-tree recovery differs from Python AST parse failure.
3. Why direct ESM/CommonJS/call occurrences remain unresolved facts rather than graph
   edges.
4. How conservative React evidence avoids claiming that every JSX-returning PascalCase
   function is a React component.
5. How written aliases, optional syntax, lexical call owners, exact spans, and stable IDs
   remain deterministic without target resolution.
6. How production empty-field omission, exact historical projections, isolated fixture
   ownership, repeated bytes, and Linux CI together establish compatibility.
7. Which resolution, traversal, reporting, HTTP, query, impact, and MCP capabilities remain
   for later milestones.

## Outcome and follow-ups

Every complete Milestone 2 acceptance criterion is satisfied. Milestone 2 is complete and
Linux-CI verified across PRs #3–#6. The next phase is planning Milestone 3; Milestone 3
remains inactive, unapproved, and unstarted.

No production code, test, fixture, gold, dependency, lockfile, schema, or CI file changed.
No staging, commit, push, pull request, or Milestone 3 work is authorized by this plan.
