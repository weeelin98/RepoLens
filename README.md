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
respecting ignore, resource, encoding, and symlink boundaries. It does not write output or
resolve imports. Milestone 1 remains active; the next slice is Milestone 1.3B — CLI index
command and deterministic `graph.json` output.

## Development

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --dev
uv run repolens --version
uv run repolens doctor
make check
```

Pip fallback:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/repolens doctor
```

Read `CODEX.md` for the complete architecture, scope, milestone acceptance criteria, and
current progress. Read `AGENTS.md` before contributing.
