# Milestone 2.2A — JSX/TSX Foundation and Conservative React Component Extraction

Status: complete and Linux CI verified on 2026-07-20 through PR #5 at implementation
commit `7ffb54879195f61a5c0823222b3c342378357bd4`. Milestone 2 remains open; M2.2B has not
been selected or started.

## Purpose and user-visible outcome

`repolens index PATH` will discover accepted `.jsx` and `.tsx` files, parse them with the
already pinned tree-sitter packages, reuse the completed M2.1A/M2.1B direct extraction
behavior where the grammar shapes agree, and identify a deliberately narrow set of named
React components from direct JSX-return evidence plus an exact runtime React import in the
same file. The output remains a syntax-derived index whose graph edges are direct syntax
facts. Component classification is a bounded convention, not proof that an import resolves
or that React renders the symbol. This slice does not resolve imports, calls, JSX elements,
routes, HTTP requests, or cross-file relationships.

The user-visible addition is one deterministic module and the existing bounded definition
and unresolved-fact set for each accepted JSX/TSX file. A qualifying component is represented
by exactly one existing `react_component` graph node, with its declaration span and normal
containment, rather than both a function/class node and a component node.

This ExecPlan is self-contained and is the approved implementation boundary for M2.2A.
The developer explicitly authorized implementation on 2026-07-20. Milestone 2 remains open.

## Scope and non-goals

### Discovery, parser, and language-label matrix

| Suffix | Parser capsule | Node/file language | Component classification |
| --- | --- | --- | --- |
| `.js` | `tree_sitter_javascript.language()` | `javascript` | disabled; preserve M2.1A/M2.1B bytes |
| `.jsx` | `tree_sitter_javascript.language()` | `jsx` | enabled |
| `.ts` | `tree_sitter_typescript.language_typescript()` | `typescript` | disabled; preserve M2.1A/M2.1B bytes |
| `.tsx` | `tree_sitter_typescript.language_tsx()` | `tsx` | enabled |

Scanner defaults and `JavaScriptTypeScriptExtractor.extensions` add exactly `.jsx` and
`.tsx`. `.mjs`, `.cjs`, declaration files as a special mode, and other suffixes remain out
of scope. Registry lookup remains case-insensitive by suffix and continues to prefer exact
filenames over extensions.

The JavaScript grammar already contains JSX productions, so `.jsx` does not need a new
grammar package. The installed `tree-sitter-typescript` wheel already exposes
`language_tsx()`, which reports the same compatible ABI 14 as `language_typescript()` under
tree-sitter runtime 0.26.0. No dependency or lockfile change is planned.

### Reused M2.1A and M2.1B behavior

One `JavaScriptTypeScriptExtractor` and one shared visitor continue to handle all four
suffixes. Read-only probes against the pinned grammars show that representative functions,
classes, methods, identifier arrows, ESM imports/exports/re-exports, CommonJS forms, and
selected TypeScript declarations have the same TypeScript/TSX shapes. JavaScript and JSX
use the same grammar capsule by construction.

The shared behavior remains:

- one extensionless-path-derived module;
- named function and async-function declarations;
- named class declarations and ordinary named class methods;
- direct identifier variable declarators whose value is an arrow function;
- nearest extracted-parent `contains` edges;
- exact byte-oriented tree-sitter spans and position-derived stable IDs;
- runtime ESM imports, direct exports, and static re-exports with type-only filtering;
- bounded top-level CommonJS occurrence facts and the complete ambiguity guard;
- module-level TypeScript interface, type-alias, and ordinary-enum nodes in `.tsx`;
- deterministic first-error diagnostics and safe-subtree barriers.

Where JSX/TSX introduces a new shape, only a small suffix-aware classification helper is
added. Existing `.js` and `.ts` component classification remains disabled even though the
JavaScript grammar can parse JSX in a `.js` file. Supporting component classification in
`.js` would broaden this slice and rewrite previously supported behavior.

### Exact ordinary definition syntax in `.jsx` and `.tsx`

Before component classification, the supported ordinary definition set is exactly the
completed M2.1A/M2.1B set:

- named `function` and `async function` declarations, including currently supported named
  declarations nested directly in an extracted function, method, or arrow block;
- named class declarations;
- ordinary identifier/property-named class methods, including async methods;
- `const`, `let`, or `var` direct identifier declarators whose value is an arrow function;
- module-level `.tsx` interfaces, type aliases, and ordinary enums.

Constructors, accessors, generators, anonymous function/class expressions, object methods,
callbacks, destructuring arrows, class-field arrows, namespaces/modules, ambient forms,
overload-only signatures, and `const enum` remain excluded or barriers exactly as before.

### Common requirements for a `react_component`

A definition is classified as `react_component` only when all of these are true:

1. The source suffix is `.jsx` or `.tsx`.
2. A function/class declaration is a direct program child or is directly wrapped by a
   top-level `export_statement`. For an arrow, its `variable_declarator` is a direct child
   of a lexical/variable declaration that is itself a program child or directly wrapped by
   a top-level `export_statement`. Nested definitions are never classified in M2.2A.
3. The syntax subtree is error-free.
4. The name is an ordinary identifier matching ASCII `[A-Z][A-Za-z0-9]*`.
5. The file has at least one error-free, top-level, non-type-only static ESM import from the
   exact source string `react` that contributes a default, namespace, or named runtime
   binding. A side-effect-only import, an empty named clause, and type-only specifiers do
   not establish this file-level React evidence.
6. The definition matches one exact function, arrow, or class rule below.

PascalCase is necessary but explicitly insufficient. A PascalCase helper without direct JSX
return evidence remains an ordinary `function` or `class` node. Conversely, a lowercase
function that directly returns JSX remains an ordinary function because lowercase JSX
identifiers have different React semantics and the rule must avoid guessing intent.

The runtime-import requirement deliberately trades recall for an honest framework label.
React automatic-runtime files with no written runtime import are false negatives in this
slice. JSX files using Preact, Solid, or a custom JSX factory do not become
`react_component` nodes merely because they use PascalCase and return JSX.

### Direct JSX-return evidence without control-flow analysis

The only JSX evidence expressions are grammar nodes of type `jsx_element` or
`jsx_self_closing_element`. Under the pinned JavaScript and TSX grammars, fragment syntax
`<>...</>` is represented as a `jsx_element` whose opening/closing tag has no name, so
fragments are supported without a separate guessed node type.

An evidence expression may be wrapped by one or more `parenthesized_expression` nodes.
No other wrapper is transparent. In particular, conditional, logical, sequence, `as`,
`satisfies`, call, identifier, await, and assignment expressions are not searched for JSX.

For a statement block, inspect only its direct named children. It qualifies only when it
has exactly one direct `return_statement` and that return's expression becomes a JSX
evidence expression after unwrapping parentheses. Do not descend into `if`, `switch`,
loops, `try`, nested functions, callbacks, or local variables to infer a returned value.
This is bounded syntax inspection, not control-flow or call analysis.

### Exact supported function components

A top-level named non-generator, non-async `function_declaration` becomes a component when
its PascalCase name and body satisfy the direct block-return rule. Parameter destructuring,
TypeScript parameter annotations, return-type annotations, and generic parameters do not
affect classification because they remain inside the declaration span. The common runtime
React import requirement above still applies.

Supported examples include:

```tsx
export function ProfileCard({ id }: { id: string }) {
  return <h2>{id}</h2>;
}

export default function Panel() {
  return (<><span /></>);
}
```

Async functions remain ordinary function nodes even if they contain JSX. M2.2A does not
infer client/server component semantics or Promise-return compatibility.

### Exact supported arrow components

A top-level direct identifier `variable_declarator` whose value is a non-async arrow
function becomes a component when its name is PascalCase and either:

- its expression body is JSX after parenthesis unwrapping; or
- its statement block satisfies the exact direct block-return rule.

The node span remains the entire `variable_declarator`, matching the existing arrow span
policy. Multiple declarators in one top-level declaration are considered independently.
Under the pinned TSX grammar both `<T>(value: T) => ...` and
`<T,>(value: T) => ...` are eligible when the initializer is actually an error-free
`arrow_function`. Classification never reparses angle-bracket text or guesses through an
ERROR/JSX-shaped ambiguous tree.

Supported examples include:

```jsx
export const Card = () => <main />;
const Panel = () => { return (<section />); };
```

Function expressions, destructured bindings, `memo(...)`, `forwardRef(...)`, and any other
call-wrapped or computed initializer remain unsupported because recognizing them would
require wrapper/call semantics.

### Exact supported class components

A top-level named class becomes a component only when all of the following direct evidence
is present in one complete file:

- its name is PascalCase;
- its direct superclass is a runtime React `Component` or `PureComponent` binding proven by
  a top-level, non-type-only static import whose source string is exactly `react`;
- it has exactly one direct, ordinary instance method named `render`;
- that `render` method is not static, async, generator, accessor, abstract, optional, or a
  class-field arrow, and its body satisfies the direct block-return rule.

When counting `render`, any additional direct class member named `render` makes the class
ineligible, including a `method_signature`, `abstract_method_signature`, accessor,
class-field definition, or second method definition. This prevents an overload/signature
neighbor from being ignored while one implementation silently qualifies the class.

The accepted superclass/import pairs are:

- `import React from "react"` or `import * as React from "react"`, followed by
  `extends React.Component` or `extends React.PureComponent`;
- `import { Component } from "react"` or `import { PureComponent } from "react"`, followed
  by the corresponding bare local name;
- a named import alias such as `import { Component as Base } from "react"`, followed by
  `extends Base`.

TSX type arguments on the heritage, such as `extends React.Component<Props, State>`, are
transparent because the pinned grammar keeps the runtime base in the `extends_clause`
`value` field. Type-only React imports do not supply runtime evidence. CommonJS React
requires, re-exported aliases, `preact`, locally defined lookalikes, unresolved bare
`Component`, and indirect base classes are not accepted.

The React-import audit is a program-level prepass so source order cannot affect the result.
Because that audit must be complete, class component classification is disabled for a file
whose root has any ERROR or missing node. An otherwise safe class remains an ordinary class
node in that partial result. Function and arrow classification needs no whole-file binding
audit and may survive in a separate error-free top-level sibling.

### Nested definitions, callbacks, and anonymous/default forms

- Top-level declarations directly wrapped in `export_statement` are still top-level.
- A named function, class, or arrow nested under an already extracted function/method/arrow
  remains eligible for its ordinary M2.1A node kind but never `react_component` in M2.2A.
- Callback arrows and definitions inside anonymous functions/classes remain behind the
  existing scope barriers and produce no node.
- Named default function/class declarations may qualify.
- Anonymous default functions/classes, anonymous default arrows, and inferred names from
  assignment/property/call context remain deferred because they lack the exact declared
  identity required by the stable-ID contract.

### Component representation, spans, containment, and IDs

A qualifying symbol produces one node only:

- function and arrow components use `NodeKind.REACT_COMPONENT` instead of
  `NodeKind.FUNCTION`;
- class components use `NodeKind.REACT_COMPONENT` instead of `NodeKind.CLASS`;
- no parallel ordinary node, classification edge, JSX node, or component fact is emitted.

Function/class component spans cover the exact declaration. Arrow component spans cover the
exact `variable_declarator`. Qualified names use the existing module parent, for example
`src.ProfileCard.ProfileCard` is not invented; `src.ProfileCard` is the module and
`src.ProfileCard.ProfileCard` is the component only when the path and symbol share a name,
following the existing `<module>.<definition>` rule.

The component ID calls `stable_node_id` with `NodeKind.REACT_COMPONENT`, normalized source
path, qualified name, declaration start line, and `column:<start-column>`. Classification
therefore intentionally changes a would-be ordinary function/class ID. This is honest
semantic identity, not ID continuity. The body, JSX tag names, React import alias, and
parser traversal order do not enter the ID.

For a class component, supported ordinary methods remain `method` nodes contained directly
by the component node. Every component receives exactly one syntax-direct confidence-1.0
`contains` edge from its module. Existing direct ESM export facts continue to use the local
declaration name and do not depend on the node kind.

The visitor must preserve traversal by syntax form after choosing the graph kind. In
particular, a `class_declaration` reclassified as `react_component` must still take the
existing class-body/method path; it must not fall through the current non-class branch just
because its selected graph kind is no longer `class`. Function and arrow component bodies
likewise retain their existing nested ordinary-definition traversal.

### Strict non-goals

- no general call extraction or call-target resolution;
- no import/export target resolution or dependency traversal;
- no React hook semantics;
- no props, state, context, ref, or data-flow analysis;
- no JSX element/attribute/text/expression graph;
- no frontend route extraction;
- no HTTP, `fetch`, or Axios extraction;
- no FastAPI or endpoint linking;
- no overview, context, ranking, or impact behavior;
- no MCP behavior;
- no Milestone 3 work;
- no M2.2B implementation or selection.

## Current state

- On 2026-07-20, `main`, `origin/main`, and `HEAD` are synchronized at
  `1ced144fc84f529c48f318b9380f630cd0d283cf`; the pre-plan working tree is clean.
- M2.1A and M2.1B are complete and Linux CI verified. Milestone 2 remains open.
- Scanner defaults currently accept `.js`, `.md`, `.py`, and `.ts` plus the three exact
  project metadata basenames. `.jsx` and `.tsx` are currently absent before file nodes,
  source loading, registry lookup, and parser selection.
- `ExtractorRegistry` already lowercases suffix lookup. The existing JS/TS extractor is
  registered once and currently declares exactly `.js` and `.ts`.
- The extractor has one shared visitor, exact source spans, source-position IDs, scope/error
  barriers, unresolved ESM/CommonJS/re-export channels, and selected TS declarations. Its
  parser selector currently has only `.js` and `.ts` branches.
- `NodeKind.REACT_COMPONENT` already exists. `GraphNode`, `GraphSnapshot`, canonical JSON,
  and old-payload parsing need no new field, enum value, channel, or schema version.
- `RepositoryIndexResult` already sorts every unresolved channel and conditionally omits
  empty post-M1 fields. No component-specific top-level field is needed.
- The indexer file-language map currently handles `.js` as `javascript` and `.ts` as
  `typescript`; `.jsx`/`.tsx` labels must be added.
- CLI output counts imports and warnings but has no component count. No CLI production
  change is required for this slice; the component is already included in the node count.
- Pinned/locked versions remain tree-sitter 0.26.0, JavaScript grammar 0.25.0, and
  TypeScript grammar 0.23.2. The runtime supports grammar ABI 13–15; JavaScript reports ABI
  15 and both TypeScript/TSX capsules report ABI 14.
- The `typescript_frontend` fixture already contains `src/ProfileCard.tsx` and is the owner
  of M2.1A partial gold. The full-stack fixture contains
  `frontend/src/TaskPanel.tsx`. Their future `gold.json` records include later call and
  resolver behavior and must not be overwritten by this extraction slice.
- Historical M1 acceptance copies fixtures under a post-Milestone `.gitignore` containing
  only `*.js` and `*.ts`; that profile and its updater must add `*.jsx`/`*.tsx` when support
  is implemented so all four M1 gold files remain byte-identical.
- The current M2.1A compatibility projection removes M2.1B node kinds/channels but indexes
  the original TS frontend repository. It must additionally apply an exact historical
  `.jsx`/`.tsx` source exclusion before comparing unchanged M2.1A bytes.
- The isolated M2.1B repository contains only `.js` and `.ts`, so its source set and gold
  should remain byte-identical without a behavior projection.

## Acceptance criteria

1. Scanner defaults, extractor extensions, and registry selection add exactly case-folded
   `.jsx` and `.tsx`; `.mjs`, `.cjs`, and unrelated suffixes remain excluded.
2. `.jsx` uses `Language(tree_sitter_javascript.language())`; `.tsx` uses
   `Language(tree_sitter_typescript.language_tsx())`; installed dependency declarations
   and `uv.lock` remain unchanged.
3. File/module/definition language labels are exactly `jsx` for `.jsx` and `tsx` for `.tsx`.
   Module names remain extensionless path-derived names.
4. Representative non-JSX source produces the same supported semantic facts under
   `.js`/`.jsx` and `.ts`/`.tsx`, aside from suffix-derived paths, IDs, and language labels.
5. Existing M2.1A/M2.1B definitions, ESM facts, CommonJS guards, TS declaration behavior,
   type-only filtering, and unsupported-scope barriers work in `.jsx`/`.tsx` where their
   pinned grammar shapes permit.
6. Every exact top-level function, arrow, and class component form in this plan produces
   exactly one `react_component` node with the exact declaration/declarator span, qualified
   name, stable component ID, and module containment.
7. A qualifying class component's supported methods are contained by the single component
   node; no duplicate `class` or `function` node exists for any component.
8. PascalCase without exact JSX-return evidence, and JSX-return evidence without a valid
   PascalCase top-level name or without the exact file-level runtime React import evidence,
   produce only the applicable ordinary definition node.
9. Direct elements, self-closing elements, fragments, and repeated parentheses are
   supported. Conditional/call/identifier/alias/`as`/`satisfies` return inference and
   nested control-flow search are absent.
10. Runtime React class bases are recognized only from the exact static imports and direct
    heritage forms in this plan. Type-only, CommonJS, local lookalike, re-exported, and
    indirect bases do not qualify.
11. Named default declarations may qualify. Anonymous defaults, call-wrapped arrows,
    callbacks, and nested definitions never become components.
12. Function/arrow component facts may survive in an error-free top-level sibling of a
    malformed subtree when an error-free top-level runtime React import supplies the common
    file-level evidence. An erroneous candidate is omitted, diagnostics remain stable, and
    class component classification is suppressed when the program-wide React binding audit
    is incomplete. Existing whole-file CommonJS suppression remains unchanged.
13. No JSX element node, call/import/export target edge, hook/props/state fact, route, HTTP
    fact, endpoint link, traversal result, report, or MCP behavior is created.
14. Nodes and edges retain explicit sorting. Repeated extraction, reversed discovery, model
    round-trip, repeated gold generation, and repeated CLI indexing are byte-identical and
    contain no absolute temporary paths, timestamps, or environment-specific content.
15. All four M1 gold files, `m2-1a-graph.json`, and `m2-1b-graph.json` remain byte-identical.
    Compatibility helpers may exclude only the named post-milestone source/kind/channel
    additions documented in this plan and may not alter production indexing.
16. `typescript_frontend/m2-2a-graph.json` records the normal current partial output for
    `api.ts`, `ProfileCard.tsx`, and `tsconfig.json`. The existing future `gold.json`,
    fixture sources, manifests, questions, and diffs remain unchanged.
17. The full-stack fixture supplies a semantic integration assertion for `TaskPanel.tsx`
    without adding a second M2.2A gold or claiming later call/HTTP/FastAPI behavior.
18. Focused tests, complete JS/TS-family tests, scanner/indexer/CLI/model/M1 regressions,
    M2.1A and M2.1B compatibility checks, new partial gold, full pytest, harness smoke,
    doctor, repeated-byte/privacy/non-execution checks, and `git diff --check` pass.
19. Linux success is claimed only after the implementation commit's required GitHub
    Actions check passes. Local Windows symlink privilege skips remain reported separately.
20. Documentation records exact delivered behavior and the developer completes the
    learning checkpoint. M2.2A completion must not mark all of Milestone 2 complete or
    select M2.2B.

## Milestone phases

### Phase 0 — Approval gate

Review this plan and resolve any requested scope changes. Do not create a feature branch or
modify behavior until the developer explicitly authorizes M2.2A implementation. At
authorization time, reconfirm clean `main`, `origin/main`, the base commit, and the expected
file set before creating a dedicated branch.

### Phase 1 — Hand-authored tests and grammar contract

Add manually authored failing tests before behavior. Verify the four parser capsules and
ABIs, suffix routing, exact JSX evidence nodes, React import/heritage shapes, and the full
positive/negative matrix below. Keep expected IDs and spans literal for representative
Unicode/multiline cases rather than deriving every expectation from production helpers.

Expected test paths:

- new `tests/test_jsx_tsx_react_components.py` for focused M2.2A syntax/classification;
- `tests/test_javascript_typescript_extractor.py` for shared-behavior and compatibility;
- `tests/test_scanner.py`, `tests/test_indexer.py`, and `tests/test_cli.py` for integration;
- `tests/test_milestone1_acceptance.py` for the historical source profile.

No production change is complete until the corresponding tests fail for the intended
missing behavior and pass after the focused implementation.

### Phase 2 — Discovery and parser foundation

Add `.jsx`/`.tsx` to scanner defaults and the existing extractor extension set. Add
`_JSX_LANGUAGE` as the existing JavaScript language object (or an explicit alias to it),
`_TSX_LANGUAGE = Language(tree_sitter_typescript.language_tsx())`, and one exact suffix
selector returning parser language plus `javascript`/`jsx`/`typescript`/`tsx` label and a
component-classification flag.

Extend the indexer file-language map. Reuse every current visitor path for the new suffixes
and add parity tests before adding React classification. Do not change dependencies,
`ExtractionResult`, `RepositoryIndexResult`, graph schema, serialization, or CLI counts.

Expected production paths:

- `src/repolens/scanner.py`;
- `src/repolens/extractors/javascript_typescript.py`;
- `src/repolens/indexer.py`.

### Phase 3 — Conservative component classification

Add small internal helpers for ASCII component names, parenthesis-only JSX evidence,
direct block returns, async/static/accessor/generator exclusions, top-level position, and
runtime React import/base prepasses. Select `NodeKind.REACT_COMPONENT` before calling the
existing definition builder so only one node and one stable ID are created. Refactor the
builder's body traversal to key off the syntax form rather than the selected graph kind, so
reclassified classes retain ordinary method children and reclassified function/arrows
retain their existing nested-definition behavior.

Keep component detection linear in the current syntax tree. Do not add a generic JSX walk,
symbol table, call walker, resolver, data-flow engine, or component fact model. Preserve
ordinary definition visitation and export collection after selecting the node kind.

### Phase 4 — Compatibility and partial gold

Extend the M1 historical ignore profile in both the acceptance test and updater to:

```text
*.js
*.ts
*.jsx
*.tsx
```

The M2.1A compatibility test must index a temporary copy of `typescript_frontend/repo` with
only `*.jsx` and `*.tsx` excluded, then apply the existing narrowly named M2.1B additive
projection. It must compare every remaining canonical byte to the unchanged
`m2-1a-graph.json`. Production always indexes the normal source set.

Run the existing M2.1B isolated updater/check twice and assert `m2-1b-graph.json` is
unchanged. Add a check-by-default, explicit-`--update`
`scripts/update_m2_2a_acceptance_gold.py` for
`harness/fixtures/typescript_frontend/m2-2a-graph.json`. It indexes the existing fixture
repository normally, validates model round-trip, and writes LF UTF-8 with one final newline
only under `--update`.

Do not edit fixture source, manifests, future `gold.json`, questions, diffs, M1 gold,
M2.1A gold, or M2.1B source/gold.

### Phase 5 — Documentation, full validation, and Linux handoff

After implementation and review, update `CODEX.md`, `README.md`, this ExecPlan, and
`docs/INTERVIEW_QUESTIONS.md` with verified decisions, data flow, limitations, exact local
results, discoveries, and the learning checkpoint. Run every validation command
sequentially on Windows, because concurrent pytest coverage processes can contend for
`.coverage`. Perform repeated gold/CLI byte comparisons and path/non-execution checks.

Publish only after a separate final review authorizes it. Record Linux CI only from the
required GitHub Actions job for the implementation commit. Stop with Milestone 2 still open
and do not select or begin M2.2B.

## Invariants and contracts

### Planned contract changes

| Contract | Planned additive change |
| --- | --- |
| Scanner | Default eligible suffixes add `.jsx` and `.tsx`. |
| Extractor registry surface | `JavaScriptTypeScriptExtractor.extensions` becomes exactly `.js`, `.jsx`, `.ts`, `.tsx`. |
| Parser selection | `.jsx` routes to JavaScript grammar; `.tsx` routes to TSX grammar. |
| Language labels | File/module/definition labels add `jsx` and `tsx`. |
| Node semantics | Exact qualifying declarations use the existing `react_component` kind instead of an ordinary function/class kind. |
| Stable identity | Component IDs use the existing v1 algorithm with `react_component` as the kind. |
| Compatibility harness | Historical test profiles exclude new suffixes; a new M2.2A partial gold is added. |

No new dependency, lock entry, `NodeKind`, graph field, edge kind, evidence kind,
`ExtractionResult` channel, `RepositoryIndexResult` channel, schema version, CLI command,
or serialized empty field is planned. `pyproject.toml`, `uv.lock`, graph models, extractor
base contracts, canonical serialization, and CI configuration should remain unchanged.

### Determinism

- Normalize source paths through the existing POSIX repository-relative helper.
- Use tree-sitter byte points directly: lines are one-based; columns remain zero-based
  UTF-8 byte offsets; end positions are exclusive.
- Sort nodes by source position in extraction and by ID at `GraphSnapshot`; sort edges by
  their complete semantic key. No new collection relies on set iteration.
- Component eligibility depends only on suffix and exact syntax in the same source file.
- React import aliases are collected into normalized sets before visitation; source order
  does not affect classification.
- IDs exclude JSX contents, import aliases, timestamps, roots, parser objects, traversal
  index, and filesystem order.
- Canonical JSON remains recursive key-sorted UTF-8 with compact separators and one final
  newline.

### Security and architectural boundaries

- Use only the source string already loaded by the indexer and the pinned in-process parser.
- Never run Node, npm, React, TypeScript, package scripts, JSX transforms, imported modules,
  or indexed source.
- Never access a network or installed target package to decide whether `react` exists.
- A written static import from the exact module string `react` is syntax evidence only; it
  is not import resolution and creates no target node/edge.
- Do not inspect `package.json`, tsconfig JSX mode, or dependency installation to classify
  a component.
- Do not create `CALLS`, `IMPORTS`, `EXPORTS`, `INHERITS`, endpoint, route, JSX, or heuristic
  edges.
- Existing scanner ignore, containment, symlink, size, count, repository-byte, output-prune,
  and diagnostics rules apply unchanged to the new suffixes.
- Component detection is bounded to top-level candidate declarations, direct block
  children, class body members, and one program-level React import prepass. Complexity is
  linear in syntax-tree size and does not recurse through JSX content.

### Partial-tree behavior

- Always emit the module for a returned parse tree.
- Keep the deterministic first ERROR/missing-node diagnostic.
- Do not visit an erroneous/missing candidate or cross an existing unsupported-scope
  barrier.
- Error-free top-level function/arrow components and ordinary facts may survive beside an
  unrelated malformed subtree when an error-free top-level runtime React import supplies
  their file-level framework evidence.
- Disable class component classification when any root error makes the program-wide React
  import audit incomplete; preserve any defensible ordinary class node.
- Preserve M2.1B's stricter whole-file suppression for CommonJS facts.
- Never add regex fallback or parser exception text to deterministic output.

### Type-only and runtime distinctions

- Reuse statement-level and inline type-only ESM filtering exactly.
- `.tsx` interfaces and type aliases are declaration nodes but never component/runtime
  export facts. Ordinary exported enums retain their current runtime export behavior.
- Type annotations such as `React.FC`, `JSX.Element`, props types, or generics never prove a
  component by themselves.
- Type-only React imports cannot establish file-level functional-component evidence or a
  runtime class base. Mixed imports contribute only their runtime bindings.
- Component classification does not imply that JSX compiles, React is installed, an export
  resolves, or a component is ever rendered.

## Test and harness plan

### Manually authored test matrix

| Area | Positive cases | Negative/boundary cases |
| --- | --- | --- |
| Parser/ABI | JS grammar parses JSX; TSX capsule parses types plus JSX; ABI 15/14 accepted by runtime 0.26 | `.ts` JSX reports syntax error; unsupported suffix rejected |
| Discovery/registry | mixed-case `.JSX`/`.TSX`; ignore, limits, output pruning, contained file symlink | `.mjs`, `.cjs`, arbitrary suffix; ignored/oversize/outside symlink absent |
| Shared definitions | `.jsx`/`.tsx` named functions, async functions, classes, methods, arrows, nested ordinary definitions | constructors, accessors, generators, object methods, destructuring, callbacks, anonymous barriers |
| Shared facts | runtime ESM imports/exports/re-exports, exact CommonJS, TSX interface/type/enum | type-only ESM, dynamic modules, shadowed/partial CommonJS, ambient/const-enum/namespaces |
| Function components | Runtime React import plus PascalCase top-level/named-default function with one direct JSX element, self-closing element, or fragment return; typed/generic parameters | missing/side-effect-only/type-only/wrong-framework import; lowercase; PascalCase without JSX; async/generator; nested/callback; conditional/call/identifier/alias return; anonymous default |
| Arrow components | Runtime React import plus PascalCase top-level identifier arrow with direct expression JSX or exact block return; multiple declarators; pinned `<T>` and `<T,>` TSX generic-arrow forms | missing/type-only/wrong-framework import; async; destructuring; function expression; `memo`/`forwardRef`; conditional/logical/call-wrapped initializer; nested or erroneous/ambiguous generic arrow |
| Class components | Exact listed default/namespace React bindings plus named/aliased runtime imports; `Component`/`PureComponent`; TSX type arguments; one direct render JSX return; named/default export declarations | missing/wrong/type-only/CommonJS/preact import; local lookalike; indirect base; static/async/generator/accessor/optional/field/signature/overload/multiple render; partial program |
| JSX evidence | nested elements, self-closing elements, pinned fragment shape, repeated parentheses | JSX only in local variable, callback, nested control flow, `React.createElement`, `as`/`satisfies`, conditional body |
| Representation | exactly one component node; class methods and nested ordinary definitions contained by it; direct/list/default export facts retained for reclassified declarations | no duplicate function/class node; no classification/JSX/inherits/call edge |
| IDs/spans | literal function/class/declarator spans; same-line duplicates; Unicode before declaration proves byte columns; literal component ID | absolute/parent paths rejected; IDs independent of JSX/tag/import alias and traversal order |
| Partial trees | safe runtime React import plus safe function/arrow sibling survives; erroneous candidate omitted; stable first diagnostic | class classification and all CommonJS facts suppressed when whole-program audits are unsafe |
| Indexer/CLI/security | `jsx`/`tsx` file labels, node counts, canonical JSON, two identical CLI runs, source sentinel remains absent | no absolute temporary path/timestamp; no subprocess/network/React execution; no target graph edges |
| Fixtures/gold | `ProfileCard` partial gold and `TaskPanel` semantic assertion | future `gold.json` and historical M1/M2.1A/M2.1B bytes unchanged |

Tests must assert both presence and absence. A generated gold file is not sufficient evidence
without literal semantic assertions for names, kinds, spans, containment, import/type
filtering, lack of target edges, and source non-execution.

### Compatibility and gold strategy

1. **M1:** Keep all four committed `m1-graph.json` files byte-identical. Extend only the
   temporary historical ignore profile in the M1 acceptance test/updater to exclude all
   four post-M1 JS-family suffixes.
2. **M2.1A:** Keep `typescript_frontend/m2-1a-graph.json` byte-identical. Use a temporary
   fixture copy with `.jsx`/`.tsx` ignored, run the normal current indexer, apply only the
   existing named M2.1B additive projection, and compare every canonical byte.
3. **M2.1B:** Keep the isolated `m2-1b-repo`, updater, and `m2-1b-graph.json` unchanged.
   Check it twice because adding extractor suffixes must not perturb `.js`/`.ts` output.
4. **M2.2A:** Add `typescript_frontend/m2-2a-graph.json` generated from the existing
   `typescript_frontend/repo`. It is explicitly a current partial extraction snapshot, not
   the future resolver/query `gold.json` and not a claim that calls or React semantics are
   complete.
5. **Full-stack:** Index the existing full-stack fixture in a focused semantic test and
   assert the `TaskPanel` component plus unchanged currently supported facts. Do not add a
   second partial gold or overwrite full-stack future expectations.
6. **Portability:** Every new/checked fixture source and gold byte is LF UTF-8, relative
   POSIX paths only, no timestamp/root/environment text, sorted canonically, round-trip
   valid, and identical across two generations.

## Exact validation commands

Run pytest commands sequentially from `C:\RepoLens`:

```text
uv lock --check --offline
uv sync --dev --locked
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest tests/test_jsx_tsx_react_components.py -v
uv run pytest tests/test_javascript_typescript_extractor.py -v
uv run pytest tests/test_scanner.py -v
uv run pytest tests/test_indexer.py -v
uv run pytest tests/test_cli.py -v
uv run pytest tests/test_models.py -v
uv run pytest tests/test_milestone1_acceptance.py -v
uv run pytest tests/test_javascript_typescript_extractor.py::test_typescript_frontend_matches_separate_m21a_partial_gold -v
uv run pytest tests/test_javascript_typescript_extractor.py::test_m21b_isolated_partial_gold_matches_semantics_and_repeated_generation -v
uv run pytest tests/test_jsx_tsx_react_components.py::test_m22a_typescript_frontend_partial_gold_matches_semantics_and_repeated_generation -v
uv run pytest
uv run repolens harness-smoke
uv run repolens doctor
uv run python scripts/update_m1_acceptance_gold.py
uv run python scripts/update_m2_1b_acceptance_gold.py
uv run python scripts/update_m2_2a_acceptance_gold.py
make check
git diff --check
git status --short
```

`make check` is the repository-level acceptance command and must be attempted and reported
exactly. If GNU Make is unavailable in the Windows shell, record that tool failure without
claiming the aggregate ran; the individually listed format, lint, type-check, full-test,
and harness commands above still supply the constituent evidence before Linux CI runs the
real target.

Also index a disposable mixed `.js`/`.jsx`/`.ts`/`.tsx` repository twice through the CLI,
compare exact bytes and SHA-256, parse both outputs, assert expected component/node/fact
counts, assert no `IMPORTS`/`EXPORTS`/`CALLS`/`INHERITS` edges, search for the absolute
temporary root and timestamp keys, verify a harmless source-execution sentinel was not
created, and remove the scratch repository.

Record exact pass/skip/coverage totals. On Windows, identify the existing three real-symlink
skips as a local privilege limitation. After publication, wait for the required Linux CI
check and record its exact commit, run, job, duration, and URL; do not infer Linux success
from local commands.

## Failure modes

- **Wrong parser capsule:** `.tsx` is sent to `language_typescript()` and valid JSX becomes
  an ERROR tree. Exact parser-selection tests must fail first.
- **Shared-shape overconfidence:** a JSX/TSX grammar node differs from JS/TS. Keep shared
  traversal only for probed shapes and add suffix-specific handling rather than broad
  fallback.
- **PascalCase-only false positives:** ordinary UI helpers become components. Require exact
  direct JSX evidence.
- **Non-React JSX false positives:** Preact, Solid, or custom-factory JSX is labeled React.
  Require a top-level runtime binding import from exact source `react`; accept the resulting
  automatic-runtime false negatives rather than infer framework configuration.
- **Deep JSX search:** JSX inside callbacks, conditionals, variables, or calls is treated as
  a returned component. Unwrap parentheses only and inspect direct returns only.
- **Fragment drift:** code assumes a `jsx_fragment` type that the pinned grammar does not
  emit. Test the actual no-name `jsx_element` representation.
- **Wrapper semantics creep:** `memo`, `forwardRef`, HOCs, `React.createElement`, or aliases
  are inferred as components. Keep them explicit non-goals.
- **Class lookalike false positives:** any `Component` superclass qualifies. Require the
  complete runtime import/base/render evidence and suppress on incomplete program audit.
- **Type/runtime conflation:** `import type`, `React.FC`, interfaces, or type aliases are
  treated as runtime component evidence. Preserve the runtime filters.
- **Duplicate symbol identity:** both ordinary and component nodes are emitted. Select one
  kind before node construction and assert one node/one containment edge.
- **Unstable reclassification ID:** a component retains the ordinary function/class ID.
  Use `react_component` in the existing stable-ID input and document intentional ID change.
- **Nested-scope leakage:** callbacks or nested definitions become module components. Gate
  classification on exact program/export parentage and retain scope barriers.
- **Partial-tree overclaim:** a broken file supplies incomplete React imports or a broken
  candidate. Require error-free candidate subtrees and a complete root for class audit.
- **Historical gold drift:** newly discovered TSX changes M1/M2.1A bytes. Use only the
  explicit test input profiles/projection and compare immutable files before/after.
- **Future-gold contamination:** the extraction snapshot overwrites resolver/query
  `gold.json`. Add only the named `m2-2a-graph.json` sibling.
- **Serialization/privacy drift:** path roots, CRLF, timestamps, enumeration order, or
  unsorted aliases enter output. Repeat bytes on Windows and Linux with explicit privacy
  assertions.
- **Accidental execution/resolution:** classification imports React, invokes Node, reads
  packages, or resolves targets. Block subprocess/network entry points and use syntax only.
- **Scope growth:** call, hook, props/state, route, HTTP, endpoint, traversal, report, MCP,
  or Milestone 3 behavior appears in the diff. Treat it as a release blocker.

## Decisions

- **2026-07-20 — Use JavaScript grammar for `.jsx` and TSX grammar for `.tsx`.** The
  JavaScript wheel includes JSX nodes; the TypeScript wheel exposes a separately verified
  `language_tsx()` capsule. Parsing TSX with the TypeScript-only capsule is incorrect.
- **2026-07-20 — Share the existing visitor with narrow shape adapters.** JavaScript/JSX
  use one grammar, and pinned TypeScript/TSX probes produced identical trees for all current
  non-JSX forms. Class heritage already differs between the JS and TS grammar families, so
  the new React-base helper must handle both exact shapes rather than assuming one.
- **2026-07-20 — Classify only exact top-level named function, arrow, and class forms.**
  This covers the fixture and common direct declarations while retaining a reviewable
  boundary around identity and scope.
- **2026-07-20 — PascalCase alone is insufficient.** It is only a name gate. Function and
  arrow components also need direct JSX return evidence; classes need runtime React base
  evidence and an exact render return.
- **2026-07-20 — Require written runtime React evidence for every component form.** JSX
  syntax is shared by React, Preact, Solid, and custom factories. A top-level runtime binding
  import from exact source `react` keeps the `react_component` label conservative; React
  automatic-runtime files without such an import remain explicit false negatives.
- **2026-07-20 — Detect JSX returns structurally, not by control flow or calls.** Only direct
  expression bodies or exactly one direct block return count; parentheses are transparent
  and all other expression/control wrappers are opaque.
- **2026-07-20 — Keep function, arrow, and class evidence distinct.** Functions use a
  declaration body, arrows use an expression body or block plus declarator span, and classes
  require a complete import/base/render audit and retain method children.
- **2026-07-20 — Support named defaults; defer anonymous defaults.** A declared name supplies
  the qualified name and stable identity. Inferred anonymous identities need a separate
  policy and broader export/assignment semantics.
- **2026-07-20 — Keep nested definitions ordinary and callbacks behind barriers.** This
  avoids treating locally recreated definitions or anonymous callback scopes as module
  components while preserving existing ordinary extraction.
- **2026-07-20 — Support fragments and parenthesized JSX.** Pinned fragments are no-name
  `jsx_element` nodes, and repeated parentheses can be unwrapped without semantic analysis.
- **2026-07-20 — Represent a component with one node kind.** `react_component` replaces the
  would-be ordinary kind for the declaration; no duplicate node or classification edge is
  needed.
- **2026-07-20 — Let classification participate in stable identity.** The node ID uses
  `react_component`; changing whether a declaration satisfies the rule may change its ID,
  which is more honest than preserving an ID for a different semantic kind.
- **2026-07-20 — Protect historical bytes with explicit test input boundaries.** M1 ignores
  all post-M1 JS-family suffixes; M2.1A temporarily ignores JSX/TSX then applies only the
  existing M2.1B projection; M2.1B isolated gold must match without projection.
- **2026-07-20 — Let `typescript_frontend` own M2.2A partial gold.** Its existing
  `ProfileCard.tsx`, `api.ts`, and tsconfig are minimal and already anchor the earlier TS
  partial snapshots. Full-stack remains a semantic integration check only.
- **2026-07-20 — Keep unsupported React semantics explicit.** Wrapper calls, hooks,
  props/state flow, indirect/alternate class bases, conditional returns, JSX graphs,
  calls/routes/HTTP, and resolution remain deferred rather than approximated.

## Unresolved design questions

No unresolved question blocks the proposed M2.2A boundary. The following are intentionally
deferred and require a separately reviewed future slice before support:

1. Whether named nested JSX-returning definitions should ever be components rather than
   ordinary definitions.
2. How to assign stable identities to anonymous default exports and call-wrapped
   `memo`/`forwardRef` components.
3. Whether component evidence should later include `null`, strings, arrays, portals,
   `React.createElement`, conditional/logical returns, or values returned through aliases.
4. Whether class components may use CommonJS React, `preact/compat`, re-exported bases, or
   indirect subclasses without import resolution.
5. Whether `.js` files containing JSX should opt into component classification; M2.2A is
   suffix-gated to protect the completed `.js` contract.
6. Whether a later typed component-fact/evidence channel is useful once ranking/query
   features need the exact JSX-return evidence span. M2.2A needs no new channel.
7. Whether a later project/framework configuration slice should recognize React's automatic
   JSX runtime without a written runtime `react` import; M2.2A intentionally does not infer
   that configuration.

## Progress

- [x] 2026-07-20: Confirmed clean synchronized `main`, `origin/main`, and `HEAD` at
  `1ced144fc84f529c48f318b9380f630cd0d283cf`.
- [x] 2026-07-20: Read `AGENTS.md`, `CODEX.md`, `.agent/PLANS.md`, both completed M2.1
  ExecPlans, `README.md`, and `docs/INTERVIEW_QUESTIONS.md` in full.
- [x] 2026-07-20: Audited scanner, registry, JS/TS extractor, graph/ID/serialization
  contracts, indexer, CLI, focused tests, M1/M2 gold helpers, TypeScript/full-stack frontend
  fixtures, future gold, and pinned package records.
- [x] 2026-07-20: Ran read-only pinned grammar probes for JSX/TSX return, fragment,
  parenthesis, class heritage/import, named/anonymous default, nested/callback, generic
  arrow, and M2.1 parity shapes.
- [x] 2026-07-20: Defined the proposed scope, acceptance criteria, contracts, phases, test
  matrix, compatibility strategy, failure modes, and learning checkpoint.
- [x] 2026-07-20: Independent planning review corrected the arrow top-level parent shape,
  required runtime React evidence for every component form, made class-method traversal
  independent of the selected graph kind, bounded render signatures/overloads and TSX
  generic arrows explicitly, and restored the required `make check` attempt.
- [x] 2026-07-20: Developer explicitly approved the reviewed M2.2A implementation scope.
- [x] 2026-07-20: Created `m2-2a-jsx-tsx-react-components` from the synchronized approved
  base `1ced144fc84f529c48f318b9380f630cd0d283cf` without altering the planning delta.
- [x] 2026-07-20: Phase 1 — Added hand-authored routing, parity, component-boundary,
  compatibility, security, privacy, determinism, fixture, ID/span, and partial-tree tests.
  The focused pre-implementation run collected 33 cases: the 2 locked-parser/control cases
  passed and the expected 31 behavior cases failed against absent JSX/TSX support.
- [x] 2026-07-20: Phase 2 — Added exactly `.jsx`/`.tsx` discovery, JavaScript/TSX parser
  routing, honest language labels, and shared M2.1A/M2.1B behavior on the new suffixes.
- [x] 2026-07-20: Phase 3 — Added suffix-gated runtime React evidence and conservative
  top-level named function, arrow, and class classification using exactly one existing
  `react_component` node while preserving methods, containment, exports, spans, and IDs.
- [x] 2026-07-20: Phase 4 — Preserved the historical profiles and isolated M2.1B fixture,
  added the M2.2A check/update helper and TypeScript frontend partial gold, and added the
  full-stack TaskPanel semantic assertion without another gold file.
- [x] 2026-07-20: Phase 5 local implementation closeout — Updated `CODEX.md`, `README.md`,
  interview questions, and this ExecPlan; completed the full Windows validation,
  compatibility, determinism, privacy, non-execution, and scope audits.
- [x] 2026-07-20: Independent final review reproduced and corrected the optional
  `render?()` false positive, added its focused regression, and repeated the required
  validation and scope audit.
- [x] 2026-07-20: PR #5's required Linux `check` passed for implementation commit
  `7ffb54879195f61a5c0823222b3c342378357bd4` in workflow run `29784583712`. The job
  completed successfully in 16 seconds. M2.2A is complete; Milestone 2 remains open, and
  M2.2B has not been selected or started.

## Discoveries and surprises

- `NodeKind.REACT_COMPONENT` already exists, so this slice needs no graph enum or schema
  addition. The main contract decision is whether that kind replaces the ordinary node.
- `tree_sitter_javascript.language()` already parses JSX. A distinct JavaScript JSX capsule
  is neither exposed nor required by the installed package.
- `tree_sitter_typescript.language_tsx()` is present in the locked 0.23.2 wheel and reports
  ABI 14, compatible with the current runtime.
- Under both pinned grammars, fragment syntax is emitted as `jsx_element` with unnamed
  opening/closing tags, not a distinct `jsx_fragment` node.
- Representative TypeScript and TSX trees are identical for current functions, classes,
  arrows, imports, re-exports, selected declarations, CommonJS, and generic arrows.
- JavaScript class heritage contains the base directly under `class_heritage`; TypeScript
  and TSX wrap the runtime base in `extends_clause.value`. Typed heritage arguments remain
  separate and can be ignored safely.
- The current visitor chooses class-body traversal with `kind is NodeKind.CLASS`; simply
  changing the selected kind to `REACT_COMPONENT` would therefore drop every method child.
  M2.2A must key traversal to the `class_declaration` syntax form instead.
- JSX syntax and PascalCase are not React-specific. Requiring a written runtime binding
  import from exact source `react` prevents Preact/Solid/custom JSX from being silently
  labeled React, while deliberately deferring no-import automatic-runtime recognition.
- The pinned TSX grammar parses both `<T>(value: T) => ...` and
  `<T,>(value: T) => ...` as `arrow_function`, while method overload declarations use
  `method_signature`; both shapes now have explicit classification boundaries.
- Independent final review found that the pinned TSX grammar accepts `render?() { ... }` as
  a `method_definition` with an unnamed `?` token and no parse error. The initial classifier
  treated it as an ordinary render method. Optional render methods are now rejected
  explicitly, with a focused regression, to preserve the approved ordinary-instance-method
  boundary.
- Existing fixture future `gold.json` files use readable placeholder IDs and include calls
  and later resolver behavior. They are not canonical current extraction output and cannot
  be reused as M2.2A gold.
- M1 compatibility currently ignores only `.js`/`.ts`; adding default JSX/TSX discovery
  requires extending that historical input profile even though no M1 gold content changes.

## Validation transcript

Planning-only validation on 2026-07-20:

- `git branch --show-current` returned `main`.
- `git rev-parse HEAD`, `main`, and `origin/main` each returned
  `1ced144fc84f529c48f318b9380f630cd0d283cf`; `git status -sb` showed a clean synchronized
  branch before the planning files were edited.
- Read-only package audit confirmed declared/locked tree-sitter 0.26.0,
  tree-sitter-javascript 0.25.0, and tree-sitter-typescript 0.23.2.
- Real parser probes confirmed JavaScript JSX ABI 15 and TSX ABI 14 parse representative
  elements, self-closing elements, fragments, parentheses, functions, arrows, named/default
  declarations, nested/callback scopes, class heritage, typed props, and generic arrows
  without errors.
- A direct TypeScript-versus-TSX comparison reported identical trees for representative
  current M2.1A/M2.1B functions, classes, arrows, imports, re-exports, declarations,
  CommonJS, and generic arrows.
- Independent review re-read the governing plans and current implementation, reconfirmed
  `HEAD == main == origin/main == 1ced144fc84f529c48f318b9380f630cd0d283cf`, and found
  only `CODEX.md` plus this untracked plan in the planning delta.
- Independent locked-environment probes reconfirmed runtime 0.26.0 with ABI range 13–15,
  JavaScript 0.25.0/ABI 15, and TypeScript plus TSX 0.23.2/ABI 14. They also confirmed
  parenthesized fragment returns, both TSX generic-arrow spellings, JS-versus-TS heritage
  fields, type-only import tokens, method modifiers, and `method_signature` overloads.
- Independent `git diff --check` and the untracked-plan whitespace check exited 0; only the
  expected Windows LF-to-CRLF working-copy warnings were printed.
- The planning review changed no production code, tests, fixture sources, gold,
  dependencies, lockfiles, CI configuration, commits, or GitHub state. The later explicit
  developer authorization activated the implementation phases recorded above.

Implementation validation on Windows on 2026-07-20:

- Offline lock check and locked sync exited 0, resolving 30 packages and checking 29; no
  dependency declaration or lockfile changed. Ruff format/check and lint exited 0 for 53
  files, and mypy found no issues in 36 source files.
- Focused suites exited 0: 35 M2.2A cases; 76 complete JS/TS/JSX/TSX extractor cases; 35
  scanner cases with 3 Windows symlink skips; 36 registry/extractor-contract cases; 30
  indexer cases; 23 CLI cases; 8 model cases; 16 M1 acceptance cases; and each individual
  M2.1A, M2.1B, and M2.2A compatibility/gold case.
- Full pytest exited 0 after collecting 313 tests: 310 passed and 3 skipped only because
  Windows returned symlink privilege error 1314. Total coverage was 93%; the shared
  JavaScript/TypeScript/JSX/TSX extractor reported 94%.
- Harness smoke and doctor exited 0: 5 fixtures, 5 questions, and 5 diff cases were valid;
  Python 3.11.15/package 0.1.0 were healthy and require no network. All M1, M2.1B, and
  M2.2A check-by-default gold helpers exited 0.
- Two independent M2.2A generations were identical at 5,550 bytes, SHA-256
  `3bd24ab7c9d6f2356c3a9955b601f9a61084b58f336c6430ebb753bd19cd1a12`.
  A disposable mixed-suffix CLI repository produced identical hashes
  `bb5b7e530c0e5aeef0bc30a235393ea9ef791f2b2e1c191d8faccda1ab00eac1`,
  14 nodes, 13 containment edges, three ESM imports, three ESM exports, and exactly the
  `View.View`/`Panel.Panel` JSX/TSX components on both runs.
- The disposable output contained no absolute root or timestamp key, no forbidden
  import/export/call/inheritance edges, and the source execution sentinel was absent. The
  verified scratch repository was removed afterward.
- Independent final review confirmed the pinned TSX `render?()` grammar shape, rejected
  that optional method from class-component evidence, and added the negative regression
  before repeating the focused and full suites reported above.
- `make check` was attempted and exited 1 before running because GNU Make is not installed
  in this Windows shell. Its lock, format, lint, type-check, full-test, and harness
  constituents were run directly and passed.

PR #5 Linux CI closeout on 2026-07-20:

- The required Linux `check` passed for implementation commit
  `7ffb54879195f61a5c0823222b3c342378357bd4` in workflow run `29784583712`.
- The job completed successfully in 16 seconds; its exact record is
  https://github.com/weeelin98/RepoLens/actions/runs/29784583712/job/88493214124.
- The three symlink skips above remain accurately scoped to the local Windows privilege
  limitation. M2.2A is complete and Linux CI verified; Milestone 2 remains open, and M2.2B
  has not been selected or started.

## Learning checkpoint

The completed M2.2A slice retains this developer learning checkpoint:

1. Why `.jsx` can use the JavaScript grammar while `.tsx` requires the TSX capsule, and how
   runtime/grammar ABI compatibility is verified.
2. Which existing visitor behavior is shared safely and where JS versus TS class-heritage
   shapes require an adapter.
3. Why PascalCase/JSX alone is neither component nor React-framework evidence, why the
   runtime import gate is conservative, and why direct JSX return inspection is not
   control-flow or call analysis.
4. How function, arrow, and class component evidence differs, including why class evidence
   requires a complete runtime React import/base audit.
5. Why fragments and parentheses are supported but conditional/call/alias returns are not.
6. Why nested/callback/anonymous forms remain ordinary or absent rather than gaining
   inferred identities.
7. Why one `react_component` node is preferable to duplicate ordinary/component nodes, and
   why classification intentionally changes the stable ID kind input.
8. How M1, M2.1A, and M2.1B bytes remain protected while normal M2.2A production indexing
   exposes JSX/TSX files.
9. Why direct React import syntax remains unresolved evidence and creates no target or
   inheritance edge.
10. Which later React, call, route, HTTP, resolver, traversal, and reporting behaviors are
    still explicitly outside M2.2A.

## Outcome and follow-ups

M2.2A is the complete, Linux-CI-verified bounded Milestone 2 slice. Its independently
reviewed implementation adds `.jsx`/`.tsx` discovery, correct JavaScript/TSX parser
routing, completed M2.1 behavior on the new suffixes, and conservative single-node React
component classification from written runtime React imports plus direct syntax evidence.
PR #5's required Linux `check` passed for implementation commit
`7ffb54879195f61a5c0823222b3c342378357bd4` in workflow run `29784583712`; the job
completed successfully in 16 seconds at
https://github.com/weeelin98/RepoLens/actions/runs/29784583712/job/88493214124.

Milestone 2 remains open. Calls, resolution, hooks, data flow, JSX graphs, routes, HTTP,
FastAPI linking, traversal, overview/context/impact, MCP, Milestone 3, and M2.2B remain
separate future work. M2.2B has not been selected or started. Do not begin any of them as
part of this ExecPlan.
