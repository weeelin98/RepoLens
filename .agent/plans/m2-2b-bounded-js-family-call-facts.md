# Milestone 2.2B — Bounded JS-Family Call Occurrence Facts

Status: approved and active on 2026-07-24. Local implementation and Windows validation are
complete on `m2-2b-bounded-js-family-call-facts`; independent review found no blocking
issue, and the slice is ready for publication. Required Linux CI, completion, Milestone 3,
and later work remain pending or unauthorized.

## Purpose and user-visible outcome

The completed M2.1A, M2.1B, and M2.2A slices provide deterministic JavaScript,
TypeScript, JSX, and TSX modules, named definitions, conservative React components, and
unresolved import/export/CommonJS syntax. The remaining Milestone 2 user-visible gap is
direct call syntax.

The approved implementation adds a default-empty
`javascript_calls` collection to canonical `graph.json`. Each entry preserves one
bounded, error-free JS-family call occurrence, its normalized written callee, whether the
supported callee uses optional chaining, the nearest indexed lexical owner, and the exact
tree-sitter call span. It will not claim that the callee exists, resolves to a graph node,
or executes at runtime.

No `calls` graph edge is created in this slice. Cross-file and same-file target resolution
remain Milestone 3. HTTP meaning remains Milestone 4.

## Remaining Milestone 2 acceptance gaps

The repository already satisfies these broad Milestone 2 requirements:

- pinned compatible JavaScript, TypeScript, JSX, and TSX grammars;
- deterministic discovery, modules, named definitions, selected TypeScript declarations,
  React components, source spans, qualified names, containment, and stable node IDs;
- unresolved ESM imports, local exports, re-exports, and bounded CommonJS occurrences,
  including written aliases and runtime/type-only distinctions;
- deterministic first-error diagnostics and conservative partial-tree barriers;
- explicit collection sorting, canonical serialization, repeated-byte tests, path privacy,
  source non-execution, historical compatibility, fixture partial gold, and Linux CI.

The unsatisfied Milestone 2 requirements are call-specific:

1. No `ExtractionResult` or `RepositoryIndexResult` channel can represent a direct
   JavaScript-family call occurrence.
2. Ordinary `call_expression` syntax is not collected. The only recognized call-shaped
   syntax is the narrow top-level CommonJS `require` contract, which is an import
   occurrence rather than general call extraction.
3. Call aliases are not preserved as written unresolved callees.
4. Optional identifier/member calls have no contract. The pinned JavaScript and
   TypeScript-family grammars expose different optional-chain token shapes.
5. Call-specific owner evidence, exact spans, malformed-subtree suppression, deterministic
   ordering, model validation, fixture semantics, and historical compatibility are absent.
6. The TypeScript frontend and full-stack frontend fixtures contain direct calls, but the
   current M2.2A partial gold deliberately has no call facts.

The Milestone 2 contract does not require call-target resolution. `CODEX.md` says syntax
facts remain direct while target resolution is deferred, and its observable output names
unresolved call facts with spans. Therefore resolution, graph edges, traversal, and HTTP
semantics do not belong in this proposed slice.

## Scope and non-goals

### Supported files and parser routes

The existing scanner, registry, parser, and language matrix remains unchanged:

| Suffix | Parser | Language label |
| --- | --- | --- |
| `.js` | pinned JavaScript grammar | `javascript` |
| `.jsx` | pinned JavaScript grammar | `jsx` |
| `.ts` | pinned TypeScript grammar | `typescript` |
| `.tsx` | pinned TSX grammar | `tsx` |

No suffix, filename, dependency, grammar, or lockfile change is planned.

### Exact supported callees

An eligible occurrence is an error-free tree-sitter `call_expression` whose `function`
field is one of these exact forms:

1. An ordinary identifier:

   ```js
   load()
   load?.()
   ```

2. A noncomputed dotted member chain rooted at an ordinary identifier, `this`, or `super`,
   with every property represented by `property_identifier`:

   ```js
   api.load()
   api.client.load()
   api?.load()
   api.load?.()
   api?.client.load?.()
   this.save()
   super.save()
   ```

3. TypeScript/TSX call type arguments are transparent only when the pinned grammar has
   already produced an error-free `call_expression` with one of the supported callees:

   ```ts
   load<Result>()
   api.load<Result>()
   ```

The normalized `callee` value removes only supported optional-chain punctuation and type
arguments: `api?.client.load?.()` records `api.client.load` with `is_optional=true`.
Ordinary identifiers and property spellings are preserved exactly, including case and
Unicode. Arguments are not interpreted.

Every eligible nested call is considered independently. For `outer(inner())`, both calls
qualify. For `factory()()` or `load().then()`, the inner identifier call qualifies but the
outer call-result callee does not.

### Exact unsupported callees and syntax

The following produce no `javascript_calls` fact:

- bare `require(...)`, optional `require?.(...)`, and `import(...)`; CommonJS/module-loading
  syntax stays in its existing dedicated contracts;
- `new Constructor(...)`, tagged templates, decorators, and JSX tag rendering;
- computed or private members such as `api["load"]()`, `api[key]()`, and
  `this.#load()`;
- parenthesized, asserted, non-null, `as`, `satisfies`, sequence, conditional, logical,
  assignment, or awaited callee wrappers;
- a call result used as the callee or receiver, including `factory()()` and
  `factory().run()`;
- arbitrary expressions such as `(condition ? a : b)()`;
- malformed or missing call/callee nodes;
- constructor, accessor, object-method, class-field, static-block, namespace/module,
  ambient, generator, or other unsupported named scope bodies whose calls cannot be
  assigned an honest indexed owner.

Valid unsupported syntax is omitted without a diagnostic. Existing parser errors retain
the existing deterministic diagnostic.

### Lexical owner and callback boundary

Each fact uses `enclosing_id` for the nearest indexed lexical module, function, method,
identifier-arrow, or `react_component` node containing the call syntax.

- Calls in a supported nested named definition belong to that nested definition.
- Calls in an anonymous arrow/function callback do not create a callback node. They keep
  the nearest indexed outer owner. This is a lexical containment fact only; it does not
  claim that the outer owner synchronously invokes the callee.
- This rule intentionally captures fixture calls such as `loadProfile(id)` inside the
  `useEffect` callback within `ProfileCard`, and `fetchTask(taskId)` inside the callback
  within `TaskPanel`.
- Calls inside unsupported named/generated/accessor/constructor/object/class-field scopes
  are omitted rather than attributed to an outer symbol.
- Direct module-body calls use the module node as their owner.

Anonymous callbacks remain unmodeled. A later resolver may use the enclosing owner as one
candidate source for a `calls` edge, but this slice does not make that decision.

### Alias boundary

The extractor preserves the written callee only:

```ts
import { fetchTask as load } from "./api";
load(id);                         // callee = "load"

const alias = load;
alias(id);                        // callee = "alias"

client.tasks.load(id);            // callee = "client.tasks.load"
```

It does not follow ESM/CommonJS aliases, assignments, destructuring, object properties,
re-exports, parameters, `.bind`, `.call`, `.apply`, or data flow. It does not turn a
written alias into a target name. Existing unresolved import facts supply separate syntax
evidence for later resolution.

### Optional-chaining boundary

`is_optional` is true when any supported part of the call boundary or dotted callee chain
contains optional-chain syntax. It does not predict whether the call executes.

The implementation must recognize the verified pinned shapes rather than search source
text:

- the JavaScript grammar represents direct optional calls and optional member segments
  with named `optional_chain` nodes;
- TypeScript/TSX represents optional member access with a named `optional_chain`, while a
  direct optional call boundary may expose an unnamed `?.` token;
- repeated optional segments still produce one fact with `is_optional=true`;
- ordinary calls use `is_optional=false`.

No regex or text fallback may compensate for an ERROR tree or unsupported callee shape.

### Strict non-goals

- no import/export or re-export resolution;
- no same-file or cross-file call-target resolution;
- no `calls`, `imports`, `exports`, `inherits`, endpoint, or other new graph edge;
- no symbol table, type checker, alias/data-flow engine, overload selection, or method
  dispatch;
- no call arguments, return values, promises, callbacks, hooks, props, state, or effect
  semantics;
- no general computed-call, dynamic-import, `require`, constructor, decorator, or tagged
  template semantics;
- no JSX element graph or wrapper/HOC/component inference;
- no `fetch`, Axios, URL, route, FastAPI, or frontend/backend HTTP meaning;
- no graph traversal, Markdown overview, query, context pack, ranking, or impact analysis;
- no CLI query/callers/callees/path behavior;
- no MCP behavior;
- no Milestone 3 or later behavior.

## Current state

- On 2026-07-24, `HEAD`, `main`, and `origin/main` are synchronized at merge commit
  `56f5c608e0df696da51288583d8cbc5342cb8be7`; the working tree was clean before this
  planning delta.
- M2.1A, M2.1B, and M2.2A are complete and Linux CI verified. Milestone 2 remains open.
- `NodeKind`, `EdgeKind.CALLS`, and graph evidence contracts already exist, but no graph
  edge may be emitted without a target node. A call occurrence therefore belongs outside
  `GraphSnapshot`, alongside unresolved imports and re-exports.
- `ExtractionResult` and `RepositoryIndexResult` have no call-fact channel.
- `JavaScriptTypeScriptExtractor` uses one shared visitor for all four suffixes. Generic
  traversal currently passes through call expressions without recording them; exact
  `require` matching is separate and top-level only.
- The indexer aggregates and re-sorts every unresolved channel. Canonical serialization
  automatically handles additive Pydantic fields.
- The CLI writes the complete `RepositoryIndexResult`; no CLI production change is needed
  to expose an added collection. The current summary does not count every unresolved fact
  category and will remain unchanged.
- The TypeScript frontend fixture contains `useState`, `useEffect`, callback-contained
  `loadProfile`, `fetch`, and `response.json` calls. The full-stack frontend contains the
  analogous `fetchTask` flow.
- Existing future `gold.json` files already describe resolver-derived `calls` edges with
  readable placeholder IDs. They are not current canonical extraction output and must not
  be overwritten or used as M2.2B call-fact gold.
- Pinned dependencies remain tree-sitter 0.26.0, tree-sitter-javascript 0.25.0, and
  tree-sitter-typescript 0.23.2. No new package is required.

## Acceptance criteria

1. The scanner, registry, parser capsules, language labels, dependencies, and lockfile are
   unchanged.
2. A frozen call-fact model and default-empty `javascript_calls` channels represent only
   the exact forms in this plan and reject inconsistent kind/callee, path, owner, and span
   data.
3. Identifier and supported dotted-member calls in `.js`, `.jsx`, `.ts`, and `.tsx`
   produce one fact per syntax occurrence with exact written names, normalized callee,
   correct optional state, owner ID, relative path, and exact call-expression span.
4. Type arguments are transparent only on an error-free TypeScript/TSX call node. No
   source-text reparsing occurs.
5. Computed/private/parenthesized/wrapped/call-result/new/import/require/tagged/decorator
   forms and unsupported scope bodies produce no call fact.
6. Calls nested in arguments are separate facts when each callee qualifies. Duplicate
   calls are not deduplicated; source coordinates preserve every occurrence.
7. Anonymous callback calls use the nearest indexed outer owner, while supported nested
   named definitions use their own node and unsupported named scopes remain barriers.
8. Import/local aliases remain written callees. No target, alias origin, installed package,
   method receiver type, or runtime existence is inferred.
9. Optional calls are detected from pinned grammar nodes/tokens for both grammar families.
   Optional state does not change confidence or create a graph edge.
10. Calls from an error-free top-level subtree may survive beside a malformed sibling.
    Erroneous/missing subtrees contribute no calls; the existing first diagnostic and
    M2.1B CommonJS whole-file suppression remain unchanged.
11. Every `enclosing_id` resolves to a graph node in the same repository result whose kind
    is module, function, method, or React component and whose source path matches the fact.
12. No call node or stable call ID is introduced. Existing node IDs, spans, qualified
    names, containment, component classification, exports, and graph schema version remain
    unchanged.
13. Facts sort by a complete explicit key. Repeated extraction, reversed discovery,
    reordered injected results, model round-trip, two gold generations, and two CLI indexes
    are byte-identical.
14. Empty `javascript_calls` is omitted from production JSON and defaults empty when old
    M1/M2 payloads are parsed. Historical files gain no empty field.
15. All M1 gold remains byte-identical. M2.1A and M2.2A compatibility remove only the new
    call channel in addition to their already approved historical input/projection rules.
    M2.1B source, helper, and gold remain byte-identical without projection because bare
    `require` and call-result member forms are excluded.
16. A new TypeScript frontend `m2-2b-graph.json` records normal current output, including
    literal call-fact semantics. Full-stack adds semantic call assertions without a second
    partial gold. Existing future gold and fixture source remain unchanged.
17. No production call edge, resolution, HTTP meaning, traversal, report, query, MCP, or
    later-milestone behavior appears.
18. Full local acceptance, repeated-byte/privacy/non-execution checks, historical
    compatibility, and the required Linux CI job pass before any completion claim.

## Model and schema implications

Add these extraction-layer contracts in `src/repolens/extractors/base.py`:

```text
JavaScriptCallKind = identifier | member

UnresolvedJavaScriptCallFact(
  kind,
  callee,
  enclosing_id,
  is_optional,
  source_path,
  span,
)
```

Model rules:

- `identifier` requires one nonempty undotted callee.
- `member` requires at least a root and one property separated by dots.
- `callee` contains no optional punctuation, type arguments, argument text, or inferred
  target identity.
- `enclosing_id` is nonempty and identifies an existing owner node.
- `source_path` uses the existing repository-relative POSIX validator.
- `span` is the exact `call_expression`.
- `is_optional` defaults to false.
- `sort_key` contains source path, start/end coordinates, enclosing ID, kind, callee, and
  optional state with no traversal-order input.

Add default-empty `javascript_calls` tuples to `ExtractionResult` and
`RepositoryIndexResult`. The repository field uses production `exclude_if` so old payload
bytes remain unchanged. `RepositoryIndexResult` validates owner existence, allowed kind,
and same-source-path consistency while sorting the collection.

No `NodeKind`, `GraphNode`, `GraphEdge`, `EdgeKind`, `EvidenceKind`, graph metadata,
`GraphSnapshot.schema_version`, canonical JSON function, dependency, or lockfile change is
planned. This is an additive top-level unresolved-fact contract within the pre-1.0 index
schema.

## ExtractionResult and indexer data flow

```text
pinned parser
  -> shared JS-family syntax visitor / bounded call collector
  -> ExtractionResult.javascript_calls
  -> index_repository aggregation and owner validation
  -> RepositoryIndexResult.javascript_calls
  -> existing canonical graph.json serialization
```

The collector reuses the already loaded UTF-8 source bytes, tree-sitter nodes, current
definition/component selection, source-span conversion, normalized path, and actual graph
node IDs. It does not reparse source or create a second syntax tree.

The indexer appends the extraction tuple, validates owners after graph assembly, and sorts
again at the repository boundary. The CLI already serializes the complete result and needs
no new command, option, count, or error policy.

## Evidence, span, identity, and ordering rules

- A call fact is direct syntax evidence, but it is not a graph edge and carries no
  confidence field.
- `callee` is derived only from exact identifier/`this`/`super` and
  `property_identifier` nodes in the `function` subtree.
- The span starts at the first byte of the callee and ends after the call arguments because
  it is the exact `call_expression`. It includes supported optional punctuation and
  TypeScript type arguments.
- Lines are tree-sitter row plus one. Columns remain zero-based UTF-8 byte offsets and end
  coordinates remain exclusive.
- Unicode before or within a callee must prove byte-column behavior in authored tests.
- Facts have no stable IDs. Their identity is the complete occurrence tuple including
  source coordinates. Existing owner stable IDs remain unchanged.
- Sort order must not depend on filesystem enumeration, parser child order, a set, object
  identity, or insertion order.

## Partial-tree and malformed-file safeguards

- Preserve the existing deterministic first ERROR/missing-node selection.
- Always emit the module for a returned tree.
- Begin collection only from error-free top-level siblings, matching the existing safe
  subtree boundary.
- Never collect a call whose node, callee, owner declaration, or traversed subtree has an
  ERROR or missing node.
- A malformed top-level sibling does not require whole-file call suppression because
  recognizing a written call needs no program-wide binding audit.
- Preserve stricter existing rules independently: CommonJS remains suppressed for any
  partial root, and class-component classification still requires its complete audit.
- No regex, token-text recovery, exception prose, TypeScript compiler, or alternate parser
  fallback is permitted.

## Milestone phases

### Phase 0 — Approval gate

Review this inactive proposal and revise any disputed boundary. Do not create a feature
branch or modify behavior until the developer explicitly approves the exact ExecPlan.
At implementation start, reconfirm clean synchronized `main`, the approved base commit,
and the allowed file set.

### Phase 1 — Authored failing behavior and contract tests

Add hand-written tests for the complete positive/negative matrix below before production
behavior. Pin literal representative fact values, owner IDs, spans, Unicode byte columns,
and absence of call edges. Re-run read-only grammar probes if an expected shape differs and
record the discovery before changing recognition.

Proposed paths:

- new `tests/test_js_family_call_facts.py`;
- `tests/test_models.py`;
- focused compatibility assertions in
  `tests/test_javascript_typescript_extractor.py`,
  `tests/test_jsx_tsx_react_components.py`, `tests/test_indexer.py`, and
  `tests/test_cli.py`.

### Phase 2 — Additive unresolved call contract

Add and export `JavaScriptCallKind` and `UnresolvedJavaScriptCallFact`; add default-empty
extraction/repository channels, complete sorting, owner validation, old-payload parsing,
and production empty-field omission.

Expected production paths:

- `src/repolens/extractors/base.py`;
- `src/repolens/extractors/__init__.py`;
- `src/repolens/indexer.py`.

No graph model or serialization module change is expected.

### Phase 3 — Bounded shared call collection

Extend the existing JS-family extractor with exact callee normalization, optional-token
adapters for the two pinned grammar families, owner-aware traversal, unsupported-scope
barriers, and safe partial-tree behavior. Preserve every M2.1/M2.2A path and keep CommonJS
matching separate.

Expected production path:

- `src/repolens/extractors/javascript_typescript.py`.

Do not add a resolver, edge builder, generic expression evaluator, symbol table, or CLI
service.

### Phase 4 — Compatibility and partial gold

- Keep M1 source profiles, helpers, and four gold files unchanged.
- Extend only the test-side M2.1A projection to omit `javascript_calls` after applying its
  existing JSX/TSX input exclusion and M2.1B additive projection.
- Keep the isolated M2.1B repository, helper, and gold unchanged and prove normal current
  indexing still matches without projection.
- Change the M2.2A checker/test to compare an exact projection with only
  `javascript_calls` removed; do not change `m2-2a-graph.json`.
- Add check-by-default, explicit-`--update`
  `scripts/update_m2_2b_acceptance_gold.py` and
  `harness/fixtures/typescript_frontend/m2-2b-graph.json` for normal current output.
- Add full-stack semantic call-fact assertions without another partial gold.
- Do not edit fixture source, manifests, questions, diffs, or future `gold.json`.

### Phase 5 — Documentation, validation, review, and Linux handoff

After implementation only, update `CODEX.md`, `README.md`,
`docs/INTERVIEW_QUESTIONS.md`, and this ExecPlan with verified behavior, decisions,
discoveries, exact results, and the learning checkpoint. Run pytest commands sequentially
on Windows. Perform repeated gold/CLI bytes, privacy, non-execution, edge-absence, and scope
audits.

Publish only after separate final review. Claim Linux success only from the required
GitHub Actions job for the exact implementation commit. Keep Milestone 2 open unless a
separate acceptance review concludes every Milestone 2 criterion is satisfied. Do not
select or begin Milestone 3.

## Authored positive and negative test matrix

| Area | Positive cases | Negative/boundary cases |
| --- | --- | --- |
| Identifier calls | module, function, method, arrow, component; repeated and nested argument calls | `require`, `import`, `new`, tagged template, missing/error callee |
| Member calls | identifier/`this`/`super` roots; multi-segment dotted chain | computed/string/private property, call-result receiver, arbitrary expression root |
| Optional calls | `fn?.()`, `api?.load()`, `api.load?.()`, repeated optional segments in JS and TSX | optional syntax in malformed tree; no text/regex fallback |
| TypeScript calls | identifier/member calls with type arguments in `.ts`/`.tsx` | JS/JSX type-argument ERROR; asserted/non-null/`as`/`satisfies` callee wrapper |
| Aliases | imported alias, local alias, parameter name, dotted alias preserved verbatim | no alias-origin, re-export, assignment, type, or target inference |
| Ownership | module; named nested function; method; identifier arrow; React component | unsupported constructor/accessor/generator/object/class-field/static-block scope |
| Anonymous callbacks | callback-contained call keeps nearest indexed outer owner; fixture effect callbacks | no callback node or synchronous-execution claim |
| Nested expressions | `outer(inner())` gives two facts; inner call of `factory()()` or `load().then()` retained | outer call-result call omitted |
| Spans/Unicode | exact multiline call span, type arguments, optional punctuation, UTF-8 byte columns | declaration/statement/arguments-only guessed span |
| Partial trees | safe sibling calls and stable diagnostic | erroneous owner/call subtree; no malformed partial promotion |
| Representation | facts only, valid owner IDs, unchanged graph nodes/edges/IDs | no call node, `calls` edge, target node, confidence, resolver note |
| Determinism | repeated extraction, reversed files, reordered injected tuples, model round-trip | no set/filesystem/parser-object ordering |
| Security/privacy | inert source that would write/spawn/fetch if executed; relative POSIX paths | no subprocess, Node, package, network, absolute root, timestamp |
| Fixtures | ProfileCard/loadProfile and TaskPanel/fetchTask callback facts; API `fetch`/`response.json` facts | future resolver gold untouched; `.then` call-result member excluded |

Tests must assert absence as strongly as presence. Gold bytes alone are insufficient:
literal tests must pin representative kind, callee, optional state, owner, path, span,
ordering, lack of call edges, and non-execution.

## Fixture and compatibility strategy

### M1

The historical M1 input profile already excludes `.js`, `.jsx`, `.ts`, and `.tsx`.
`javascript_calls` is empty and omitted. All four `m1-graph.json` files and the M1 helper
remain byte-identical without a projection.

### M2.1A

Keep `m2-1a-graph.json` immutable. Continue indexing a temporary TypeScript frontend copy
with JSX/TSX excluded, run the normal current pipeline, apply the existing exact M2.1B
additive projection, then remove only `javascript_calls` before comparing all canonical
bytes. Production indexing never uses this projection.

### M2.1B

Keep `m2-1b-repo`, `update_m2_1b_acceptance_gold.py`, and `m2-1b-graph.json` unchanged.
The repository's call-shaped syntax is bare `require` or a call-result member form, both
outside this plan's call channel. Normal current indexing must therefore remain
byte-identical with no projection.

### M2.2A

Keep `m2-2a-graph.json` immutable. Update only its test/check path to remove exactly
`javascript_calls` from a validated current result before canonical comparison. No node,
edge, import/export/CommonJS fact, metadata, diagnostic, or existing source is filtered.

### M2.2B

The existing TypeScript frontend repository owns `m2-2b-graph.json`. The new helper checks
by default and writes only under explicit `--update`, using UTF-8 LF with exactly one final
newline and a canonical model round-trip. The gold is a current extraction snapshot, not
the future resolver/query `gold.json`.

The full-stack fixture receives semantic assertions for TaskPanel's unresolved
`fetchTask` occurrence and API-client calls. It does not receive a second partial gold.

Every compatibility test must compare committed bytes, report a useful unified diff, and
prove the production path exposes current call behavior before any historical projection.

## Security, privacy, and resource rules

- Use only the already loaded source bytes and pinned in-process parser.
- Never execute or import indexed code, invoke Node/npm/TypeScript, inspect installed
  packages, run package scripts, open sockets, or access a network.
- Never resolve a module, alias, receiver type, target symbol, or HTTP endpoint.
- Keep paths repository-relative and POSIX; omit temporary roots, environment paths,
  timestamps, parser addresses, and exception prose.
- Preserve scanner ignore, symlink containment, file/repository limits, output pruning,
  decoding, and diagnostics unchanged.
- Call collection is linear in visited syntax nodes. It does not inspect argument values or
  recurse through source text.

## Exact local validation commands

Run sequentially from `C:\RepoLens`; tests and harness commands require no network:

```text
uv lock --check --offline
uv sync --dev --locked
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest tests/test_js_family_call_facts.py -v
uv run pytest tests/test_javascript_typescript_extractor.py -v
uv run pytest tests/test_jsx_tsx_react_components.py -v
uv run pytest tests/test_models.py -v
uv run pytest tests/test_extractors.py -v
uv run pytest tests/test_scanner.py -v
uv run pytest tests/test_indexer.py -v
uv run pytest tests/test_cli.py -v
uv run pytest tests/test_milestone1_acceptance.py -v
uv run pytest tests/test_javascript_typescript_extractor.py::test_typescript_frontend_matches_separate_m21a_partial_gold -v
uv run pytest tests/test_javascript_typescript_extractor.py::test_m21b_isolated_partial_gold_matches_semantics_and_repeated_generation -v
uv run pytest tests/test_jsx_tsx_react_components.py::test_m22a_typescript_frontend_partial_gold_matches_semantics_and_repeated_generation -v
uv run pytest tests/test_js_family_call_facts.py::test_m22b_typescript_frontend_partial_gold_matches_semantics_and_repeated_generation -v
uv run pytest
uv run repolens harness-smoke
uv run repolens doctor
uv run python scripts/update_m1_acceptance_gold.py
uv run python scripts/update_m2_1b_acceptance_gold.py
uv run python scripts/update_m2_2a_acceptance_gold.py
uv run python scripts/update_m2_2b_acceptance_gold.py
make check
git diff --check
git status --short
```

Also:

1. generate M2.2B gold twice and compare exact bytes plus SHA-256;
2. index a disposable mixed `.js`/`.jsx`/`.ts`/`.tsx` repository twice through the CLI;
3. compare exact JSON bytes and SHA-256;
4. parse and round-trip the result;
5. assert expected call facts, owners, spans, optional flags, and ordering;
6. assert no `calls`/import/export/inheritance/HTTP edge was added;
7. assert no absolute temporary root or timestamp appears;
8. assert source write/subprocess/network sentinels remain absent;
9. remove the verified scratch repository.

Record exact pass, skip, coverage, byte count, and hash results. On Windows, keep the
existing three real-symlink privilege skips separate and make no Linux claim.

## Linux CI acceptance

Local Windows results cannot complete this slice. After explicit implementation approval,
independent review, commit, and publication:

- the required Linux `check` job must run `make check` for the exact implementation commit;
- `uv run repolens doctor` must pass;
- no test may be silently skipped except an already reviewed platform-specific condition;
- the run ID, commit SHA, job name, conclusion, duration, and exact job URL must be recorded
  in this ExecPlan and `CODEX.md`;
- completion may be claimed only after that required job succeeds.

## Failure modes

- **Call edge overclaim:** a fact is emitted as `EdgeKind.CALLS` without a target resolver.
  Keep the collection outside `GraphSnapshot`.
- **Callee text guessing:** regex or raw substring parsing accepts unsupported syntax.
  Build the normalized callee only from exact grammar fields.
- **Optional-token drift:** JavaScript and TSX use different named/unnamed shapes. Pin both
  in tests and keep a small grammar adapter.
- **Alias overreach:** `load()` is rewritten to an imported/exported origin. Preserve the
  written identifier only.
- **Callback overclaim:** enclosing ownership is described as synchronous invocation.
  Name it lexical containment and emit no edge.
- **Scope leakage:** constructor/accessor/generator/object/class-field calls are assigned to
  a module or class that is not their honest callable owner. Retain explicit barriers.
- **Call-result false positive:** `.then()` or `factory()()` becomes a static member target.
  Accept only identifier/`this`/`super`-rooted dotted chains.
- **Module-loading duplication:** `require` or dynamic `import` appears in both module and
  call channels. Exclude them from `javascript_calls`.
- **Partial-tree promotion:** an error-free child inside an erroneous owner leaks a call.
  Start only at safe top-level subtrees and require a valid owner.
- **Owner drift:** component reclassification or nesting changes a fact owner based on
  traversal timing. Use the actual selected graph node ID.
- **Historical masking:** a broad projection hides production regressions. Remove only the
  named call channel and compare every other canonical byte.
- **Future-gold contamination:** current extraction overwrites resolver/query
  `gold.json`. Add only the M2.2B partial sibling.
- **Nondeterminism/privacy:** traversal order, sets, roots, timestamps, or parser identities
  enter JSON. Use complete sort keys and repeated-byte assertions.
- **Execution:** source, Node, package scripts, or network calls run during indexing. Keep
  parsing in-process and block execution in tests.

## Decisions

- **2026-07-24 — Choose unresolved call occurrences as the smallest next slice.** Calls are
  the only unsatisfied Milestone 2 user-visible output category. Resolution belongs to
  Milestone 3 and HTTP meaning belongs to Milestone 4.
- **2026-07-24 — Keep calls outside the graph.** Without a defensible target node, a
  `calls` edge would violate endpoint and evidence invariants. A typed top-level fact
  preserves direct syntax honestly.
- **2026-07-24 — Normalize only exact identifier/member callees.** This covers fixture
  calls and common static syntax while excluding computed, call-result, and expression
  targets that need data flow.
- **2026-07-24 — Preserve aliases as written.** Extraction records syntax; import and local
  alias interpretation is a resolver responsibility.
- **2026-07-24 — Represent optionality explicitly.** Optional syntax affects whether a call
  executes but not the written target candidate. One boolean plus exact span preserves the
  bounded evidence without control-flow analysis.
- **2026-07-24 — Use lexical enclosing owners, not callback nodes.** Anonymous callbacks
  remain unmodeled; their calls retain the nearest indexed owner solely as containment
  evidence. Unsupported named scopes remain barriers.
- **2026-07-24 — Exclude module-loading calls.** `require` and dynamic `import` already have
  different import semantics and must not become generic call-target claims.
- **2026-07-24 — Preserve historical bytes through production omission and exact
  projections.** Empty fields stay absent; M2.1A/M2.2A projections remove only the new
  channel; the isolated M2.1B contract remains unchanged without projection.

## Discoveries and surprises

- The pinned JavaScript grammar emits named `optional_chain` nodes for both direct optional
  calls and optional member segments.
- The pinned TSX grammar emits a named `optional_chain` for optional member access but may
  expose direct optional-call `?.` as an unnamed token on `call_expression`. A
  one-grammar token check would silently miss TS/TSX optional calls.
- The pinned TSX grammar places call type arguments in a named `type_arguments` child while
  leaving the `function` field as the ordinary identifier/member callee. The JavaScript
  grammar reports the same TypeScript spelling as an ERROR tree.
- `api["load"]()` uses `subscript_expression`; `factory()()` uses a `call_expression`
  callee; `(foo)()` uses `parenthesized_expression`; and `new Foo()` uses
  `new_expression`. Exact field matching can exclude each without text heuristics.
- `import("x")` is a `call_expression` whose function is the `import` keyword, so it needs
  an explicit module-loading exclusion.
- The frontend fixture's desired `loadProfile`/`fetchTask` occurrences sit inside anonymous
  `useEffect` callbacks. Treating every anonymous callback as a hard call barrier would
  miss the fixture's central direct syntax while the future resolver gold already expects
  the enclosing component-to-client relationship.
- The isolated M2.1B fixture contains bare/nested `require` calls and a
  `require(...).writeFileSync(...)` call-result member. The proposed exclusions let its
  current production bytes remain unchanged without a compatibility projection.
- During implementation, the pinned grammar exposed tagged templates as call-shaped nodes
  whose argument field is a template string rather than ordinary `arguments`. Requiring
  the exact `arguments` node prevents a tagged template from becoming a call fact.
- An initial owner traversal treated every anonymous callable as transparent. Restricting
  outer-owner inheritance to direct call arguments keeps effect callbacks while preventing
  anonymous defaults, assigned function expressions, nested unindexed arrows, and class
  expressions from leaking calls into an outer owner.
- Supported function, method, arrow, and direct-callback default parameters expose ordinary
  error-free call expressions. Visiting the pinned `parameters` field records them under
  the same actual indexed callable owner without inspecting type syntax.

## Progress

- [x] 2026-07-24: Confirmed clean synchronized `main`, `origin/main`, and `HEAD` at merge
  commit `56f5c608e0df696da51288583d8cbc5342cb8be7`.
- [x] 2026-07-24: Read `AGENTS.md`, `CODEX.md`, `.agent/PLANS.md`, `README.md`, and the
  completed M2.1A, M2.1B, and M2.2A ExecPlans in full.
- [x] 2026-07-24: Audited graph models, extraction/result contracts, the shared JS-family
  extractor, scanner, indexer, serialization, CLI, focused and acceptance tests, fixture
  sources, historical/current/future gold, and all three gold helpers.
- [x] 2026-07-24: Ran read-only locked grammar probes for identifier, member, optional,
  computed, parenthesized, nested-result, constructor, dynamic-import, `this`, `super`, and
  generic call shapes in JavaScript, TypeScript, and TSX.
- [x] 2026-07-24: Derived this inactive proposal, exact syntax boundary, contract/data flow,
  authored test matrix, compatibility strategy, validation commands, Linux gate, and
  learning checkpoint.
- [x] 2026-07-24: Developer explicitly approved the exact ExecPlan, existing planning
  delta, base commit, and implementation branch.
- [x] 2026-07-24: Added the authored positive/negative contract, syntax, ownership, span,
  partial-tree, determinism, privacy, non-execution, fixture, and compatibility tests.
- [x] 2026-07-24: Added the frozen call contract, default-empty channels, complete sorting,
  owner validation, bounded shared-tree collector, and indexer aggregation.
- [x] 2026-07-24: Added only the M2.2B TypeScript frontend partial gold/helper, exact
  M2.1A/M2.2A projections, and full-stack semantic assertions while preserving historical
  fixtures and gold.
- [x] 2026-07-24: Updated `README.md`, `CODEX.md`, interview questions, and this ExecPlan
  with verified local behavior and limitations.
- [x] 2026-07-24: Completed the full sequential Windows validation, repeated-byte probes,
  privacy/non-execution checks, and scope audit with the three established symlink skips.
- [x] Implementation: complete locally.
- [x] Independent final review: completed on 2026-07-24 with no blocking correctness or
  scope finding; focused/full tests, static checks, harness, doctor, gold checks, and the
  final scope audit were reproduced.
- [ ] Linux CI: not begun.

## Planning validation transcript

- `git status -sb` reported clean `main...origin/main`.
- `git rev-parse HEAD`, `main`, and `origin/main` each returned
  `56f5c608e0df696da51288583d8cbc5342cb8be7`.
- `git show -s` confirmed merge commit `56f5c60` is PR #5's merge.
- Declared/locked packages remain tree-sitter 0.26.0, JavaScript grammar 0.25.0, and
  TypeScript grammar 0.23.2.
- Read-only JavaScript, TypeScript, and TSX parser probes produced the exact shapes recorded
  in Discoveries and surprises without changing repository files.
- No production code, test, fixture, gold, dependency, lockfile, schema, or CI file was
  changed during planning.

## Local implementation validation transcript

All commands below ran sequentially from `C:\RepoLens` on Windows with Python 3.11.15:

- `uv lock --check --offline` — exit 0; 30 packages resolved.
- `uv sync --dev --locked` — exit 0; 30 packages resolved and 29 checked.
- `uv run ruff format .` — exit 0; 55 files unchanged.
- `uv run ruff format --check .` — exit 0; 55 files already formatted.
- `uv run ruff check .` — exit 0; all checks passed.
- `uv run mypy src tests` — exit 0; no issues in 37 source files.
- Focused M2.2B, complete JS/TS, JSX/TSX, models, extractors, scanner, indexer, CLI,
  M1 acceptance, and individual M2.1A/M2.1B/M2.2A/M2.2B compatibility commands — exit 0.
  Counts were respectively 19, 76, 35, 9, 36, 35 plus 3 skips, 30, 23, and 16; each
  compatibility selection passed its one test.
- `uv run pytest` — exit 0; 333 collected, 330 passed, and 3 skipped only because Windows
  returned symlink privilege error 1314; total coverage 93%, JS-family extractor 95%.
- `uv run repolens harness-smoke` — exit 0; 5 fixtures, 5 questions, and 5 diff cases valid.
- `uv run repolens doctor` — exit 0; Python 3.11.15/package 0.1.0 healthy, network not
  required.
- The M1, M2.1B, exact-projection M2.2A, and M2.2B check-by-default gold helpers — exit 0.
- `make check` — exit 1 before execution because GNU Make is unavailable. Every constituent
  command was run directly and passed; this plan does not claim `make check` passed.
- Two normal M2.2B fixture generations matched at 6,654 bytes and SHA-256
  `6db66f57e197ed491236f530dd33a502bb7baa8e67330084dbb2c2d33f6335e6`.
- Two disposable mixed four-suffix CLI indexes matched at 7,687 bytes and SHA-256
  `d5c3d72d1e61e728db5e7e51bd94d65f0e3b107b412b128f8578884fdc9826d3`.
  The validated result contained 12 nodes, 11 containment edges, and 8 ordered call facts.
  Canonical round-trip, literal callee/owner/span/optional assertions, semantic-edge
  absence, absolute-root/timestamp absence, and source non-execution all passed.
- `git diff --check` — exit 0. The final scope audit confirmed dependencies, lockfiles, CI,
  graph schema/kinds, scanner, CLI production, resolver/later-milestone modules, fixture
  sources, future gold, and all historical gold remained unchanged.

## Independent review transcript

Independent review on Windows on 2026-07-24 found no blocking correctness, determinism,
compatibility, or scope issue:

- `uv lock --check --offline`, `uv sync --dev --locked`, Ruff format check/lint, and mypy
  all exited 0; mypy reported no issues in 37 source files.
- 81 focused call/model/indexer/CLI review tests passed.
- Full pytest reproduced 333 collected, 330 passed, and the same 3 Windows symlink
  privilege skips; total coverage was 93% and the JS-family extractor reported 95%.
- Harness smoke, doctor, and the M1/M2.1B/M2.2A/M2.2B check-only gold helpers all passed.
- `make check` was attempted and remained unavailable because GNU Make is not installed;
  its constituents passed independently. `git diff --check` exited 0.
- The developer completed the learning checkpoint in their own words, distinguishing
  syntax occurrences from resolved edges, static callees from data-flow-dependent forms,
  optional syntax from execution, written aliases from targets, lexical callback ownership
  from invocation order, and the Milestone 3–6 deferred behavior.

No local Windows result is presented as Linux verification.

## Learning checkpoint

Before implementation can be considered complete, the developer must explain in their own
words:

1. Why a written call occurrence is not yet a `calls` graph edge.
2. Why identifier/member callees are defensible while computed and call-result callees
   require data-flow or runtime knowledge.
3. How call type arguments and optional-chain tokens differ across the pinned grammar
   families.
4. Why `is_optional` records syntax but cannot prove whether a call executes.
5. Why import/local aliases are preserved as written rather than resolved during
   extraction.
6. How lexical owner evidence differs from claiming that an outer component synchronously
   invokes a callback-contained call.
7. Why malformed safe siblings may contribute calls while CommonJS still requires
   whole-file suppression.
8. Why facts need complete deterministic sort keys but no stable node ID.
9. How production empty-field omission and exact historical projections preserve M1,
   M2.1A, M2.1B, and M2.2A bytes without hiding current M2.2B behavior.
10. Which call resolution, HTTP, traversal, reporting, query, and MCP behaviors remain
    deferred.

## Deferred questions and later-milestone boundaries

No unresolved question blocks review of this proposal. These require separate decisions:

1. Whether Milestone 3 resolves callback-contained facts directly from the nearest indexed
   owner or introduces a distinct anonymous-scope representation.
2. Whether same-file local calls and cross-file imported calls use one resolver pass or
   separate candidate stages.
3. Whether literal computed members, private methods, parenthesized callees, bound
   functions, callable objects, and call-result chains should ever become static
   candidates.
4. Whether Python gains a parallel direct-call fact channel during Milestone 3.
5. How ambiguous aliases, overloads, inheritance, method dispatch, namespace imports,
   CommonJS exports, and re-exports affect candidate confidence.
6. How `fetch` and Axios calls become HTTP facts and endpoint links in Milestone 4.
7. How call edges feed traversal, overview, queries, context packs, and impact in later
   milestones.

Import/export resolution, cross-file call resolution, graph traversal, Markdown overview
generation, impact analysis, FastAPI/frontend HTTP linking, queries, context packs, MCP,
Milestone 3, and all later behavior are explicitly outside M2.2B.

## Outcome and follow-ups

M2.2B now implements bounded unresolved JS-family call occurrence extraction and addresses
the remaining direct call-fact portion of Milestone 2 without starting resolution or later
product behavior. Local Windows validation is complete with the established three
symlink-privilege skips; independent review and required Linux CI remain pending.

Do not stage, commit, publish, mark the slice complete, or select Milestone 3 during this
implementation handoff. Milestone 2 remains open.
