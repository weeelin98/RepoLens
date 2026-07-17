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

The current `graph.json` contains repository/directory/file structure, Python modules and
definitions with spans and stable IDs, unresolved Python imports, Markdown document/section
hierarchy and direct syntax facts, allowlisted direct project metadata, and deterministic
diagnostics. It does not contain resolved imports, calls, JavaScript/TypeScript source
symbols, overview/query/impact results, or MCP behavior. The next active milestone is
Milestone 2 — JavaScript, TypeScript, JSX, and TSX extraction.

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
