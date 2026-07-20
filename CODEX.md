# RepoLens Living Project Specification

Status: Milestone 1 complete; Linux CI verified. M2.1A is complete. M2.1B is complete and
Linux CI verified.
Active slice: M2.2A — JSX/TSX Foundation and Conservative React Component Extraction.
Implementation independently reviewed and locally validated on Windows on 2026-07-20;
ready for commit. Milestone 2 remains open and no Linux verification is claimed.
Last updated: 2026-07-20

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
- `indexer`: scanner/extractor orchestration and deterministic in-memory graph assembly.
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
`interface`, `type_alias`, `enum`, `react_component`, `api_endpoint`, `data_model`, `test`, `markdown_document`,
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
`ExtractionResult.imports` holds immutable unresolved import facts; it never implies a
resolved target node or graph edge.
`ExtractionResult.esm_imports` and `ExtractionResult.esm_exports` separately preserve
direct JavaScript/TypeScript ESM syntax because Python relative-import fields do not model
ESM accurately. These channels likewise imply neither a resolved target nor graph edge.
`ExtractionResult.commonjs_requires`, `ExtractionResult.commonjs_exports`, and
`ExtractionResult.esm_reexports` preserve only the bounded M2.1B occurrence forms. A
complete program-level ambiguity guard protects CommonJS global names; all three channels
remain unresolved and create no graph import/export edge.
`ExtractionResult.markdown_facts` similarly holds immutable unresolved links, fenced-code
blocks, and inline-code syntax. Their containing Markdown section may be known while their
referenced target remains unresolved, so they do not become `references` edges.
`ExtractionResult.metadata_facts` holds allowlisted direct fields from exact supported
project manifests. These values are declarations, not installed or resolved dependencies.
Output order is irrelevant because the graph boundary sorts it. Invalid syntax produces a
diagnostic and partial results only when correctness can be maintained.

Python uses `ast`, preserving decorator, import, qualified-name, and line/column evidence.
JS/TS/JSX/TSX later use pinned compatible tree-sitter grammars. Markdown deterministically
extracts headings, hierarchy, links, fenced blocks, and inline-code references. Metadata
extractors parse only documented structural fields. The MVP never asks an LLM to invent an
edge.

## Repository indexing contract

`index_repository(root, config, registry=None)` is the M1.3A in-memory orchestration
boundary. It scans accepted files, creates one repository node plus only the directory and
file nodes required by those files, safely loads registry-supported source, merges direct
extractor facts, and returns `RepositoryIndexResult`. The result keeps a validated
`GraphSnapshot`, unresolved import facts, typed scanner diagnostics, and extractor/source
loading diagnostic strings as separate channels.

The repository node uses the portable `<repository>` sentinel and represents the root; no
second root-directory node exists. Directory/file identity uses only repository-relative
POSIX paths. New structural containment is repository-to-directory/file,
directory-to-directory/file, and Python-file-to-module. All such edges are syntax-direct
with confidence 1.0. Extractor module/symbol containment is retained unchanged.

The default registry is fresh per call and contains `PythonExtractor`,
`JavaScriptTypeScriptExtractor`, `MarkdownExtractor`, and `ProjectMetadataExtractor`; an
injected registry is authoritative.
Files without an extractor
remain structural nodes and are not read. Supported source uses the existing contained
`tokenize.open()` loader, so Python encoding cookies remain honored and ordinary Markdown
is decoded as UTF-8. Expected read/decode failures preserve the file node, emit a
deterministic relative-path diagnostic, and do not block later files. This API does not
resolve imports/references or execute/import target code. M1.3B exposes it through
`repolens index PATH`, canonically serializes the complete `RepositoryIndexResult`, and
atomically writes the configured `graph.json`. M1.4A adds file-to-document containment,
Markdown heading hierarchy, and unresolved Markdown facts to that same result.
M1.4B adds exact-basename discovery and unresolved metadata facts for `pyproject.toml`,
`package.json`, and `tsconfig.json`; arbitrary JSON/TOML remains outside scanning.

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

`graph.json` is the serialized `RepositoryIndexResult`: a nested schema-versioned graph,
unresolved Python, ESM import/export/re-export, and bounded CommonJS facts, unresolved Markdown facts, direct project
metadata facts, scanner diagnostics, and
extractor/source-loading diagnostics. It is
UTF-8, canonical-keyed, stably sorted, compact, and terminated by one newline. Generated
dates and machine paths are omitted. The CLI writes a flushed temporary sibling and uses
atomic replacement so an expected failure cannot expose a partially written final file.

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

Milestone 0 also exposes `repolens harness-smoke`. `repolens index PATH` is implemented in
M1.3B with default output `<repository>/repolens-out/graph.json`; other unimplemented
commands exit nonzero with a message naming the target milestone and never emit fake
artifacts.

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
follows symlinks outside the repository by default. Discovery enforces maximum file
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
- **2026-07-16 — Scanner output excludes absolute paths.** `SourceFile` contains only a
  normalized repository-relative path, lowercase suffix, and observed byte size so public
  deterministic results remain portable and serialization-safe.
- **2026-07-16 — Milestone 1.1 uses root `.gitignore` scope.** Root Git-style patterns and
  ordinary negation are in scope; nested `.gitignore` stacking is explicitly deferred.
  `pathspec` will become a direct runtime dependency only when matching is implemented.
- **2026-07-16 — Expected scanner failures use one result channel.** Invalid roots produce
  empty diagnosed results; per-entry failures produce partial results; aggregate count/byte
  limits stop at the first excluded eligible file.
- **2026-07-16 — M1.1A stops at basic deterministic scanning.** Root validation, top-down
  traversal, default and directory-symlink pruning, normalized suffix filtering, relative
  metadata, and total bytes are implemented. Ignore matching, limits, escaping file-link
  detection, and broad filesystem recovery remain later M1.1 work.
- **2026-07-16 — M1.1C uses root-only pathspec matching.** Only the resolved root
  `.gitignore` is decoded. Pathspec 1.1.1 applies Git-compatible matching and negation to
  relative POSIX paths; nested ignore files have no rule effect, and ignored files are
  excluded before `stat()`.
- **2026-07-16 — M1.1B checks limits before result mutation.** Individual oversize files
  produce a diagnostic and scanning continues. Accepted-file count and proposed repository
  bytes are checked before append; their first breach produces one diagnostic and stops the
  deterministic scan.

- **2026-07-16 — M1.1D separates lexical identity from resolved containment.** File-link
  targets are resolved strictly and checked with `Path.relative_to`; accepted files retain
  the repository-relative lexical link path. Expected metadata `PermissionError` and
  `OSError` states become stable diagnostics without exception or absolute-target text.
- **2026-07-16 — M1.2A uses nearest lexical definition scope.** A direct class-scope
  function is a method; a function nested inside that method is a function. Qualified names
  preserve every enclosing definition and drive the existing stable-ID function.
- **2026-07-16 — Python definition spans preserve AST coordinates.** Definition lines and
  columns map directly from `lineno`, `end_lineno`, `col_offset`, and `end_col_offset`.
  Columns therefore remain zero-based UTF-8 byte offsets with an exclusive end.
- **2026-07-16 — M1.2B keeps import syntax outside the graph.** `UnresolvedImportFact`
  records direct AST evidence in `ExtractionResult.imports`; an `IMPORTS` edge remains
  unavailable until a resolver can supply a defensible target node.
- **2026-07-16 — Import facts use alias-node spans and nullable relative modules.** One
  `ast.alias` becomes one fact. `from . import local` preserves `module=None` and level 1,
  while star imports remain explicit and unexpanded.
- **2026-07-16 — M1.3A wraps the existing validated graph.** `RepositoryIndexResult` keeps
  `GraphSnapshot` intact and adds unresolved imports plus scanner and extractor diagnostic
  channels rather than widening graph models with non-graph facts.
- **2026-07-16 — Structural roots and IDs remain portable.** One `<repository>` node
  represents the root; directory and file nodes use relative POSIX paths, and no absolute
  repository path participates in graph identity or serialized models.
- **2026-07-16 — Registry selection precedes source loading.** The default registry contains
  Python only, an injected registry is not mutated, and files with no extractor are never
  decoded. Python reads use `tokenize.open()` plus a repeated containment check.
- **2026-07-16 — graph.json stores the complete index result.** Serializing only
  `GraphSnapshot` would lose unresolved imports and diagnostics, so the existing canonical
  encoder now supports `RepositoryIndexResult` without a parallel handwritten schema.
- **2026-07-16 — CLI graph writes are atomic.** The command serializes in memory, writes and
  syncs `.graph.json.tmp`, closes it, then replaces the final path. Expected failures clean
  the temporary file when practical and never print success.
- **2026-07-16 — Configured output is pruned before scanner accounting.** A strict
  repository-descendant output directory is excluded top-down so preserved source-like
  files there cannot consume limits or enter repeated indexes.
- **2026-07-17 — M1.4A uses `markdown-it-py` CommonMark tokens.** The constrained
  `markdown-it-py>=4.2,<5` dependency supplies structured ATX/Setext headings, links,
  fences, inline code, and block line maps. Inline child columns are not exposed, so facts
  retain conservative containing-block line evidence instead of searched/guessed columns.
- **2026-07-17 — Unresolved Markdown syntax remains outside the graph.** One typed
  `UnresolvedMarkdownFact` contract preserves links, fenced code, inline code, source
  occurrence, and nearest section. `REFERENCES` edges remain deferred because graph
  endpoints cannot be fabricated solely to satisfy the edge model.
- **2026-07-17 — M1.4B discovers exact metadata basenames.** Scanner eligibility supplements
  `.py`/`.md` suffixes with only `pyproject.toml`, `package.json`, and `tsconfig.json`, then
  applies the same ignore, containment, `stat()`, resource, and output-pruning rules.
- **2026-07-17 — Project metadata remains immutable direct facts.** Documented fields are
  stored in `RepositoryIndexResult.metadata_facts`; structural file nodes are not overloaded
  and external dependency nodes/edges remain deferred until resolution is defensible.
- **2026-07-17 — Metadata uses standard parsers plus constrained JSONC.** Python 3.11
  `tomllib` parses pyproject data, strict standard JSON parses package data, and
  `json-with-comments>=1.2.10,<2` supports tsconfig comments/trailing commas. None exposes
  reliable field positions, so facts carry source paths without fabricated spans.
- **2026-07-17 — M1 acceptance gold is separate from future harness gold.** Existing
  `gold.json` files retain resolver/query/impact expectations beyond M1. Four selected
  fixtures also commit complete canonical `m1-graph.json` results, paired with literal
  semantic assertions and an explicit check/update helper.
- **2026-07-17 — M1 acceptance portability is fixture-scoped.** PR #2 normalizes only
  committed harness fixture text and M1 gold to LF, and corrects the CLI non-execution
  test's contradictory absolute-path input without changing production extraction.
- **2026-07-17 — M2.1A uses pinned compatible tree-sitter wheels.** Runtime 0.26.0 accepts
  grammar ABI 13–15; JavaScript 0.25.0 reports ABI 15 and TypeScript 0.23.2 reports ABI 14.
  A fresh parser is constructed per extraction and no Node/TypeScript process is invoked.
- **2026-07-17 — ESM facts remain separate unresolved channels.** Side-effect, default,
  namespace, and named imports plus direct local declaration/list exports preserve syntax
  without target lookup or `IMPORTS`/`EXPORTS` edges. Empty channels use `exclude_if`, so
  M1 canonical bytes remain unchanged.
- **2026-07-17 — Erroneous and unsupported scopes are barriers.** Only error-free subtrees
  contribute facts. Anonymous functions/classes, generators, constructors, accessors,
  TypeScript namespaces/modules, and ambient declarations cannot leak nested definitions
  under a false extracted parent.
- **2026-07-20 — M2.1B CommonJS is exact and globally guarded.** Only documented direct
  program-child calls, declarators, and assignments produce occurrence facts. A complete
  error-free program-scope audit suppresses any fact whose `require`, `module`, or `exports`
  receiver is bound or reassigned; partial parses suppress every CommonJS fact.
- **2026-07-20 — Re-exports retain written identities without target claims.** Named, star,
  and namespace runtime forms use a dedicated unresolved channel. Explicit type-only forms
  are omitted, and no import/export target node or edge is fabricated.
- **2026-07-20 — Selected TypeScript declarations use honest additive node kinds.** Named
  module-level interfaces, type aliases, and ordinary enums use `interface`, `type_alias`,
  and `enum`; `const enum`, ambient, namespace, nested, and other declarations remain out of
  scope. The nested graph schema stays at version 1 because old payloads still parse and
  new top-level channels default empty and serialize only when nonempty.
- **2026-07-20 — Historical M2.1A comparison uses an exact additive projection.** Tests may
  remove only the three M2.1B node kinds, their containment edges, and the three new fact
  channels before comparing every remaining canonical byte. Production indexing always
  exposes all current M2.1B behavior.
- **2026-07-20 — CommonJS ambiguity follows runtime bindings.** The complete program audit
  includes hoisted program-scope `var`, runtime generator/class/enum/namespace declarations,
  import-equals bindings, and bare program-level reassignments while excluding erased
  type-only imports, interfaces, type aliases, and `const enum`. Exact require matching also
  excludes optional and type-argument calls; named re-exports require identifier names.
- **2026-07-20 — M2.2A component classification is suffix-gated and deliberately narrow.**
  Exactly `.jsx` and `.tsx` add the existing JavaScript and TSX grammar routes with honest
  `jsx`/`tsx` labels. A named top-level function, identifier arrow, or exact React class can
  replace its ordinary node with one `react_component` only when an error-free top-level
  runtime binding import from exact module `react` and a direct JSX return supply evidence.
  Automatic-runtime inference, wrappers, async/nested/anonymous components, indirect
  returns, JSX nodes, calls, inheritance edges, and resolution remain deferred.
- **2026-07-20 — Component reclassification preserves the existing graph path.** The node
  keeps its declaration/declarator span, qualified name, direct exports, and ordinary
  containment, with the node kind participating in the existing v1 stable-ID algorithm.
  Class-body traversal keys on syntax shape so methods remain contained by the single
  component node. No graph/model/serialization schema or dependency changed.
- **2026-07-20 — Optional TSX render methods are not ordinary component evidence.** The
  pinned grammar parses `render?() { ... }` as a `method_definition` with an unnamed `?`
  token even though TypeScript rejects an optional method implementation semantically.
  M2.2A now excludes that exact token so syntax recovery cannot promote the class.

## Progress

### Milestone 0

- [x] Inspected the empty/nonexistent working location and initialized a new repository.
- [x] Inspected the reference project's public README at a high level.
- [x] Wrote the pre-code design summary and clean-room reference analysis.
- [x] Created project operating guidance and ExecPlan convention.
- [x] Implemented package foundations and CLI behavior.
- [x] Created all five fixture corpora, gold records, questions, and diff cases.
- [x] Added tests, tooling, CI, and ran the full validation loop.
- [x] Recorded exact results and marked Milestone 0 complete.

Milestone 1 is complete, including Linux acceptance verification on PR #2 at repair commit
`28ad7fab44fa08d66934dacf541f9b366db14673`. Milestone 2 is in progress: M2.1A is complete,
and M2.1B is complete and Linux CI verified on PR #4 at implementation commit
`b680592a25409f5c7bb0abe9f70b24459298c0d0`. M2.2A is implemented, independently
reviewed, and locally validated on Windows. It is ready for commit; Milestone 2 remains
open and M2.2B is not selected.

### Milestone 1.1 — Repository scanner (complete)

- [x] Created the self-contained scanner ExecPlan with exact API, ignore, symlink, limit,
  diagnostic, security, testing, and manual-implementation decisions.
- [x] Added frozen scanner metadata/result contracts without machine-specific absolute
  paths or graph/extractor dependencies.
- [x] Added hand-written behavioral expectations covering all requested scanner contracts;
  unfinished production behavior remains strict xfail.
- [x] Kept the existing harness gold unchanged because this slice returns metadata rather
  than graph facts.
- [x] M1.1A complete: implemented root validation, resolved top-down traversal,
  pre-descent default and directory-symlink pruning, normalized suffix filtering, POSIX
  metadata, and byte totals.
- [x] Removed strict xfails only for behavior fully delivered by M1.1A and added an explicit
  custom `supported_suffixes` test.
- [x] M1.1C complete: implemented root `.gitignore` matching and negation, pre-descent
  directory pruning, and pre-`stat()` file exclusion; declared pathspec as a direct runtime
  dependency.
- [x] M1.1B complete: implemented maximum individual file bytes, accepted file count, and
  accepted repository bytes with exact-boundary acceptance and stable diagnostics.
- [x] Added explicit tests for boundary equality, excluded-file accounting, deterministic
  aggregate stops, and root-ignore interaction.
- [x] M1.1D complete: implemented external file-symlink containment, lexical-path inclusion
  for contained links, and focused deterministic filesystem diagnostics before resource
  accounting.
- [x] Added platform-independent containment/failure tests plus real directory, external
  file, and contained file symlink integrations for Linux CI.
- [x] Linux GitHub Actions passed after push and verified the real directory, escaping-file,
  and contained-file symlink integrations skipped by the local Windows environment.
- [x] Closed Milestone 1.1 documentation and handed off to M1.2A without marking all of
  Milestone 1 complete.

### Milestone 1.2A — Basic Python definition extraction

- [x] Added a stateless `.py` extractor compatible with the existing `Extractor` protocol
  and `ExtractionResult` contract.
- [x] Derived deterministic module names for ordinary modules, package `__init__.py`, and
  root `__init__.py` without repository-name inference.
- [x] Extracted module, class, function, async-function, method, and nested-definition nodes
  with qualified names, AST spans, and existing stable IDs.
- [x] Added only nearest-parent syntax-direct `contains` edges; imports, calls, inheritance,
  graph building, and orchestration remain deferred.
- [x] Added deterministic syntax-error diagnostics with no partial AST facts.
- [x] Added manually authored tests for naming, classification, nesting, identities,
  containment, paths, spans, determinism, extensions, invalid syntax, and non-execution.
- [x] Completed the full M1.2A validation record; the developer learning checkpoint remains
  the handoff question for review.

### Milestone 1.2B — Unresolved Python import fact extraction

- [x] Added the missing generic unresolved-import fact contract and default-empty
  `ExtractionResult.imports` channel without changing graph models.
- [x] Collected one fact per `ast.alias` for direct, from, relative, aliased, multi-member,
  nested, repeated, and star imports.
- [x] Preserved nullable modules, relative levels, aliases, explicit star state, relative
  POSIX paths, and alias-level AST spans without resolution or execution.
- [x] Sorted facts deterministically without deduplication and preserved all M1.2A
  definition nodes and containment edges.
- [x] Added manual syntax expectations, contract-invariant tests, non-execution coverage,
  and the M1.2B learning questions.
- [x] Completed the full M1.2B validation record; the developer learning checkpoint remains
  the handoff question for review.

### Milestone 1.3A — In-memory repository graph assembly

- [x] Added a frozen top-level result containing a validated graph, unresolved imports,
  scanner diagnostics, and extractor/source-loading diagnostics.
- [x] Added deterministic repository, accepted-directory, and accepted-file nodes with
  portable stable IDs and syntax-direct structural containment.
- [x] Connected scanning to a fresh default Python registry, Python-aware source loading,
  extractor merging, and file-to-module containment without writing artifacts.
- [x] Preserved ignored/limited-file exclusion, unresolved import facts, invalid-source
  partial results, and focused read failures without blocking later files.
- [x] Added 21 focused tests covering all requested hierarchy, merge, diagnostics,
  determinism, integrity, encoding, limit, ignore, and non-execution behaviors.
- [x] Completed the full M1.3A validation record; the developer learning checkpoint remains
  the handoff question for review.

### Milestone 1.3B — CLI index and deterministic graph.json

- [x] Replaced the `index` placeholder with a Typer-validated repository argument and the
  existing M1.3A pipeline.
- [x] Added canonical complete-result serialization and validation while preserving the
  graph-only serialization API.
- [x] Resolved relative output under the repository, retained absolute configured output,
  created missing parents, and atomically replaced `graph.json`.
- [x] Kept file-level diagnostics non-fatal and serialized while invalid invocation,
  root-level, output, write, and unexpected pipeline failures exit non-zero.
- [x] Pruned the configured in-repository output directory before scanner descent and
  resource accounting without deleting preserved files.
- [x] Added focused CLI, serialization, scanner, determinism, failure, and non-execution
  tests and completed the full validation/manual-smoke record.

### Milestone 1.4A — Basic deterministic Markdown extraction

- [x] Added a `.md` extractor backed by constrained `markdown-it-py` CommonMark tokens.
- [x] Added one stable document node per Markdown file plus ATX/Setext section nodes and
  nearest-lower-level syntax-direct containment.
- [x] Added typed unresolved link, fenced-code, and inline-code facts with nearest-section
  association, deterministic occurrence order, and no target fabrication or execution.
- [x] Preserved block line maps honestly; document columns are exact while heading, link,
  fence, and inline child columns remain unavailable rather than guessed.
- [x] Registered Markdown through the existing extractor registry, added file-to-document
  containment, and included sorted Markdown facts in canonical `graph.json`.
- [x] Added focused extractor, indexer, and CLI coverage for hierarchy, syntax, ignore,
  determinism, path privacy, recovery, non-execution, and unchanged Python behavior.

### Milestone 1.4B — Deterministic project metadata extraction

- [x] Added exact-basename scanner eligibility without broad `.json` or `.toml` support.
- [x] Extended the extractor registry with deterministic exact-filename selection and
  precedence over extension matching.
- [x] Added typed source-path-only facts for allowlisted pyproject, package, and tsconfig
  fields without graph target, installation, or resolution claims.
- [x] Used `tomllib`, strict standard JSON, and constrained `json-with-comments` parsing;
  scripts, entry points, backends, dependencies, exports, and paths remain inert data.
- [x] Added scanner, registry, extractor, indexer, and CLI coverage for selection, fields,
  JSONC, diagnostics, limits, determinism, path privacy, and non-execution.

### Milestone 1.5 — Fixture gold and deterministic acceptance (complete)

- [x] Selected `python_service`, `markdown_documented_project`,
  `fullstack_fastapi_react`, and `typescript_frontend` for current M1 acceptance.
- [x] Added separate complete canonical `m1-graph.json` records without replacing the
  future resolver/query harness `gold.json` contracts.
- [x] Added an explicit check/update helper; ordinary tests and check mode never overwrite
  committed gold.
- [x] Added independently authored Python, Markdown, and metadata semantic expectations,
  full byte comparisons, meaningful unified differences, and model round-trip checks.
- [x] Added graph-integrity, path-privacy, output-pruning, controlled-enumeration,
  non-execution/network, partial-diagnostic, and fatal-root acceptance coverage.
- [x] Confirmed all M1.1–M1.5 slices and the complete Milestone 1 local acceptance contract.
- [x] Kept the three real-symlink tests as honest Windows privilege skips.
- [x] Repaired cross-platform acceptance on `fix/m1-linux-ci` by normalizing selected
  fixture/gold text to LF and correcting the contradictory absolute-path CLI test input.
- [x] Verified the complete M1 acceptance suite on Linux through PR #2 at commit
  `28ad7fab44fa08d66934dacf541f9b366db14673`; the required CI check passed.

### Milestone 2.1A — Tree-sitter foundation and basic JavaScript/TypeScript extraction (complete)

- [x] Locked tree-sitter 0.26.0, JavaScript grammar 0.25.0, and TypeScript grammar 0.23.2
  after real parser and ABI verification.
- [x] Added exactly `.js`/`.ts` discovery and one side-effect-free extractor for module,
  named function/async-function, class, ordinary method, and identifier-arrow nodes.
- [x] Added stable qualified names, column-disambiguated IDs, exact byte-oriented spans,
  nearest extracted-parent containment, and conservative partial-tree diagnostics.
- [x] Added typed unresolved ESM import/export channels and integrated them through the
  default registry, indexer, canonical serialization, and CLI counts without target edges.
- [x] Preserved every M1 gold byte with an explicit historical scan profile and added the
  separate TypeScript frontend `m2-1a-graph.json` partial snapshot.
- [x] Added focused extractor/scanner/indexer/CLI/security/determinism tests and completed
  the full offline validation plus two-run manual smoke. JSX/TSX and M2.1B remain open.
- [x] Final review fixes omit statement-level and inline type-only ESM syntax while retaining
  runtime specifiers in mixed clauses, and align the Pydantic floor with `exclude_if` at 2.12.

Learning checkpoint: explain runtime/grammar ABI compatibility; byte-column/end-coordinate
mapping; why ESM facts are not edges; why recoverable tree-sitter errors differ from a
failed Python AST parse; and why unsupported anonymous/namespace/generator scopes are
barriers rather than transparent containers. Also explain why erased TypeScript type-only
imports and exports must not be reported as runtime ESM facts.

### Milestone 2.1B — Bounded CommonJS, re-exports, and TypeScript declarations

- [x] Added frozen unresolved contracts and default-empty, conditionally omitted repository
  channels for CommonJS requires, CommonJS export assignments, and ESM re-exports.
- [x] Added exact top-level CommonJS structural matching, complete program-scope shadow and
  reassignment guards, and whole-file CommonJS suppression on partial parses.
- [x] Added named/star/namespace runtime re-exports with statement/specifier type-only
  filtering and no target lookup or graph edge.
- [x] Added direct module children for named interfaces, type aliases, and ordinary enums;
  ambient, `const enum`, namespace, nested, and other declaration forms remain absent.
- [x] Added an isolated M2.1B partial repository/gold and an explicit check/update helper;
  M1 gold remains unchanged and M2.1A uses only the reviewed additive test projection.
- [x] Completed the final offline validation, deterministic CLI smoke, documentation audit,
  and scope audit. M2.1B is complete; Milestone 2 remains open.
- [x] Independent final review repaired the runtime shadow audit and exact-shape boundaries,
  added focused regressions, and repeated the complete offline validation and scope audit.
- [x] PR #4's required Linux `check` job passed for implementation commit
  `b680592a25409f5c7bb0abe9f70b24459298c0d0` in workflow run `29776458604`; no next
  Milestone 2 slice has been selected.

Learning checkpoint: explain the boundary between exact CommonJS occurrence matching and
general call analysis; why runtime shadowing/reassignment and partial parses require
suppression while erased type-only names do not; why re-exports are unresolved facts rather
than edges; why interface/type declarations differ from ordinary enums at runtime; and how
empty-field omission plus the exact M2.1A projection preserve historical bytes without
hiding current production behavior.

### Milestone 2.2A — JSX/TSX foundation and conservative React components

- [x] Added exactly `.jsx` and `.tsx` discovery; `.jsx` uses the pinned JavaScript grammar,
  `.tsx` uses `language_tsx()`, and file/module/definition labels are `jsx`/`tsx`.
- [x] Reused the shared M2.1 visitor and unresolved ESM/CommonJS/re-export/type-declaration
  channels on the new suffixes without changing `.js` or `.ts` production behavior.
- [x] Added exact runtime React import evidence and conservative top-level named function,
  arrow, and class classification with direct JSX returns through parentheses/fragments.
- [x] Represented each match with one `react_component` node while retaining declaration
  spans, qualified names, containment, class methods, export facts, and deterministic IDs.
- [x] Added manually authored positive/negative grammar, classification, partial-tree,
  compatibility, security, privacy, non-execution, fixture, and determinism coverage.
- [x] Preserved all M1 gold and the isolated M2.1B repository/gold; M2.1A uses only its
  approved historical input profile and existing narrow additive projection. Added the
  TypeScript frontend `m2-2a-graph.json` partial gold and TaskPanel semantic assertions.
- [x] Completed independent final review, local Windows validation, and scope audit. The
  review rejected optional `render?()` methods from the ordinary class-component boundary
  and added a regression. No Linux verification is claimed; Milestone 2 remains open and
  M2.2B is untouched.

Learning checkpoint: explain why syntax that looks like JSX is insufficient to claim a
React component; how runtime import evidence, top-level shape, direct-return evidence, and
partial-tree safeguards bound false positives; why reclassification uses one node but
preserves containment/exports; and how the historical compatibility profiles prove old
bytes without filtering current production output.

## Milestone 2.2A validation record

Independently reviewed and validated locally on Windows on 2026-07-20 with Python 3.11.15.
Linux CI remains pending; this record makes no Linux claim.

- `uv lock --check --offline` and `uv sync --dev --locked` exited 0, resolving 30 packages
  and checking 29. No dependency declaration or lockfile changed.
- Ruff formatted/checked 53 files and lint passed; mypy found no issues in 36 source files.
- Focused suites passed: 35 M2.2A cases; 76 complete shared extractor cases; 35 scanner
  cases with 3 Windows symlink skips; 36 registry/extractor-contract cases; 30 indexer
  cases; 23 CLI cases; 8 model cases; 16 M1 acceptance cases; plus the individual M2.1A,
  M2.1B, and M2.2A compatibility/gold tests.
- Full pytest collected 313 tests: 310 passed and 3 skipped only because Windows returned
  symlink privilege error 1314. Total coverage was 93%; the shared JS/TS/JSX/TSX extractor
  reported 94%.
- Harness smoke validated 5 fixtures, 5 questions, and 5 diff cases. Doctor reported
  Python 3.11.15/package 0.1.0 healthy with no network requirement. All three M1, M2.1B,
  and M2.2A check-by-default gold helpers exited 0.
- M1 gold and the committed M2.1A/M2.1B partial gold remained byte-identical to base. The
  M2.1A compatibility test used only its historical `.jsx`/`.tsx` input exclusion plus the
  existing narrow M2.1B additive projection; the isolated M2.1B repository/helper/gold did
  not change.
- Two M2.2A partial-gold generations were byte-identical at 5,550 bytes with SHA-256
  `3bd24ab7c9d6f2356c3a9955b601f9a61084b58f336c6430ebb753bd19cd1a12`.
- Two disposable mixed `.js`/`.jsx`/`.ts`/`.tsx` CLI indexes were byte-identical with
  SHA-256 `bb5b7e530c0e5aeef0bc30a235393ea9ef791f2b2e1c191d8faccda1ab00eac1`:
  14 nodes, 13 containment edges, 3 ESM imports, 3 ESM exports, and the exact JSX/TSX
  components `View.View` and `Panel.Panel`. No absolute root, timestamp, forbidden semantic
  edge, or source-execution sentinel appeared.
- Independent final review reproduced the pinned TSX shape for `render?()`, fixed its
  false-positive class classification, and added a focused negative regression. The
  corrected focused and full suites produced the counts above.
- `make check` was attempted and exited 1 before execution because GNU Make is unavailable
  in this Windows shell. Its lock, format, lint, type-check, full-test, and harness
  constituents were run directly and passed. Final `git diff --check` exited 0.

The scope audit found no changes to dependencies, lockfiles, CI, graph models, base
contracts, serialization, MCP, calls, resolution, HTTP/routes, traversal, reporting, or
Milestone 3. Milestone 2 remains open; M2.2B was not selected or started.

## Milestone 2.1B validation record

Validated locally on Windows on 2026-07-20 with Python 3.11.15. This local record is kept
separate from the subsequent Linux GitHub Actions verification below.

- `uv lock --check --offline` resolved 30 packages; `uv sync --dev --locked` resolved 30
  and checked 29. No dependency declaration or lockfile changed.
- Ruff reported 51 files formatted and all lint checks passed. Mypy reported no issues in
  35 source files.
- Focused suites passed: 44 selected M2.1B cases; 78 complete JS/TS extractor cases; 8
  model cases; 30 indexer cases; 22 CLI cases; 16 M1 acceptance cases; and the individual
  M2.1A projection and M2.1B partial-gold cases.
- Full pytest collected 279 tests: 276 passed and 3 skipped only because Windows returned
  symlink privilege error 1314. Total coverage was 93%; the JS/TS extractor reported 94%.
- Harness smoke validated 5 fixtures, 5 questions, and 5 diff cases. Doctor reported
  Python 3.11.15/package 0.1.0 healthy and no network requirement.
- The M1 checker matched all 4 unchanged gold files. The M2.1A test removed only the three
  additive node kinds, their containment edges, and the three M2.1B fact channels before
  matching every historical canonical byte. The committed `m2-1a-graph.json` was unchanged.
- Two M2.1B partial-gold generations were byte-identical at 6,192 bytes with SHA-256
  `bc5d0eab6684fdd27f6bdb66252bb2958ebc0c9750b818a0fc2151cf353a445e`.
- Two disposable CLI indexes produced the same hash, 10 nodes, 9 edges, 2 CommonJS require
  facts, 2 CommonJS export facts, 5 ESM re-export facts, and no warnings. The temporary
  absolute repository path was absent from JSON and the source non-execution sentinel was
  not created.

PR #4 Linux CI closeout on 2026-07-20:

- The required Linux `check` job passed for implementation commit
  `b680592a25409f5c7bb0abe9f70b24459298c0d0` in workflow run `29776458604`.
- The job completed successfully in 18 seconds; its exact record is
  https://github.com/weeelin98/RepoLens/actions/runs/29776458604/job/88466891502.
- The three symlink skips above remain accurately scoped to the local Windows privilege
  limitation. M2.1B is complete and Linux CI verified; Milestone 2 remains open, with no
  next slice selected.

## Milestone 2.1A validation record

Validated locally on 2026-07-17 from the repository root with Python 3.11.15:

- Locked sync resolved 30 packages and checked 29. Ruff formatting/check and full lint
  passed. Mypy reported no issues in 35 source files.
- Focused suites passed: JS/TS extractor 29; existing extractors 36; scanner 35 plus 3
  Windows error-1314 real-symlink skips; indexer 29; CLI 21; M1 acceptance 16.
- Full pytest passed 224 tests, retained the same 3 Windows symlink skips, and reported 93%
  total coverage. `javascript_typescript.py` reported 96% coverage.
- Harness smoke validated 5 fixtures, 5 questions, and 5 diff cases. Doctor reported
  Python 3.11.15/package 0.1.0 healthy and no network requirement.
- Two isolated CLI runs produced byte-identical SHA-256
  `655dd2d175619d192c0befcc9a32e2cac719f507c29aa5dd67a0dae7bd185e45`, with 13 nodes,
  12 edges, 1 ESM import, 2 ESM exports, and 1 expected syntax diagnostic. `.tsx` was
  excluded and the temporary absolute repository path did not enter JSON.
- All four M1 gold outputs stayed byte-identical; the separate TypeScript frontend M2.1A
  partial gold matched. Milestone 2 remains open; the next proposed slice is M2.1B.

Final pre-commit review fixes were validated locally on 2026-07-17 with Python 3.11.15:

- `uv lock --offline` and `uv lock --check --offline` resolved 30 packages; Pydantic remained
  locked at 2.13.4 under the corrected `>=2.12,<3` runtime range.
- The JS/TS extractor suite passed 36 tests. Full pytest passed 231 tests with the same 3
  Windows error-1314 symlink skips, 93% total coverage, and 96% extractor coverage.
- Ruff format check, Ruff lint, Mypy, M1 acceptance, the four-fixture M1 gold checker,
  harness-smoke, and doctor passed.
- Two CLI indexes of a scratch TypeScript fixture produced byte-identical SHA-256
  `974a462e02b18f82d3fbcb0067b302cbbaa9b1aaceaa3b2cd7e00398d533a817`; no absolute scratch
  path entered JSON. This is local Windows validation, not Linux CI verification.

## Milestone 1.5 validation record

Validated locally on 2026-07-17 from the repository root with Python 3.11.15:

- Locked sync resolved 27 packages and checked 26.
- Ruff format left 48 files unchanged; format check and lint passed.
- Mypy reported no issues in 33 source files.
- Focused suites passed: M1 acceptance 12; scanner 33 plus 3 Windows real-symlink skips;
  extractors 36; Markdown 24; metadata 17; indexer 24; CLI 19.
- Full pytest passed 182 tests, skipped the same 3 real-symlink integrations because
  Windows returned privilege error 1314, and reported 92% total coverage.
- Harness smoke validated 5 fixtures, 5 questions, and 5 diff cases. Doctor reported
  package 0.1.0 healthy and no network requirement. All 4 committed M1 gold files matched.
- Repeated CLI hashes matched per fixture: `python_service`
  `00fbfa010fdf255f4438dc84606eab8c9af30c8bc41c8c81400a7f9aee11fdab`;
  `markdown_documented_project`
  `6b313491589c5e3bba0cf071ac6043baa8396070a68440e1d3d6cd3d2761d574`;
  `fullstack_fastapi_react`
  `8af42c916a3ede5fc68386fd76e9e7525c335cfb7c7c6d53a995b078fa18b9c4`;
  `typescript_frontend`
  `761554305f6e4d06cf6329569e30c5292c7ff4ec90762438ec9675e1b7c8d549`.
- `git diff --check` passed. GNU Make was not invoked, so this record does not claim
  `make check` ran.

PR #1 was merged before its CI completed. Its Linux run then failed five pytest cases: four
M1 gold byte comparisons reflected Windows CRLF fixture sizes rather than Linux LF sizes,
and one CLI non-execution test contradicted its own absolute-path assertion by embedding
the temporary repository path in package-script input. Production behavior was not the
cause.

PR #2 (`fix/m1-linux-ci`) repaired those cross-platform test inputs. At repair commit
`28ad7fab44fa08d66934dacf541f9b366db14673`, GitHub Actions workflow run `29590342724`
completed successfully: its required `check` job passed `make check` and
`uv run repolens doctor`. The complete Milestone 1 acceptance suite therefore passed on
Linux. Historical M1.1 Linux CI also remains the real-symlink integration evidence that
the local Windows privilege limitation cannot provide.

## Milestone 1.4B validation record

Validated locally on 2026-07-17 from the repository root with Python 3.11.15:

- `uv sync --dev --locked` — exit 0; 27 packages resolved and 26 checked.
- `uv run ruff format .` — exit 0; 46 files left unchanged.
- `uv run ruff format --check .` — exit 0; 46 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 32 source files.
- Metadata extractor tests — 17 passed; metadata extractor coverage 94%.
- Markdown extractor tests — 24 passed; Markdown extractor focused coverage 92%.
- Existing extractor tests — 36 passed; Python extractor coverage 97%, registry 95%.
- Indexer tests — 24 passed; indexer coverage 93%.
- CLI tests — 19 passed; CLI coverage 84%.
- Additional scanner tests — 33 passed and 3 Windows real-symlink integrations skipped;
  scanner coverage 96%.
- Full `uv run pytest` — 170 passed and the same 3 scanner integrations skipped because
  Windows returned symlink privilege error 1314; total coverage 92%, metadata extractor
  coverage 94%, and serialization coverage 100%.
- Harness smoke — 5 fixtures, 5 questions, and 5 diff cases valid.
- Doctor — Python 3.11.15 and package 0.1.0 healthy; no network required.
- `git diff --check` — exit 0; no whitespace errors.
- `git status --short` — exactly 20 planned M1.4B paths modified or untracked.

The manual temporary-repository smoke indexed the three supported manifests plus arbitrary
JSON/TOML twice. Both runs reported 3 files, 4 nodes, 3 edges, 0 imports, and 0 warnings.
Ten facts came only from the supported basenames; arbitrary values and absolute paths were
absent, the package script did not execute, bytes matched, and the output ended with a
newline. The verified temporary repository was removed.

GNU Make is unavailable in the documented Windows shell. This record does not claim
`make check` ran. The three skips remain M1.1 Windows symlink-privilege limitations; every
M1.4B test ran and passed.

## Milestone 1.4A validation record

Validated locally on 2026-07-17 from the repository root with Python 3.11.15:

- `uv sync --dev --locked` — exit 0; 26 packages resolved and 25 packages checked.
- `uv run ruff format .` — exit 0; 44 files left unchanged.
- `uv run ruff format --check .` — exit 0; 44 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 30 source files.
- `uv run pytest tests/test_markdown_extractor.py -v` — exit 0; 24 passed; Markdown
  extractor coverage was 93%.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 34 passed; Python extractor
  coverage was 96%.
- `uv run pytest tests/test_indexer.py -v` — exit 0; 21 passed; indexer coverage was 92%.
- `uv run pytest tests/test_cli.py -v` — exit 0; 17 passed; CLI coverage was 84%.
- `uv run pytest` — exit 0; 144 passed and 3 existing scanner integrations skipped
  because Windows returned symlink privilege error 1314; total coverage was 92%, Markdown
  extractor coverage was 93%, and complete-result serialization coverage was 100%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.
- `git diff --check` — exit 0; no whitespace errors.
- `git status --short` — exactly 13 planned M1.4A paths were modified or untracked.

The manual Markdown fixture smoke indexed
`harness/fixtures/markdown_documented_project` twice. Both runs reported 2 files, 11 nodes,
10 edges, 0 unresolved imports, and 0 warnings. Inspection found 1 Markdown document, 3
sections, 3 Markdown hierarchy edges, and `inline_code`, `link`, and `fenced_code` facts.
The output was byte-identical, contained no absolute fixture path, ended with a newline,
and the generated output directory was removed afterward.

GNU Make is unavailable in the documented Windows shell. This record does not claim
`make check` ran. The three skips are unchanged M1.1 Windows symlink-privilege limitations;
every M1.4A test ran and passed.

## Milestone 1.3B validation record

Validated locally on 2026-07-16 from the repository root with Python 3.11.15:

- `uv run ruff format .` — exit 0; the final run reformatted 1 file and left 41 unchanged.
- `uv run ruff format --check .` — exit 0; 42 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 28 source files.
- `uv run pytest tests/test_cli.py -v` — exit 0; 16 passed; CLI coverage was 84%.
- `uv run pytest tests/test_indexer.py -v` — exit 0; 21 passed; indexer coverage was 92%.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 34 passed; Python extractor
  coverage was 96%.
- `uv run pytest tests/test_scanner.py -v` — exit 0; 31 passed and 3 existing real-symlink
  integrations skipped because Windows returned privilege error 1314; scanner coverage was
  96%.
- `uv run pytest` — exit 0; 119 passed and the same 3 scanner integrations skipped; total
  coverage was 92%, complete-result serialization coverage was 100%, CLI coverage was 84%,
  and indexer coverage was 92%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.
- `git diff --check` — exit 0; only LF-to-CRLF working-copy warnings were printed for six
  modified tracked files.
- `git status --short` — exactly the ten planned M1.3B paths were modified or untracked.

The manual temporary-repository smoke ran `uv run repolens index <path>` twice. Both runs
reported 2 files, 5 nodes, 4 edges, 1 unresolved import, and 0 warnings. `graph.json` parsed
with zero diagnostics, the two byte sequences were identical, no absolute repository path
appeared in the JSON, and the file ended with a newline. The verified temporary directory
was removed afterward.

GNU Make is unavailable in the documented Windows shell. This record does not claim
`make check` ran. The three skips are unchanged M1.1 Windows symlink-privilege limitations;
every M1.3B test ran and passed.

## Milestone 1.3A validation record

Validated locally on 2026-07-16 from the repository root with Python 3.11.15:

- `uv run ruff format .` — exit 0; 42 files left unchanged.
- `uv run ruff format --check .` — exit 0; 42 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 28 source files.
- `uv run pytest tests/test_indexer.py -v` — exit 0; 21 passed; the indexer module
  reported 92% coverage.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 34 passed; the import contract
  reported 100% coverage and the Python extractor reported 96% coverage.
- `uv run pytest tests/test_scanner.py -v` — exit 0; 30 passed and 3 existing real-symlink
  integrations skipped because Windows returned privilege error 1314; scanner coverage was
  97%.
- `uv run pytest` — exit 0; 105 passed and the same 3 scanner integrations skipped; total
  coverage was 92% and indexer coverage was 92%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.
- `git diff --check` — exit 0; only LF-to-CRLF working-copy warnings were printed for
  `CODEX.md`, `README.md`, and `docs/INTERVIEW_QUESTIONS.md`.
- `git status --short` — exactly the six planned M1.3A paths were modified or untracked.

GNU Make is unavailable in the documented Windows shell. This record does not claim
`make check` ran. The three skips are unchanged M1.1 Windows symlink-privilege limitations;
every M1.3A indexer test ran and passed.

## Milestone 1.2B validation record

Validated locally on 2026-07-16 from the repository root with Python 3.11.15:

- `uv run ruff format .` — exit 0; 40 files left unchanged.
- `uv run ruff format --check .` — exit 0; 40 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 26 source files.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 34 passed; import-fact contract
  coverage was 100% and the Python extractor module reported 96% coverage.
- `uv run pytest` — exit 0; 84 passed and 3 existing real-symlink scanner integrations
  skipped because Windows returned privilege error 1314; total coverage was 92%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.
- `git diff --check` — exit 0; only LF-to-CRLF working-copy warnings were printed.

GNU Make was not invoked and this record does not claim `make check` ran. The three skipped
tests are unchanged M1.1 Windows symlink-privilege limitations, not import extractor skips.

## Milestone 1.2A validation record

Validated locally on 2026-07-16 from the repository root with Python 3.11.15:

- `uv run ruff format .` — exit 0; 40 files left unchanged.
- `uv run ruff format --check .` — exit 0; 40 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 26 source files.
- `uv run pytest tests/test_extractors.py -v` — exit 0; 17 passed; the Python extractor
  module reported 96% coverage.
- `uv run pytest` — exit 0; 67 passed and 3 existing real-symlink scanner integrations
  skipped because Windows returned privilege error 1314; total coverage was 92%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases were
  valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy; no
  network is required.
- `git diff --check` — exit 0; only LF-to-CRLF working-copy warnings were printed.

GNU Make was not invoked and this record does not claim `make check` ran. The three skipped
tests are unchanged M1.1 Windows symlink-privilege limitations, not Python extractor skips.

## Milestone 0 validation record

Validated on 2026-07-15 from the repository root with Python 3.11.15:

- `uv run ruff format --check .` — exit 0; `37 files already formatted`.
- `uv run ruff check .` — exit 0; `All checks passed!`.
- `uv run mypy src tests` — exit 0; `Success: no issues found in 23 source files`.
- `uv run pytest` — exit 0; 23 tests passed in 0.29 seconds; total coverage was 87%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff
  cases were valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy;
  no network is required.

The `make check` aggregate could not start in the validation shell because GNU Make was
not installed. Its five underlying commands are the first five commands recorded above;
each was run directly and passed. This record does not claim that `make check` itself ran.

## Milestone 1.1 contracts-only validation record

Validated on 2026-07-16 from the repository root with Python 3.11.15:

- `uv run ruff format --check .` — exit 0; `39 files already formatted`.
- `uv run ruff check .` — exit 0; `All checks passed!`.
- `uv run mypy src tests` — exit 0; no issues in 25 source files.
- `uv run pytest` — exit 0; 25 tests passed normally, 12 strict M1.1 tests xfailed,
  and 2 symlink tests skipped in 0.35 seconds; total coverage was 89%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff
  cases were valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15 and package 0.1.0 were healthy;
  no network is required.
- `git diff --check` — exit 0; only line-ending conversion warnings were printed.

The 25 normal passes include all 23 pre-existing Milestone 0 tests. This run deliberately
does not implement scanner traversal, ignore matching, symlink handling, or resource-limit
behavior. The 12 reachable behavioral tests remain strict xfails until the developer
implements their phases. Windows error 1314 prevented creation of both test symlinks, so
those tests skipped safely. GNU Make was not invoked; this record does not claim
`make check` ran.

## Milestone 1.1A validation record

Validated on 2026-07-16 from the repository root with Python 3.11.15:

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

GNU Make was not invoked; this record does not claim `make check` ran. The xfails remain
for root ignore/negation, all three resource limits, and—on a link-capable platform—the
escaping file-symlink contract. Windows error 1314 caused both symlink tests to skip before
their scanner assertions.

## Milestone 1.1C validation record

Validated on 2026-07-16 from the repository root with Python 3.11.15:

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

GNU Make was not invoked; this record does not claim `make check` ran. The three resource
limit tests remain strict xfails in the local checkout. Both symlink tests skipped because
Windows returned error 1314 before their scanner assertions.

## Milestone 1.1B validation record

Validated on 2026-07-16 from the repository root with Python 3.11.15:

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

GNU Make was not invoked; this record does not claim `make check` ran. Both symlink tests
skipped because Windows returned error 1314 before their scanner assertions. The escaping
file-symlink test remains strict xfail on platforms that can create the link.

## Milestone 1.1D validation record

Validated locally on 2026-07-16 from the repository root with Python 3.11.15:

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

Windows error 1314 prevented creation of the real directory, escaping-file, and
contained-file symlinks. Platform-independent focused tests passed for each decision path;
Linux GitHub Actions subsequently passed after push and verified all three integrations
against real symlinks. GNU Make is not installed in this shell, so this record does not
claim `make check` ran.

## Discovery and surprise log

- **2026-07-17:** TypeScript class declarations expose `type_identifier` names while the
  JavaScript grammar exposes `identifier`; the inherited visitor therefore missed all TS
  classes until both shapes were handled.
- **2026-07-17:** Generic traversal crossed bare TypeScript namespace/module and JavaScript
  generator scopes, incorrectly promoting nested declarations to the module. Explicit
  barriers now keep unsupported relationships unresolved rather than fabricating parents.
- **2026-07-17:** Pydantic 2.13.4 field-level `exclude_if` preserves legacy canonical JSON
  by omitting empty ESM channels while still parsing old output into default-empty tuples.
- **2026-07-14:** The configured workspace path did not yet exist; it was created before
  repository initialization, so there were no useful existing files to preserve.
- **2026-07-14:** System Python is 3.9.6, below the project floor, while `uv` 0.7.18 is
  available. The project will let uv provision/use Python 3.11+ rather than weakening the
  requirement.
- **2026-07-14:** GitHub CLI is absent. GitHub remote creation must use the connected plugin
  if it exposes repository creation, or install/authenticate `gh` as an explicit external
  step; local Milestone 0 work remains unblocked.
- **2026-07-15:** The six requested validation commands passed when run independently. The
  harness contains five valid fixtures, five questions, and five diff cases; the test suite
  contains 23 passing tests and reports 87% total coverage.
- **2026-07-15:** GNU Make is absent from the Windows validation shell, so `make check`
  could not start. Each command in its Makefile target was run directly and passed.
- **2026-07-16:** The initiating request named branch `Python-definition-extractor`, but
  Git reported the only local/current branch as `main`. No branch was silently created or
  switched.
- **2026-07-16:** `pathspec` appears transitively in `uv.lock` but is not declared in
  `pyproject.toml`; production ignore matching must declare it directly when implemented.
- **2026-07-16:** Windows denied both test symlink creations with error 1314. The two tests
  skipped safely, while non-symlink behavioral contracts remained strict xfails.
- **2026-07-16:** At M1.1A start, Git reported the requested
  `Python-definition-extractor` branch. This differed from the earlier contracts-only
  observation of `main`; Codex did not create or switch branches.
- **2026-07-16:** The focused scanner suite passed 11 tests, retained 4 strict xfails for
  later behavior, and skipped 2 symlink cases because Windows denied link creation. The
  scanner module reported 91% coverage in the focused run.
- **2026-07-16:** The M1.1C prompt described M1.1B resource limits as complete, but the local
  scanner had no enforcement and all three tests remained strict xfails. This slice did not
  implement or alter limit behavior.
- **2026-07-16:** Offline lock regeneration failed because metadata for all supported Python
  splits was not cached. Approved online resolution succeeded. Pathspec 1.1.1 deprecated
  the old `gitwildmatch` factory name, so RepoLens uses its current `gitignore` factory for
  the required Git-compatible semantics.
- **2026-07-16:** M1.1B was implemented after M1.1C in this worktree. The focused resource
  suite passed all 24 reachable scanner tests, skipped 2 Windows symlink cases, and reported
  96% scanner coverage.
- **2026-07-16:** Windows error 1314 prevented all three real-symlink integrations from
  creating links. Platform-independent focused tests exercise directory pruning, internal
  and external containment, broken-link resolution, permission failures, and ordinary
  metadata failures locally. Linux GitHub Actions later passed after push and verified the
  real filesystem integrations.
- **2026-07-16:** The `python_service` harness gold contains future readable IDs plus
  call/test resolver edges. M1.2A leaves it unchanged because isolated definition extraction
  neither assembles snapshots nor resolves relationships; harness validation still passes.
- **2026-07-16:** M1.2A focused tests passed all 17 cases and reported 96% coverage for the
  new extractor. The full suite passed 67 tests, retained the 3 existing Windows symlink
  skips, and reported 92% total coverage.
- **2026-07-16:** The extraction contract promised unresolved syntax facts but had no result
  field for them. M1.2B added one generic `imports` channel instead of misusing graph edges
  or creating a Python-only duplicate model.
- **2026-07-16:** Concurrent focused/full pytest startup contended for `.coverage` on
  Windows and one process failed with error 32. Sequential reruns passed; final validation
  therefore ran pytest commands sequentially.
- **2026-07-16:** M1.2B focused tests passed all 34 cases with 100% import-contract and 96%
  Python-extractor coverage. The full suite passed 84 tests, retained the 3 existing Windows
  symlink skips, and reported 92% total coverage.
- **2026-07-16:** M1.3A focused tests passed all 21 cases with 92% indexer coverage. The
  full suite passed 105 tests, retained the same 3 Windows scanner-symlink skips, and
  reported 92% total coverage. No M1.3A test was skipped, and the final worktree contained
  exactly the six planned paths.
- **2026-07-16:** M1.3B focused CLI tests passed all 16 cases, the full suite passed 119
  tests with the same 3 Windows scanner-symlink skips, and total coverage remained 92%.
  A manual two-run CLI smoke produced byte-identical complete JSON without an absolute
  repository path; the final worktree contained exactly the ten planned paths.

## Final portfolio deliverables

- Installable typed Python package and documented CLI/MCP service architecture.
- Five synthetic, understandable fixture repositories with committed gold expectations.
- Deterministic graph, overview, context, and impact examples from measured releases.
- Reproducible evaluation/baseline commands and honest failure analysis.
- Architecture, decision, security, limitations, and clean-room reference documentation.
- A short demo tracing the React-to-FastAPI-to-data flow and a Git change impact.
- Interview questions and developer-written learning explanations for every milestone.
