# Milestone 2.1B — Bounded CommonJS, ESM Re-exports, and TypeScript Declarations

## Purpose and user-visible outcome

`repolens index PATH` will preserve a deliberately small set of additional direct
JavaScript/TypeScript syntax facts: top-level literal CommonJS `require` and export
assignments, static ESM re-exports, and named module-level TypeScript interfaces, type
aliases, and ordinary enums. The slice remains extraction-only. It will not resolve a
module specifier, infer a runtime target, execute source, or create `imports`/`exports`
graph edges.

This ExecPlan is the review boundary for M2.1B. Creating it does not authorize JSX/TSX,
calls, resolution, traversal, rendering, React, HTTP, impact, or MCP work.

## Scope and non-goals

### Exact supported CommonJS syntax

Only direct children of the program root are eligible. Module specifiers must be nonempty
ordinary quoted string literals; template strings, concatenation, interpolation, and
computed values are excluded.

- `require("setup");` produces one side-effect require fact.
- `const client = require("pkg");`, `let client = require("pkg");`, and
  `var client = require("pkg");` produce one simple-binding require fact.
- Multiple eligible simple declarators in one top-level declaration each produce their own
  fact.
- `module.exports = client;` produces one whole-module export-assignment fact.
- `exports.client = client;` and `module.exports.client = client;` each produce one named
  export-assignment fact.
- The CommonJS callee/receivers must be bare identifiers with the exact case-sensitive
  spellings `require`, `module`, and `exports`; the export right-hand side must be one
  simple identifier; the assignment operator must be plain `=`; and named export
  properties must be ordinary noncomputed property identifiers.
- Facts describe source occurrences, not a final runtime export table. Repeated or
  conflicting assignments remain separate occurrences and are not collapsed.

Before emitting CommonJS facts, perform a complete error-free program-level ambiguity
check. Suppress facts using `require`, `module`, or `exports` when that name has a direct
program-scope import/declaration binding or bare reassignment. A syntax error prevents a
complete shadow check, so CommonJS facts are suppressed for that file while existing
M2.1A safe-subtree extraction and diagnostics continue.

### Exact supported ESM re-export syntax

- `export { value } from "pkg";` preserves imported `value` and exported `value`.
- `export { value as alias } from "pkg";` preserves imported `value` and exported `alias`.
- `export { default as value } from "pkg";` preserves imported `default` and exported
  `value`.
- `export * from "pkg";` produces one star re-export fact.
- `export * as namespace from "pkg";` produces one namespace re-export fact.
- `export type { Type } from "pkg";` and `export type * from "pkg";` produce no runtime
  fact.
- Inline type-only specifiers such as `export { type Type } from "pkg";` are omitted.
- Mixed clauses such as `export { value, type Type } from "pkg";` retain only the runtime
  `value` specifier.
- Source modules must use the same bounded nonempty static-string policy as supported ESM
  imports. No target lookup or graph edge is created.

### Exact selected TypeScript declarations

Only named declarations directly contained by the program, or directly wrapped by a
top-level `export_statement`, are supported:

- `interface User { ... }` becomes a node with new kind `interface`.
- `type UserId = string | number;` becomes a node with new kind `type_alias`.
- `enum Status { Ready, Done }` becomes a node with new kind `enum`.
- `export interface`, `export type`, and `export enum` use the same declaration-node rules.
  Interfaces and type aliases do not create runtime ESM export facts. An ordinary exported
  enum creates the existing direct declaration export fact because it has a runtime
  binding.
- Generic parameters, extends clauses, type expressions, interface members, and enum
  members remain part of the declaration span only. They do not become separate nodes,
  relationships, or signatures.
- New declaration nodes are direct children of the file module. Their qualified names are
  `<module>.<name>`.

### Explicit unsupported syntax

- `.jsx`, `.tsx`, `.mjs`, and `.cjs`; scanner support remains exactly `.js` and `.ts`.
- JSX/TSX, React classification, callbacks, object methods, generators, constructors,
  accessors, anonymous default definitions, destructuring arrows, and broader definition
  inference.
- General call extraction. `require(...)` is recognized only inside the exact top-level
  forms above; nested require calls, calls used as arguments, chained property access such
  as `require("pkg").value`, and dynamic `import()` remain unsupported.
- CommonJS destructuring bindings, property bindings, default values, object-literal
  exports, anonymous/function/class expression exports, chained assignments, computed
  properties, string-named properties, `Object.defineProperty`, `__esModule`, conditional
  or nested assignments, and `exports = ...` alias manipulation.
- Node-specific forms `module.require`, `require.resolve`, `require.cache`, and global
  aliases.
- TypeScript `import name = require("pkg")` and `export = name`.
- Export attributes/assertions, proposal syntax, source-phase imports, and dynamic module
  names.
- Ambient or `declare` declarations, declaration-file special handling, `const enum`,
  namespaces/internal modules, external module declarations, global augmentation,
  abstract classes, function/method overload signatures, index signatures as nodes,
  decorators, and declaration merging semantics.
- Import/export resolution, external-dependency nodes, `imports`/`exports` graph edges,
  calls, inheritance, target candidates, confidence heuristics, graph traversal, overview,
  context, impact, HTTP/React behavior, or MCP.

## Current state

- PR #3 is merged. On 2026-07-17 local `main`, `origin/main`, and `HEAD` were synchronized
  at merge commit `6e3137e4effceb730ee00464a970c530c76061a4`; the working tree was clean before this
  plan was created.
- M2.1A pins tree-sitter runtime 0.26.0, JavaScript grammar 0.25.0, and TypeScript grammar
  0.23.2. Those dependencies and `.js`/`.ts` scanner eligibility are sufficient for this
  slice; no dependency or lockfile change is expected.
- `src/repolens/extractors/javascript_typescript.py` already builds one module, extracts a
  bounded definition set, preserves unresolved ESM imports/direct exports, treats erroneous
  and unsupported scopes as barriers, and sorts every returned collection.
- `ExtractionResult` and `RepositoryIndexResult` have separate default-empty ESM channels.
  Repository serialization uses Pydantic `exclude_if`, so absent post-M1 channels do not
  change historical JSON.
- `NodeKind` has no honest values for interface, type alias, or enum. Reusing `class` or
  `data_model` would conflate distinct syntax and is not permitted by this plan.
- The pinned TypeScript grammar exposes `interface_declaration`,
  `type_alias_declaration`, and `enum_declaration`. A `const enum` is also an
  `enum_declaration` but has an unnamed `const` child, so it needs an explicit exclusion.
- Re-exports are `export_statement` nodes with a `source` field. Named clauses contain
  `export_specifier` nodes, namespace exports contain `namespace_export`, and star exports
  expose an unnamed `*` token. Statement-level and inline type-only forms expose unnamed
  `type` tokens, matching the established M2.1A filtering policy.
- CommonJS forms parse as ordinary `call_expression` and `assignment_expression` nodes.
  Exact top-level structural matching is therefore required to avoid silently becoming a
  general call or data-flow extractor.
- `harness/fixtures/typescript_frontend/repo/src/api.ts` already contains
  `export type Profile = ...`. Normal M2.1B indexing will add a type-alias node, so the
  historical M2.1A partial gold must remain immutable while a new M2.1B gold records the
  additive result.

## Acceptance criteria

1. Scanner and registry support remain exactly `.js` and `.ts`; no dependency declaration
   or locked version changes.
2. Every exact CommonJS form listed above produces one typed unresolved occurrence with a
   normalized repository-relative path and exact source span, and produces no graph import
   or export edge.
3. Unsupported, nested, dynamic, destructuring, computed, chained, or ambiguous CommonJS
   forms produce no fact and do not crash indexing.
4. Program-scope binding/reassignment of `require`, `module`, or `exports` suppresses only
   facts that rely on that ambiguous name. CommonJS facts are suppressed on a partial
   parse because a safe whole-program shadow audit is unavailable.
5. Named, aliased, default-named, star, and namespace ESM re-exports produce typed
   unresolved re-export facts with their source module and narrow spans. They produce no
   target nodes or edges.
6. Statement-level and inline type-only re-exports produce no fact; a mixed clause retains
   all and only runtime specifiers in source order before canonical sorting.
7. Named module-level interfaces, type aliases, and ordinary enums become `interface`,
   `type_alias`, and `enum` nodes with exact declaration spans, direct module containment,
   stable qualified names, and no fabricated member nodes.
8. Ambient declarations, `const enum`, namespaces, nested declarations, overloads, and all
   other TypeScript declarations remain absent. Valid unsupported syntax produces no
   diagnostic.
9. `export interface` and `export type` create declaration nodes but no runtime direct
   export fact. `export enum` creates its enum node plus the existing direct declaration
   export fact. Explicit type-only ESM facts remain omitted.
10. New node IDs derive only from the existing versioned namespace, new node kind,
    normalized repository-relative path, qualified name, declaration start line, and start
    column. Duplicate/merged names remain distinct by position and do not depend on parser
    traversal order.
11. New facts sort explicitly by path, position, kind, module/name fields, and stable
    tie-breakers. Repeated extraction, reversed discovery, model round-trip, and two CLI
    runs are byte-identical and contain no absolute temporary path, timestamps, or
    environment-dependent bytes.
12. `ExtractionResult` and `RepositoryIndexResult` parse missing new channels as empty.
    Empty CommonJS/re-export channels are omitted by production serialization, not by
    test-only JSON filtering. M1 and M2.1A output without new behavior gains no empty keys.
13. All four M1 gold files and `m2-1a-graph.json` remain byte-identical. A narrowly defined
    test-only M2.1A projection removes only the three new node kinds, their containment
    edges, and new M2.1B channels before comparing every remaining byte with historical
    M2.1A gold. Production indexing always uses the normal current pipeline.
14. A separate M2.1B partial repository/gold covers CommonJS, re-exports, all three selected
    declarations, type-only filtering, unsupported neighbors, exact spans, stable IDs,
    ordering, path privacy, and non-execution without changing the five-fixture harness
    manifest contract.
15. Focused tests, all historical tests, M1 gold check, M2.1A compatibility projection,
    M2.1B gold check, harness smoke, doctor, coverage, and the complete offline validation
    command set pass. No Linux success is claimed until GitHub Actions runs after a later
    reviewed implementation PR.

## Milestone phases

### Phase 1 — Behavioral tests and contract proof

Add manually authored failing tests for exact supported/unsupported forms, contract
validation, shadow ambiguity, type-only filtering, spans, IDs, ordering, partial parses,
non-execution, and serialization. Use the locked parsers to record any grammar-shape
surprise in this plan before changing production code.

Expected paths: `tests/test_javascript_typescript_extractor.py`, `tests/test_models.py`,
`tests/test_indexer.py`, and `tests/test_cli.py`.

### Phase 2 — Additive typed contracts

Add frozen enums/models for CommonJS requires, CommonJS export assignments, and ESM
re-exports in `src/repolens/extractors/base.py`; export them from
`src/repolens/extractors/__init__.py`; add three default-empty extraction/index channels;
and add `INTERFACE`, `TYPE_ALIAS`, and `ENUM` to `NodeKind`.

Repository fields must use production `exclude_if` behavior for empty tuples. Model
validators must reject inconsistent kind/name combinations and absolute or parent paths.
The nested graph `schema_version` remains 1: node-kind additions and default-empty
repository fact channels are additive within the current pre-1.0 index contract and do not
alter old payload bytes. Record this compatibility consequence in `CODEX.md`.

### Phase 3 — Conservative extractor implementation

Extend the existing visitor rather than adding a second parser. Perform an error-free
program-level CommonJS ambiguity prepass, then match only the exact top-level call,
declarator, and assignment shapes. Extend `export_statement` handling with a separate
re-export path and established type-token filtering. Add only top-level declaration
recognizers for interfaces, type aliases, and non-const enums.

Reuse current path normalization, source decoding, source-span conversion, containment,
partial-error diagnostic, and stable-ID helpers. Do not add a resolver, symbol table,
general expression walker, or graph edge.

Expected production paths:

- `src/repolens/models.py`
- `src/repolens/extractors/base.py`
- `src/repolens/extractors/__init__.py`
- `src/repolens/extractors/javascript_typescript.py`
- `src/repolens/indexer.py`
- `src/repolens/cli.py` only to include CommonJS require facts in the existing aggregate
  `imports=` success count

No scanner, resolver, graph traversal, `pyproject.toml`, or `uv.lock` edit is expected.

### Phase 4 — Compatibility and partial gold

Keep the existing five harness manifests, fixture repositories, four M1 gold files, and
`harness/fixtures/typescript_frontend/m2-1a-graph.json` unchanged. Add isolated source under
`harness/fixtures/typescript_frontend/m2-1b-repo/` and a sibling
`m2-1b-graph.json`. This is an explicit partial-slice fixture used by focused acceptance;
it does not claim that the TSX frontend fixture is fully supported.

Add a check-by-default, explicit-`--update` helper for M2.1B gold rather than extending or
weakening the historical M1 updater. The update path must write LF UTF-8 with one final
newline and must be safe to rerun. Tests must assert committed gold has no absolute paths,
timestamps, platform line endings, nondeterministic order, or empty legacy channels.

The M2.1A compatibility helper is test-only and operates on validated models before
canonical serialization. It may remove exactly new M2.1B node kinds, containment edges to
those nodes, and the three new fact channels. It may not select an alternate production
scanner/extractor or filter any pre-existing node, edge, ESM fact, diagnostic, metadata
fact, or path.

### Phase 5 — Documentation, full validation, and handoff

After behavior and tests pass, update `CODEX.md`, `README.md`,
`docs/INTERVIEW_QUESTIONS.md`, and this plan with decisions, progress, discoveries,
validation results, and the learning checkpoint. Perform the two-run temporary repository
smoke, audit the complete diff for scope growth, and stop with M2.1B only. Do not mark all
of Milestone 2 complete.

## Invariants and contracts

### Typed unresolved fact models

Use separate channels; do not overload Python imports or local ESM exports:

```text
UnresolvedCommonJsRequireFact(
  kind, module, local_name, source_path, span
)
UnresolvedCommonJsExportFact(
  kind, exported_name, local_name, source_path, span
)
UnresolvedEsmReExportFact(
  kind, module, imported_name, exported_name, source_path, span
)
```

CommonJS require kinds are `side_effect` and `binding`. Side-effect facts require
`local_name=None`; binding facts require a nonempty local name. Their span is the exact
`call_expression`.

CommonJS export kinds are `module_exports` and `named`. Whole-module assignments require
`exported_name=None`; named assignments require a nonempty exported property. Both require
a simple nonempty local RHS name. Their span is the exact `assignment_expression`.

ESM re-export kinds are `named`, `star`, and `namespace`. Named facts require imported and
exported names. Star facts use imported `*` and no exported name. Namespace facts use
imported `*` and a nonempty exported namespace name. Named spans use the exact
`export_specifier`; namespace spans use `namespace_export`; star spans use the exact `*`
token. Every fact also stores the nonempty static source module.

`ExtractionResult` and `RepositoryIndexResult` add `commonjs_requires`,
`commonjs_exports`, and `esm_reexports`. The repository fields are omitted when empty and
default to empty when older JSON is parsed. Facts remain outside `GraphSnapshot` and never
create endpoints or edges.

### Evidence and ambiguity rules

- Facts are emitted only from direct, error-free syntax matching the documented forms.
- A module string is preserved lexically by the bounded static-string helper; it is not
  resolved, normalized as a filesystem path, or interpreted as an installed package.
- CommonJS global names are accepted only after the program-level shadow/reassignment
  guard. If the guard cannot prove the relevant bare name unambiguous, omit the fact rather
  than lowering confidence or guessing.
- ESM re-export facts preserve the written imported/exported names. They do not establish
  that the target module or member exists.
- A bare runtime-form re-export such as `export { Value } from "pkg"` remains a syntax fact
  even if the unknown target might be type-only; target symbol classification requires
  resolution and is explicitly deferred. Explicit `type` syntax is always omitted.
- Interface and type-alias nodes are source declarations, not runtime availability claims.
  Only ordinary enums are runtime-capable for direct export-fact purposes.
- Valid unsupported syntax is silently omitted. Syntax errors retain the one deterministic
  first-error diagnostic. No regex fallback, parser-exception prose, or heuristic edge is
  allowed.

### Partial parse barrier

Keep the existing deterministic first ERROR/missing-node selection by byte position.
Always emit the module for a returned tree. Re-export and selected TypeScript declaration
facts may come only from error-free top-level subtrees; no new visitor may cross a node with
`has_error`, `is_error`, or `is_missing`, or an existing anonymous/unsupported scope
barrier. Existing valid M2.1A siblings before or after an erroneous child remain eligible.

CommonJS is stricter because it needs a whole-program ambiguity audit: if the root has any
ERROR or missing node, emit no CommonJS facts from that file. This avoids treating a valid
sibling as the global `require`/`module`/`exports` when the malformed subtree could contain
the binding or reassignment that changes its meaning.

### Stable IDs, ordering, and serialization

New declaration IDs call the existing `stable_node_id` with the new node kind,
repository-relative POSIX path, `<module>.<name>`, start line, and
`column:<start-column>`. Parser object identity, child index, filesystem enumeration, and
fact traversal order never enter an ID. Duplicate declarations preserve separate nodes
when their start positions differ; an exact duplicate coordinate remains an invalid graph
collision rather than being silently renamed.

Each new fact model defines a complete `sort_key` beginning with source path, start line,
and start column, followed by kind and every semantic field with explicit null sentinels.
Extractor results sort nodes by source position and facts by model sort keys. The indexer
sorts every aggregated channel again. `GraphSnapshot` retains ID/edge normalization, and
canonical JSON retains recursive key ordering, compact separators, UTF-8, and one newline.

### Resource and security rules

Use only the already-loaded source string and pinned parser. Do not invoke Node, npm,
TypeScript, package scripts, imported code, subprocesses, network, or target resolution.
Do not read `package.json` exports or `tsconfig` paths in this slice. Paths and diagnostics
remain repository-relative, and unsupported syntax must not materially increase scanner
or repository resource limits.

## Test and harness plan

### Focused extractor and model cases

- Every supported CommonJS form, quote style, multiple declarators, repeated assignments,
  exact fact kind/name/module/span, and absence of graph edges.
- Dynamic/template/empty module strings; destructuring; member/chained require; nested,
  conditional, callback, and argument calls; object/function/class RHS; computed/string
  properties; compound/chained assignments; TypeScript import-equals/export-assignment.
- Program-scope import, variable, function, class, and bare-assignment shadow cases for each
  CommonJS global, including declarations after the candidate use.
- Named, aliased, default-named, star, and namespace ESM re-exports; empty/dynamic sources;
  statement/inline type-only forms; mixed lists; repeated specifiers; no target edges.
- Interface, generic interface, type alias, union/object/function types, ordinary enum,
  string/numeric enum initializers, exported forms, exact spans, containment, literal IDs,
  duplicates, and source-order independence.
- Ambient/declare, const enum, namespace/module, nested declarations, overload signatures,
  anonymous/default and other unsupported TypeScript forms remain absent.
- Malformed CommonJS suppression, safe re-export/declaration siblings around an error,
  stable first diagnostics, Unicode byte columns, path rejection, and source
  non-execution.
- Model validator matrices for each allowed/forbidden kind-field combination and absolute,
  parent, empty, or malformed paths.

### Integration and compatibility cases

- Indexer aggregation and sorting across `.js`/`.ts` files, file language labels, custom
  registry authority, diagnostics, and no fabricated `IMPORTS`/`EXPORTS` edges.
- CLI canonical serialization, aggregate CommonJS require count, omitted empty channels,
  parsing old M1/M2.1A JSON, atomic output, repeated bytes, path privacy, and source
  non-execution.
- Reversed filesystem enumeration and deliberately reordered extraction collections yield
  identical JSON.
- All existing JS/TS tests continue to prove M2.1A definitions, type-only ESM filtering,
  error barriers, IDs, spans, and `.jsx`/`.tsx` exclusion.
- M1 acceptance and updater check pass with all four hashes unchanged.
- Historical `m2-1a-graph.json` bytes remain unchanged and match the exact additive
  projection described above.
- Dedicated M2.1B partial gold is generated twice from its isolated repository and matches
  committed LF bytes, model round-trip, literal semantic assertions, stable IDs/spans,
  and no machine-specific content.

## Full acceptance commands

Run sequentially from `C:\RepoLens`; tests and harness commands require no network:

```text
uv lock --check --offline
uv sync --dev --locked
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest tests/test_javascript_typescript_extractor.py -v
uv run pytest tests/test_models.py -v
uv run pytest tests/test_extractors.py -v
uv run pytest tests/test_scanner.py -v
uv run pytest tests/test_indexer.py -v
uv run pytest tests/test_cli.py -v
uv run pytest tests/test_milestone1_acceptance.py -v
uv run pytest
uv run repolens harness-smoke
uv run repolens doctor
uv run python scripts/update_m1_acceptance_gold.py
uv run python scripts/update_m2_1b_acceptance_gold.py
git diff --check
git status --short
```

Record focused/full pass, skip, and coverage totals exactly. Total coverage must not fall
below the accepted M2.1A baseline without an explicit reviewed reason, and new production
branches need focused coverage. Perform the planned temporary repository CLI index twice,
compare bytes and SHA-256, parse the output, assert no absolute temporary path, and remove
the generated scratch repository. On Windows, do not claim Linux symlink or CI evidence.

## Failure modes

- **Grammar-shape drift:** pinned grammar nodes or unnamed modifier tokens differ from the
  probe. Fail focused ABI/shape tests and update this plan before changing recognition.
- **Accidental call extraction:** a generic `call_expression` walk emits nested or computed
  calls. Require exact program-child structural parents and negative tests.
- **CommonJS shadowing/reassignment:** local bindings make global-looking names ambiguous.
  Complete the program guard before emission; suppress rather than guess.
- **CommonJS runtime-table overclaim:** assignment order and alias mutation can change final
  exports. Preserve occurrence facts only; never synthesize a final table or edge.
- **Type/runtime conflation:** explicit type-only re-exports or interface/type declarations
  appear as runtime export facts. Filter explicit type tokens and declaration kinds.
- **Enum ambiguity:** `const enum` or ambient enum leaks as a runtime node/fact. Inspect
  modifier/ambient ancestors and exclude it.
- **Barrier leakage:** generic traversal discovers declarations inside namespaces,
  anonymous scopes, or erroneous subtrees. Gate new declarations at the program/export
  boundary and retain current barriers.
- **ID collision/order dependence:** duplicates use traversal index or source order. Use
  semantic coordinates and complete sort keys only.
- **Legacy JSON drift:** empty fields or a schema-version change rewrites M1/M2.1A bytes.
  Apply `exclude_if` in production, parse missing channels with defaults, and hash old gold
  before/after.
- **Compatibility test masking:** a broad historical projection hides a pre-existing
  regression. Permit removal of only named M2.1B kinds/edges/channels and compare every
  remaining canonical byte.
- **Fixture contamination:** adding M2.1B sources to the manifest repository changes
  earlier module/file output. Use the isolated sibling partial repository and leave all
  existing fixture sources/manifests/gold untouched.
- **Platform leakage:** temporary roots, CRLF, timestamps, or enumeration order enter gold.
  Assert LF, relative POSIX paths, no clock data, canonical ordering, and repeated hashes.

## Progress

- [x] 2026-07-17: Confirmed GitHub PR #3 is merged.
- [x] 2026-07-17: Fetched `origin/main`, switched from the clean feature branch, and
  fast-forwarded local `main` to `6e3137e4effceb730ee00464a970c530c76061a4`.
- [x] 2026-07-17: Confirmed `HEAD == main == origin/main` and a clean pre-plan tree.
- [x] 2026-07-17: Read `AGENTS.md`, `CODEX.md`, `.agent/PLANS.md`, and the completed M2.1A
  ExecPlan in full.
- [x] 2026-07-17: Audited current models, IDs, serialization, extractor, indexer, tests,
  dependency declarations, fixture layout, M1 profile, and pinned parser shapes.
- [x] 2026-07-17: Defined the proposed M2.1B scope and acceptance contract in this plan.
- [x] 2026-07-20: Developer approved the bounded scope without expansion.
- [x] 2026-07-20: Reconfirmed `HEAD == main == origin/main` at `6e3137e`, with only this
  untracked plan present, then created `m2-1b-commonjs-reexports-ts-declarations`.
- [x] 2026-07-20: Phase 1 — Added behavioral and contract tests and recorded the expected
  pre-implementation import failure for the absent typed contracts.
- [x] 2026-07-20: Phase 2 — Added typed contracts, three node kinds, default-empty channels,
  strict validators, sorting, old-payload defaults, and production empty-field omission.
- [x] 2026-07-20: Phase 3 — Implemented guarded top-level CommonJS, bounded ESM re-exports,
  selected module-level TypeScript declarations, index aggregation, and CLI import counts.
- [x] 2026-07-20: Phase 4 — Added the isolated partial repository/gold and generator; M1
  gold check passes and the exact additive M2.1A projection matches every historical byte.
- [x] 2026-07-20: Phase 5 — Completed documentation, every offline validation command,
  repeated gold/CLI hashes, path-privacy and non-execution checks, and the scope audit.
- [x] 2026-07-20: Independent final review found and repaired incomplete/overbroad CommonJS
  shadow auditing plus optional/type-argument require and string-named re-export leakage;
  focused regressions and the complete validation set pass after the repair.

## Decisions

- **2026-07-17 — Select exactly interfaces, type aliases, and ordinary enums.** These are
  the smallest common named TypeScript declarations omitted by M2.1A. Namespaces,
  ambient declarations, overloads, and abstract/declaration-file semantics introduce
  scope or runtime ambiguity and remain deferred.
- **2026-07-17 — Add honest node kinds.** Mapping interfaces/type aliases/enums to `class`
  or `data_model` would make syntax identity false. Additive enum values preserve existing
  IDs and old bytes while allowing exact new nodes.
- **2026-07-17 — Keep CommonJS occurrence facts separate.** CommonJS calls/assignments are
  neither Python imports nor ESM bindings. Dedicated channels prevent misleading fields
  and make the lack of target resolution explicit.
- **2026-07-17 — Require top-level exact forms and a shadow guard.** This draws a visible
  boundary between bounded CommonJS syntax and later general call/data-flow analysis.
- **2026-07-17 — Give re-exports their own channel.** A re-export has a source module and
  imported/exported identity, which the existing local `UnresolvedEsmExportFact` cannot
  represent honestly.
- **2026-07-17 — Preserve explicit type/runtime semantics.** Type-only re-export syntax and
  interface/type direct exports are omitted from runtime fact channels. Ordinary enums
  retain their runtime direct export fact.
- **2026-07-17 — Preserve historical gold with exact additive projection.** Production
  always runs the current pipeline. A test-only projection proves all pre-M2.1B bytes are
  unchanged while a separate gold records new behavior.
- **2026-07-17 — Do not bump graph schema version.** New node enum values and top-level
  unresolved channels are additive within the current pre-1.0 contract; changing the
  nested graph version would rewrite every historical output without improving old-payload
  parsing.
- **2026-07-20 — Audit CommonJS names by runtime meaning.** Hoisted `var`, generator,
  abstract-class, ordinary-enum, namespace, import-equals, update, and program-level bare
  assignment forms make the corresponding CommonJS name ambiguous. Erased type-only
  imports, interfaces, type aliases, `const enum`, and identifiers used only in pattern
  initializers do not bind the runtime name.

## Discoveries and surprises

- The completed TypeScript frontend M2.1A source already contains a type alias, so adding
  type-alias nodes necessarily makes normal M2.1B output a strict superset of the historical
  partial gold. Compatibility needs an exact additive comparison, not overwritten gold.
- In tree-sitter-typescript 0.23.2, `const enum` does not have a distinct named node type;
  it is an `enum_declaration` with an unnamed `const` child.
- Statement-level and inline re-export `type` modifiers are unnamed tokens, consistent with
  M2.1A import/export filtering. Mixed clauses can therefore retain runtime specifiers.
- CommonJS has no dedicated grammar node: the pinned JavaScript parser emits ordinary calls,
  declarators, member expressions, and assignments. Parent-shape checks are the primary
  defense against accidental M2.2 call extraction.
- `export * as namespace` has a named `namespace_export` node, while bare star re-export
  exposes only an unnamed `*` child. Span policy must be explicit for byte-stable gold.
- The existing static-string helper assembled only `string_fragment` children, which could
  omit lexical escape nodes. M2.1B now preserves the exact quoted interior for supported
  module strings; target interpretation remains deferred.
- Independent final review showed that the initial ambiguity prepass inspected only direct
  root declarations, treated every identifier in a destructuring default as a binding, and
  accepted optional/type-argument require calls and string-named re-exports. Runtime-aware
  program-scope helpers and exact node-shape guards now cover those cases.

## Validation transcript

Planning-only checks on 2026-07-17:

- GitHub PR metadata: PR #3 `feat: add JavaScript and TypeScript extraction foundation`
  is closed and merged; merge commit
  `6e3137e4effceb730ee00464a970c530c76061a4`.
- `git fetch origin main` updated `origin/main` from `8197b09` to `6e3137e`.
- `git switch main` reported a clean switch; `git merge --ff-only origin/main` completed a
  fast-forward without reset or rebase.
- `git branch --show-current` returned `main`; `git rev-parse HEAD`, `main`, and
  `origin/main` each returned `6e3137e4effceb730ee00464a970c530c76061a4`; pre-plan
  `git status --short` was empty.
- Read-only parser probes using the locked environment parsed representative CommonJS,
  ESM re-export, interface, type-alias, enum, const-enum, exported, ambient, and namespace
  syntax without parser errors and confirmed the node shapes recorded above.
- No production code, test, dependency, fixture, gold, or documentation behavior was
  changed during planning. Full acceptance commands intentionally remain pending until an
  implementation is separately authorized.

Final local Windows validation on 2026-07-20:

- `uv lock --check --offline` — exit 0; 30 packages resolved. `uv sync --dev --locked` —
  exit 0; 30 packages resolved and 29 checked. `pyproject.toml` and `uv.lock` are unchanged.
- `uv run ruff format --check .` — exit 0; 51 files already formatted.
  `uv run ruff check .` — exit 0; all checks passed. `uv run mypy src tests` — exit 0;
  no issues in 35 source files.
- Focused pytest — exit 0 throughout: 44 selected M2.1B cases; 78 complete JS/TS cases;
  8 model cases; 30 indexer cases; 22 CLI cases; 16 M1 acceptance cases; 1 exact M2.1A
  compatibility case; and 1 M2.1B partial-gold case.
- `uv run pytest` — exit 0; 276 passed and 3 skipped because Windows denied symlink
  creation with error 1314; total coverage 93% and JS/TS extractor coverage 94%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases.
  `uv run repolens doctor` — exit 0; Python 3.11.15/package 0.1.0 healthy and no network.
- `uv run python scripts/update_m1_acceptance_gold.py` — exit 0; all 4 M1 gold files
  matched. `uv run python scripts/update_m2_1b_acceptance_gold.py` — exit 0; partial gold
  matched. The M1 and M2.1A committed gold files are unchanged.
- Two M2.1B generations were byte-identical at 6,192 bytes with SHA-256
  `bc5d0eab6684fdd27f6bdb66252bb2958ebc0c9750b818a0fc2151cf353a445e`.
  Two disposable CLI runs produced the same hash, 10 nodes, 9 edges, 2 CommonJS require
  facts, 2 CommonJS export facts, 5 ESM re-export facts, no warnings, and no absolute
  temporary path in JSON; verified scratch cleanup completed.
- `git diff --check` — exit 0 with only expected Windows LF-to-CRLF working-copy warnings
  for three Markdown files. The final scope contains 14 modified tracked files and 5 new
  files, exactly within the approved production/model/indexer/CLI, tests, docs, isolated
  fixture/gold, generator, and ExecPlan paths. Immutable dependency/lock, scanner, existing
  manifest/source, four M1 gold, and M2.1A gold paths have no diff. Final branch is
  `m2-1b-commonjs-reexports-ts-declarations` at unchanged base `6e3137e`.
- This is local Windows evidence only and does not claim Linux or GitHub Actions
  verification. No commit, push, PR, merge, or later Milestone 2 work was performed.

## Learning checkpoint

Before M2.1B is complete, the developer must explain in their own words:

1. Why matching one exact top-level `require` shape is not general call extraction, and why
   optional/type-argument variants remain out of scope.
2. Why runtime `require`, `module`, and `exports` bindings/reassignments make an apparent
   CommonJS fact ambiguous, why erased type-only names do not, and why a partial parse
   cannot safely complete that audit.
3. Why a re-export is a direct syntax fact but not yet an `exports` graph edge.
4. How named, star, and namespace re-exports differ, including explicit type-only forms.
5. Why interfaces/type aliases can be graph nodes while still producing no runtime export
   fact, and why ordinary enums differ from `const enum`.
6. Why new declaration IDs remain independent of traversal order and machine paths.
7. How production empty-field omission and an exact test-only compatibility projection
   preserve M1/M2.1A bytes without hiding current production behavior.

## Outcome and follow-ups

M2.1B is complete locally: exact guarded CommonJS occurrences, bounded runtime ESM
re-exports, and selected TypeScript declaration nodes flow through canonical indexing with
no target resolution or graph import/export edges. M1 bytes remain unchanged; M2.1A bytes
match through the exact additive test projection; and the isolated M2.1B gold records normal
current production behavior. Milestone 2 remains open. JSX/TSX and React classification,
calls, resolution, traversal, overview/context/impact, and MCP require separately reviewed
later slices. No Linux verification is claimed from this Windows run.
