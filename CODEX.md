# RepoLens Living Project Specification

Status: Milestone 0 in progress  
Last updated: 2026-07-14

## Mission and user problem

RepoLens is a local-first context compiler for AI coding agents. It turns a mixed Python
and TypeScript repository into a complete, evidence-backed typed code graph, a bounded
`CODEBASE_OVERVIEW.md`, query-scoped Markdown context packs, a Git-diff-specific
`CHANGE_IMPACT.md`, and deterministic CLI/MCP retrieval tools.

Coding agents repeatedly scan large repositories, lose cross-file evidence, and spend
context on irrelevant code. A single enormous generated document fails in the opposite
direction: it is expensive, stale, hard to verify, and still cannot preserve every detail.
RepoLens therefore keeps complete coverage in the graph, broad orientation in a bounded
overview, and detailed evidence in scoped context packs.

## Users, positioning, and portfolio goals

Primary users are developers using AI coding agents on local Python, JavaScript, and
TypeScript applications. Secondary users are maintainers reviewing architectural impact
and tool builders consuming deterministic code intelligence.

RepoLens is not a general search engine, hosted code platform, or autonomous code reviewer.
It is a transparent compiler-style pipeline whose conclusions retain source spans and
uncertainty. The portfolio should demonstrate schema design, parsing, static resolution,
deterministic systems, CLI/API boundaries, evaluation discipline, and honest failure
analysis. In interviews the developer should be able to derive the stable-ID scheme,
explain every evidence class, trace a cross-stack flow, interpret evaluation errors, and
defend the dependency boundaries without relying on framework magic.

## Product principles

1. Complete coverage lives in `graph.json`.
2. Broad orientation stays within a configurable overview budget (default about 8,000
   tokens later).
3. Detailed evidence is selected on demand and always cited.
4. Static facts, resolver results, heuristics, and ambiguity are never conflated.
5. Identical content produces byte-stable deterministic output when time metadata is
   excluded.
6. MCP and CLI adapt application services; they do not contain analysis logic.
7. Evaluation fixtures and baselines evolve with behavior.

## Reference-project decisions

The only inspected reference material is Graphify's public README. Direct observations,
design inferences, and the clean-room boundary are recorded in
`docs/REFERENCE_ANALYSIS.md`.

Adopted high-level ideas: staged extraction, normalized graph data, evidence-backed edges,
a complete graph plus bounded report, query-first agent consumption, deterministic local
parsing, and fixture-driven evaluation.

Changed: Python uses the standard-library AST; evidence has four classes; reports are
explicitly token-bounded; and the showcase targets React-to-FastAPI flows.

Rejected or deferred: dozens of languages, media extraction, LLM-created code semantics,
HTML visualization, community detection, graph databases, many-assistant installation,
and unmeasured performance or token claims. No reference implementation code is copied.

## Scope

### MVP capabilities

- `.gitignore`-aware discovery with file and repository limits.
- Stable typed nodes/edges with repository-relative source spans.
- Python AST extraction; tree-sitter JS/TS/JSX/TSX extraction; deterministic Markdown and
  metadata extraction.
- Cross-file imports/exports and statically recoverable direct calls.
- Explicit ambiguous/unresolved records.
- FastAPI routes, frontend `fetch`/Axios calls, and conservative endpoint matching.
- Symbol lookup, caller/callee traversal, dependency paths, query context packs, overview,
  and Git-diff change impact.
- Deterministic JSON/Markdown outputs, CLI services, a thin MCP adapter, and evaluation.

### Language tiers

- Tier A, deep: Python.
- Tier B, practical: JavaScript, TypeScript, JSX, TSX.
- Tier C, structure/docs: Markdown, MDX, `package.json`, `pyproject.toml`, `tsconfig.json`.
- SQL is a possible stretch goal after MVP evidence; it is not a requirement.

### Non-goals

No PDF/image/audio/video, Java, Go, Rust, Neo4j, embeddings, vector databases, cloud
multi-tenancy, runtime tracing, or exhaustive framework magic. No single Markdown artifact
reproduces the repository. No network is required by tests. No unsupported language may be
added without an explicit scope decision, fixtures, and acceptance criteria.

## Architecture and data flow

`scanner -> extractor registry -> per-language facts -> resolvers -> graph builder ->`
`deterministic serialization -> traversal/ranking/impact -> Markdown renderers -> CLI/MCP`

The evaluation package consumes the same graph/output contracts but does not import CLI or
MCP adapters. Fixtures can be schema-validated before production extractors exist.

### Package boundaries

- `config`: validated local resource and output settings.
- `models` and `ids`: graph contract, normalization, stable IDs, canonical serialization.
- `scanner`: discovery only; it does not parse content.
- `extractors`: syntax/metadata facts and direct evidence; no graph traversal.
- `resolvers`: cross-file candidates, ambiguity, confidence, and resolver notes.
- `graph`: assembly, invariants, deterministic export, traversal primitives.
- `context`: ranking, budgeting, overview and scoped Markdown rendering.
- `impact`: Git diff parsing and affected-symbol propagation.
- `evaluation`: schemas, pure metrics, validators, runner, and baselines.
- `mcp`: thin adapter over deterministic services, never parser/ranker logic.
- `cli`: argument parsing, orchestration, diagnostics, and explicit errors.

Dependencies point inward toward contracts and services. Renderers do not mutate the
graph. Extractors do not call resolvers. MCP does not import parser implementations.

## Graph data contract

### Nodes

Kinds: `repository`, `directory`, `file`, `module`, `class`, `function`, `method`,
`react_component`, `api_endpoint`, `data_model`, `test`, `markdown_document`,
`markdown_section`, `external_dependency`.

Every node supports `id`, `kind`, `label`, optional `language`, repository-relative
`source_path`, optional 1-based source span, optional qualified name/signature, and JSON
metadata. Repository and external nodes may lack a source span; source-backed symbol nodes
must gain one once their extractor is implemented.

### Edges

Relations: `contains`, `imports`, `exports`, `calls`, `inherits`, `defines_endpoint`,
`invokes_endpoint`, `documents`, `references`, `tests`, `reads_model`, `writes_model`.

Every edge supports source and target node IDs, relation, evidence kind, confidence in
`[0,1]`, optional evidence path/span, and optional resolver notes. Edge endpoints must exist
in the snapshot. Duplicate semantic edges are normalized before serialization.

Evidence classes:

- `syntax_direct`: explicit syntax; confidence is exactly 1.
- `resolver_derived`: deterministic resolution from syntax and repository structure.
- `heuristic`: a documented conservative rule, never presented as certain.
- `ambiguous_unresolved`: multiple/no defensible targets; confidence at most 0.5 and notes
  are mandatory.

### Stable IDs

IDs are derived from a versioned namespace, node kind, normalized POSIX repository-relative
path, qualified name, and a disambiguator such as a declaration start position. Input is
Unicode-normalized and serialized with fixed separators; SHA-256 supplies a compact digest
prefixed by node kind. IDs exclude absolute repository roots, modification times, traversal
order, and mutable labels. Changing the algorithm requires a schema/namespace version and
gold migration. A relocation changes an ID in MVP; future content-aware continuity is a
separate decision.

## Extraction contracts

An extractor declares supported extensions and accepts a normalized source record. It
returns nodes, direct edges, diagnostics, and unresolved syntax facts without side effects.
Output order is irrelevant because the graph boundary sorts it. Invalid syntax produces a
diagnostic and partial results only when correctness can be maintained.

Python uses `ast`, preserving decorator, import, qualified-name, and line/column evidence.
JS/TS/JSX/TSX later use pinned compatible tree-sitter grammars. Markdown deterministically
extracts headings, hierarchy, links, fenced blocks, and inline-code references. Metadata
extractors parse only documented structural fields. The MVP never asks an LLM to invent an
edge.

## Resolver contracts

Resolvers consume extracted facts plus an immutable repository index and return candidate
edges. They must record the rule used, confidence, evidence, and all unresolved ambiguity.
Python resolution follows package/module rules within configured roots without importing
or executing user code. JS/TS resolution handles relative paths, explicit extensions,
index files, and a bounded subset of `tsconfig` aliases documented by tests. Calls resolve
only statically defensible identifiers/attributes. Dynamic import, reflection, monkey
patching, dependency injection, and runtime-generated names remain explicit limitations.

HTTP matching normalizes literal paths, simple `{param}`/`:param` segments, and methods.
It recognizes common `fetch` forms and `axios.get/post/put/patch/delete`, and FastAPI
decorator routes. Generated URLs, proxies, framework magic, and unknown methods remain
ambiguous rather than guessed.

## Output contracts

All generated files live under `repolens-out/`:

```text
graph.json
CODEBASE_OVERVIEW.md
CHANGE_IMPACT.md
contexts/<query-slug>.md
metrics/indexing.json
metrics/evaluation.json
```

`graph.json` is schema-versioned, UTF-8, canonical-keyed, and stably sorted. Generated dates
are omitted from deterministic payloads or isolated outside compared content.

The overview targets about 8,000 tokens by default and contains summary, languages and
frameworks, entry points, modules, important symbols, frontend routes/components, backend
endpoints, models, cross-stack flows, hotspots, ambiguity, freshness, citations, and how to
request details. It is orientation, not source reproduction.

A context pack records the question, selected nodes/edges, paths, signatures, useful
docstrings/comments, small snippets, path/line citations, unresolved assumptions,
truncation, and estimated tokens. `CHANGE_IMPACT.md` records the diff range, changed spans,
direct/propagated affected symbols, reasons, uncertainty, citations, and limits.

## CLI and MCP contracts

Planned CLI:

```text
repolens index <path>
repolens overview
repolens find <symbol>
repolens callers <symbol>
repolens callees <symbol>
repolens path <source> <target>
repolens query "<question>" --budget <tokens>
repolens impact --diff <git-range>
repolens eval
repolens doctor
```

Milestone 0 also exposes `repolens harness-smoke`. Unimplemented commands exit nonzero with
a message naming the target milestone; they never emit fake artifacts.

Later MCP tools are `get_codebase_overview`, `find_symbol`, `get_symbol_context`,
`trace_dependency_path`, and `analyze_change_impact`. MCP handlers validate transport
arguments and call application services. They contain no parsing, traversal, ranking, or
impact logic. Milestone 0 has only interface documentation/placeholders.

## Context budgeting

Ranking later starts with exact symbol/path/question matches, expands a bounded graph
neighborhood and useful dependency paths, assigns evidence/role weights, then packs units
without splitting required citations. Reserved budget covers headers, assumptions, and
truncation notices. Approximate tokens use a documented deterministic estimator until a
tokenizer dependency is justified. Stable tie-breakers are node ID and source position.
The renderer reports its estimate and omitted categories; it never claims exact model
tokens.

## Determinism

Normalize paths to repository-relative POSIX form, Unicode to NFC, line endings where
needed, dictionaries by key, nodes by ID, edges by a full semantic tuple, diagnostics by
location/code, and output sections by explicit ranking plus stable tie-breakers. Avoid set
iteration, wall-clock data, random seeds, environment paths, and parser-version drift in
gold output. Determinism tests compare bytes across repeated runs and shuffled inputs.

## Security and resource limits

RepoLens reads local repositories and writes only beneath the configured output directory.
It never executes indexed source, imports target modules, evaluates package scripts, or
follows symlinks outside the repository by default. Discovery later enforces maximum file
bytes, repository bytes/file count, ignored directories, allowed suffixes, decoding policy,
and configurable time/diagnostic limits. Generated snippets escape Markdown fences. Git
commands use argument arrays and validated ranges. Tests never require a network. MCP input
and output budgets are bounded. Secrets and `.env` contents are not rendered.

## Test strategy

Unit tests cover schemas, IDs, normalization, extractors, resolvers, traversal, budgeting,
metrics, and error behavior. Integration tests build each synthetic repository and compare
normalized graphs, paths, context citations, impact results, and bytes. CLI tests use an
isolated runner. Property-style cases target ordering and path normalization. Strict xfails
must name a target milestone and missing behavior; existing regressions may not be hidden.

Every behavioral change updates tests and relevant gold data. `make check` is the local and
CI contract: format check, lint, Mypy, pytest, and harness smoke, all network-free.

## Evaluation harness

`harness/fixtures/` contains `python_service`, `typescript_frontend`,
`fullstack_fastapi_react`, `markdown_documented_project`, and
`ambiguous_resolution_cases`. Each manifest versions its fixture, points to a synthetic
repository, gold graph expectations, question JSONL, and diff cases. The full-stack case
contains TSX component -> API client -> literal HTTP call -> FastAPI endpoint -> service ->
repository/model, plus pytest and architecture Markdown.

Gold data represents expected nodes, edges, spans, ambiguity, query results, dependency
paths, and impact. Question records contain ID, category, question, expected node IDs, edge
relations, citations, and maximum context tokens. Diff cases point to patch fixtures and
expected changed/affected symbols.

Metrics: node/edge precision, recall and F1; import accuracy; call precision; endpoint
matching; path correctness; impact recall; citation correctness; determinism; approximate
context size; indexing/query latency; incremental correctness. Pure set/count metrics ship
in Milestone 0; behavior metrics are populated only when their systems exist.

Baselines include ripgrep exact-symbol/path searches and documented manual expectations.
Run them on the same pinned fixtures, question set, budget, and machine conditions. Never
claim graph retrieval beats grep until measured. Optional public-repository benchmarks must
pin commits and remain outside required CI.

## Milestones

### Milestone 0 — Repository scaffold and harness foundation

- **User-visible behavior:** installable CLI reports version/health, validates all fixture
  and gold schemas, and rejects unfinished commands explicitly.
- **Likely files:** guidance/docs, `pyproject.toml`, `src/repolens/{models,ids,cli}.py`,
  extractor/evaluation foundations, `harness/`, `tests/`, CI, Makefile.
- **Invariants:** no parser/resolver claims; stable IDs and canonical snapshots are
  deterministic; harness smoke needs no extractors or network.
- **Tests:** graph validation/round-trip, IDs, evidence, registry, metrics, manifests,
  questions, diffs, sorting, doctor, unfinished commands.
- **Harness cases:** all five fixture schemas and references validate.
- **Acceptance commands:** `make check`.
- **Observable output:** tests pass; `repolens doctor` is healthy; harness reports five
  valid fixtures; unfinished command exits nonzero and names its milestone.
- **Failure modes:** dependency/tool version mismatch, invalid relative fixture reference,
  accidental nondeterminism, placeholder returning success.
- **Learning checkpoint:** explain contract-first architecture, stable IDs, evidence
  validation, and why harness validation precedes extraction.

### Milestone 1 — Scanner, schemas, stable IDs, Python and Markdown extraction

- **User-visible behavior:** `index` discovers bounded files and extracts repository/file,
  Python symbol/import, Markdown hierarchy/link/code-reference facts.
- **Likely files:** config/scanner, Python/Markdown/metadata extractors, graph builder,
  fixture gold and tests.
- **Invariants:** `.gitignore` and resource limits apply; target code is never executed;
  direct facts retain spans; IDs remain stable.
- **Tests:** ignore rules, limits, syntax errors, decorators, nested names, headings/fences,
  metadata, shuffled discovery determinism.
- **Harness cases:** `python_service` and `markdown_documented_project`, plus relevant
  ambiguity cases.
- **Acceptance commands:** `make check` and repeated fixture index byte comparison.
- **Observable output:** deterministic partial `graph.json` with cited Python/Markdown facts.
- **Failure modes:** namespace packages, encodings, symlink escape, AST end positions,
  malformed Markdown.
- **Learning checkpoint:** explain discovery/parser separation and trace one source span to
  its stable graph node.

### Milestone 2 — JavaScript, TypeScript, JSX, and TSX extraction

- **User-visible behavior:** index emits modules, symbols, components, imports/exports, and
  direct calls for the JS/TS family.
- **Likely files:** JS extractor/grammar adapter, registry/config, TS fixtures and gold.
- **Invariants:** grammar versions are compatible/pinned; syntax facts remain direct while
  target resolution is deferred; partial parses emit diagnostics.
- **Tests:** ESM/CommonJS forms in scope, TS declarations, JSX/TSX components, aliases,
  optional chaining, malformed files, deterministic traversal.
- **Harness cases:** `typescript_frontend` and frontend portion of full-stack.
- **Acceptance commands:** `make check` plus TS fixture golden index.
- **Observable output:** repeatable JS/TS nodes and unresolved import/call facts with spans.
- **Failure modes:** grammar API drift, anonymous/default exports, re-exports, JSX name
  inference, dynamic imports.
- **Learning checkpoint:** contrast Python AST and tree-sitter error recovery and explain a
  TSX component classification.

### Milestone 3 — Resolution, graph export, and deterministic overview

- **User-visible behavior:** cross-file imports/exports and defensible calls resolve;
  `graph.json` and bounded overview are emitted.
- **Likely files:** Python/JS import and call resolvers, builder/serialization/traversal,
  overview renderer, schemas and gold.
- **Invariants:** all edges have evidence/confidence; ambiguity remains explicit; identical
  inputs produce identical graph/overview bytes; overview obeys budget.
- **Tests:** package/index/alias resolution, ambiguous names, direct calls, duplicate edges,
  shuffled input, overview citations/truncation.
- **Harness cases:** first four fixtures and ambiguous-resolution cases.
- **Acceptance commands:** `make check`, double index/compare, overview budget assertion.
- **Observable output:** stable complete-in-scope graph and cited bounded overview.
- **Failure modes:** circular imports, shadowing, wildcard exports, alias precedence,
  overconfident call targets, unstable rankings.
- **Learning checkpoint:** walk a direct fact through candidate generation, resolution,
  graph insertion, serialization, and overview selection.

### Milestone 4 — FastAPI, frontend HTTP, and cross-stack endpoint linking

- **User-visible behavior:** FastAPI endpoints and literal frontend calls link by normalized
  method/path into a cited cross-stack flow.
- **Likely files:** Python/JS extractors, HTTP resolver, models/renderers, full-stack gold.
- **Invariants:** literal/method evidence is preserved; parameter normalization is bounded;
  generated URLs and framework magic stay unresolved.
- **Tests:** routers/prefixes, supported Axios/fetch forms, method mismatch, path params,
  duplicate/ambiguous endpoints, service/repository call chain.
- **Harness cases:** full-stack fixture and ambiguity variants.
- **Acceptance commands:** `make check` plus endpoint-match metric report.
- **Observable output:** React -> client -> HTTP -> FastAPI -> service -> model/repository
  dependency path with every hop cited.
- **Failure modes:** router prefixes, base URLs, method inference, wrappers, dependencies,
  false matches on similar paths.
- **Learning checkpoint:** explain why each cross-stack edge is direct, derived, heuristic,
  or unresolved.

### Milestone 5 — Queries, context packs, and Git diff impact

- **User-visible behavior:** find/callers/callees/path/query/impact commands return bounded,
  cited results and write context/impact artifacts.
- **Likely files:** traversal, ranking/budgeting/rendering, Git diff parser/analyzer, CLI,
  evaluation runner and gold.
- **Invariants:** ranking/ties deterministic; budgets include overhead; impact reasons are
  traceable; Git input is validated; uncertainty is visible.
- **Tests:** traversal cycles, ambiguous symbols, path selection, packing/truncation,
  citations, diff hunks/renames/deletes, propagation limits.
- **Harness cases:** question and diff suites across all fixtures.
- **Acceptance commands:** `make check`, query budget assertions, change-impact recall.
- **Observable output:** query packs and `CHANGE_IMPACT.md` within budget with cited reasons.
- **Failure modes:** graph explosion, misleading shortest paths, estimator drift, rename
  mapping, test-impact overreach, missing reverse edges.
- **Learning checkpoint:** defend ranking weights and trace a diff hunk to each affected
  symbol without hand-waving.

### Milestone 6 — MCP, evaluation, failure analysis, and portfolio packaging

- **User-visible behavior:** thin MCP tools mirror deterministic services; reproducible
  evaluation reports and polished docs demonstrate measured strengths and limits.
- **Likely files:** MCP adapter, service interfaces, evaluation runner/baselines, docs,
  examples, CI packaging.
- **Invariants:** MCP contains no analysis logic; identical service calls match CLI results;
  all reported numbers come from committed commands/data; no CI network.
- **Tests:** transport validation, adapter equivalence, timeout/budget errors, metric report
  schemas, baseline parity, install/package smoke.
- **Harness cases:** complete corpus, ripgrep baselines, optional pinned external benchmark
  outside required CI.
- **Acceptance commands:** `make check`, package build/install smoke, MCP protocol smoke,
  documented evaluation reproduction.
- **Observable output:** callable MCP tools, evaluation JSON, failure-analysis narrative,
  demo and portfolio documentation with honest measured results.
- **Failure modes:** transport/service coupling, stale graphs, cherry-picked questions,
  unreproducible latency, accidental secret/path disclosure.
- **Learning checkpoint:** present the architecture and evaluation as an interview demo,
  explain weakest metrics, and propose the next experiment.

## Mentoring workflow

Work one milestone/coherent slice at a time. Before behavioral code, state acceptance
criteria. Let the developer attempt core logic when practical; help in the order hints,
pseudocode, minimal local example. Prefer focused repairs to subsystem replacement. After
work, explain changed data flow and require an own-words explanation at the milestone
checkpoint. Reviews cover correctness, edge cases, tests, types, errors, complexity, and
architecture. Do not introduce an abstraction the developer cannot explain. Add interview
questions to `docs/INTERVIEW_QUESTIONS.md`. Never invent adoption, accuracy, token, or
performance numbers.

## Known hard problems and explicit limitations

Static calls across higher-order functions, monkey patches, dependency injection, dynamic
imports, computed property access, runtime routes, frontend proxies, generated URLs, and
framework plugins may be unresolved. Name collisions and re-export graphs require bounded
candidate sets. Stable IDs trade relocation continuity for determinism. Source snippets can
misestimate model-specific tokens. Git impact is conservative graph reachability, not proof
of runtime effect. The overview necessarily omits details. Parser versions can change
syntax trees and require controlled gold migrations.

## Decision log

- **2026-07-14 — Python 3.11+ src layout.** Modern typing, packaging isolation, and a clear
  import boundary; CI initially targets 3.11.
- **2026-07-14 — Pydantic v2 and Typer only at runtime for M0.** They directly support the
  implemented contracts/CLI; parsing/graph dependencies wait until used.
- **2026-07-14 — SHA-256 stable IDs over normalized semantic coordinates.** Transparent,
  deterministic, dependency-free; versioned for future migration.
- **2026-07-14 — Canonical JSON at the graph boundary.** Models validate meaning while
  serialization enforces byte ordering.
- **2026-07-14 — Harness validation independent of extractors.** Corpus mistakes can fail
  early even while production behavior is intentionally unfinished.
- **2026-07-14 — Clean-room Graphify reference.** Public product ideas inform requirements;
  no source implementation is reused.

## Progress

### Milestone 0

- [x] Inspected the empty/nonexistent working location and initialized a new repository.
- [x] Inspected the reference project's public README at a high level.
- [x] Wrote the pre-code design summary and clean-room reference analysis.
- [x] Created project operating guidance and ExecPlan convention.
- [ ] Implement package foundations and CLI behavior.
- [ ] Create all five fixture corpora, gold records, questions, and diff cases.
- [ ] Add tests, tooling, CI, and run the full validation loop.
- [ ] Record exact results and mark Milestone 0 complete.

## Discovery and surprise log

- **2026-07-14:** The configured workspace path did not yet exist; it was created before
  repository initialization, so there were no useful existing files to preserve.
- **2026-07-14:** System Python is 3.9.6, below the project floor, while `uv` 0.7.18 is
  available. The project will let uv provision/use Python 3.11+ rather than weakening the
  requirement.
- **2026-07-14:** GitHub CLI is absent. GitHub remote creation must use the connected plugin
  if it exposes repository creation, or install/authenticate `gh` as an explicit external
  step; local Milestone 0 work remains unblocked.

## Final portfolio deliverables

- Installable typed Python package and documented CLI/MCP service architecture.
- Five synthetic, understandable fixture repositories with committed gold expectations.
- Deterministic graph, overview, context, and impact examples from measured releases.
- Reproducible evaluation/baseline commands and honest failure analysis.
- Architecture, decision, security, limitations, and clean-room reference documentation.
- A short demo tracing the React-to-FastAPI-to-data flow and a Git change impact.
- Interview questions and developer-written learning explanations for every milestone.
