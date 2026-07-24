# RepoLens

RepoLens is a local-first context compiler for AI coding agents. It is being built as a
clean-room, evaluation-driven project for mixed Python and TypeScript repositories.

Milestone 0 is complete. It provides the repository operating contract, typed graph
foundations, deterministic stable IDs/serialization, extractor interfaces, evaluation
metrics and schemas, five synthetic fixture corpora, a smoke validator, and a CLI scaffold.
It does not yet parse a repository.

Milestone 1.1 Repository Scanner is complete: M1.1A deterministic discovery, M1.1B resource
limits, M1.1C repository-root `.gitignore` support, and M1.1D symlink containment and
focused filesystem diagnostics all pass local validation. Windows skipped three real-link
tests because symlink creation returned privilege error 1314; Linux GitHub Actions passed
after push and verified those real symlink integrations. That completed scanner slice then
handed off to the Python extraction work described below.

Milestone 1.2A now provides isolated, standard-library AST extraction for Python modules,
classes, functions, async functions, methods, nested definitions, stable IDs, source spans,
and syntax-direct containment. It does not yet extract calls or build `graph.json`.

Milestone 1.2B adds deterministic unresolved Python import facts for direct, from, relative,
aliased, multi-member, nested, and star imports. These facts preserve syntax only; RepoLens
still does not resolve targets, create cross-file import edges, or execute imported modules.

Milestone 1.3A now connects scanning and Python extraction into a deterministic in-memory
repository index. It creates repository/directory/file/module/symbol nodes, syntax-direct
containment, unresolved import facts, and separate scanner/extractor diagnostics while
respecting ignore, resource, encoding, and symlink boundaries.

Milestone 1.3B implements `repolens index PATH`. It writes the complete deterministic index
to `<repository>/repolens-out/graph.json` using atomic replacement, preserves non-fatal
diagnostics, and excludes the configured output directory from repeated scans.

Milestone 1.4A adds deterministic CommonMark extraction for accepted `.md` files. The graph
now includes one Markdown document node, ATX/Setext section nodes, heading containment, and
typed unresolved link, fenced-code, and inline-code facts. Links and code references are
not resolved, fenced code is never executed or recursively parsed, and inline syntax keeps
line-level evidence when parser columns are unavailable.

Milestone 1.4B extracts documented direct fields from exactly `pyproject.toml`,
`package.json`, and `tsconfig.json`. Arbitrary JSON/TOML and lockfiles are not scanned.
Pyproject and package data use standard-library parsers; tsconfig uses a constrained JSONC
parser for comments and trailing commas. Scripts, entry points, build backends,
dependencies, exports, and TypeScript paths are retained only as unresolved data and are
never executed or resolved.

Milestone 1.5 completes Milestone 1. Four existing fixture repositories now have
separate committed canonical M1 outputs, independently authored semantic acceptance tests,
graph-integrity checks, non-execution checks, deterministic diagnostic coverage, and
two-run byte comparisons. The local Windows suite passes with three real-symlink tests
skipped because link creation returned privilege error 1314. The complete M1 acceptance
suite also passed in Linux GitHub Actions on
[PR #2](https://github.com/weeelin98/RepoLens/pull/2) at repair commit
`28ad7fab44fa08d66934dacf541f9b366db14673`.

PR #1 was merged before its CI completed, and that Linux run failed because Windows CRLF
fixture bytes had produced platform-dependent gold sizes and a contradictory CLI test had
placed its own absolute temporary path in package-script input. PR #2 repaired both issues
on `fix/m1-linux-ci`: fixture sources and M1 gold are normalized to LF, and the inert script
test now uses relative input while retaining its absolute-path and non-execution checks.
Linux CI passed the repaired acceptance suite.

Milestone 2.1A adds pinned tree-sitter extraction for exactly `.js` and `.ts`. The index now
includes deterministic JavaScript/TypeScript modules, named functions and async functions,
classes, ordinary class methods, simple identifier-bound arrows, and typed unresolved
direct ESM import/export facts. Malformed files retain only defensible error-free subtrees
plus a stable diagnostic. JSX/TSX, CommonJS, re-exports, calls, and target resolution were
outside that slice.

Milestone 2.1B adds bounded top-level CommonJS `require` and export-assignment occurrence
facts, static ESM re-export facts, and module-level TypeScript interface, type-alias, and
ordinary-enum nodes. CommonJS facts require a complete error-free program-level shadow
audit; ambiguous globals and partial parses suppress those facts. Explicit type-only
re-exports, interfaces, and type aliases do not become runtime export facts, while ordinary
exported enums do. All module relationships remain unresolved syntax facts without target
nodes or import/export graph edges.

M2.1B is complete and Linux CI verified after an independent final review. The local
Windows full suite passed 276 tests with the same three symlink skips caused by privilege
error 1314, total coverage remained 93%, and repeated partial-gold/CLI hashes were
byte-identical. PR #4's required Linux `check` job passed for implementation commit
`b680592a25409f5c7bb0abe9f70b24459298c0d0` in workflow run `29776458604`, completing in
18 seconds; the exact job record is
https://github.com/weeelin98/RepoLens/actions/runs/29776458604/job/88466891502.
Milestone 2 remained open after that slice.

Milestone 2.2A adds discovery and pinned tree-sitter parsing for exactly `.jsx` and `.tsx`,
with honest `jsx`/`tsx` language labels. It reuses the completed JavaScript/TypeScript
visitor and conservatively reclassifies only named, top-level functions, arrows, and React
classes that have exact direct-JSX-return evidence plus a runtime binding import from
`react`. Each match is one `react_component` node; ordinary containment, spans, stable IDs,
and direct export facts are preserved. Automatic-runtime files, async or nested components,
wrappers such as `memo`/`forwardRef`, anonymous defaults, indirect returns, JSX element
graphs, calls, and resolution remain outside this slice. The implementation is independently
reviewed, locally validated on Windows, and Linux CI verified. PR #5's required Linux
`check` passed for implementation commit
`7ffb54879195f61a5c0823222b3c342378357bd4` in workflow run `29784583712`, completing in
16 seconds; the exact job record is
https://github.com/weeelin98/RepoLens/actions/runs/29784583712/job/88493214124.

Milestone 2.2B adds default-empty, conditionally serialized unresolved call facts for
bounded direct syntax in `.js`, `.jsx`, `.ts`, and `.tsx`. It accepts ordinary identifiers
and noncomputed dotted member chains rooted at an identifier, `this`, or `super`; preserves
written aliases, exact `call_expression` spans, optional-chain state, and the nearest
indexed lexical owner; and retains duplicate occurrences. Bare `require`, dynamic import,
constructors, tagged templates, computed/private or wrapped callees, call-result receivers,
unsupported named scopes, and malformed subtrees remain absent. These are syntax facts,
not call nodes or `calls` edges: no target, alias origin, runtime execution, HTTP meaning,
or same-file/cross-file resolution is claimed. Local Windows implementation validation
and independent review are complete; required Linux CI remains pending.

The current `graph.json` contains repository/directory/file structure, Python modules and
definitions with spans and stable IDs, JavaScript/TypeScript/JSX/TSX modules and bounded
definition facts, conservative React component classifications, unresolved Python imports,
ESM imports/exports/re-exports, bounded CommonJS occurrences, bounded unresolved
JavaScript-family call occurrences, Markdown document/section hierarchy and direct syntax
facts, allowlisted direct project metadata, and deterministic diagnostics. It does not
contain resolved imports/exports/calls, call edges, JSX element nodes,
overview/query/impact results, or MCP behavior. Milestone 2 remains open; Milestone 3
resolution has not started.

## Development

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --dev
uv run repolens --version
uv run repolens doctor
uv run repolens index path/to/repository
make check
```

The index command writes `path/to/repository/repolens-out/graph.json` by default.

Pip fallback:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/repolens doctor
```

Read `CODEX.md` for the complete architecture, scope, milestone acceptance criteria, and
current progress. Read `AGENTS.md` before contributing.
