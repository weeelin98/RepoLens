# RepoLens

RepoLens is a local-first context compiler for AI coding agents. It is being built as a
clean-room, evaluation-driven project for mixed Python and TypeScript repositories.

Milestone 0 is complete. It provides the repository operating contract, typed graph
foundations, deterministic stable IDs/serialization, extractor interfaces, evaluation
metrics and schemas, five synthetic fixture corpora, a smoke validator, and a CLI scaffold.
It does not yet parse a repository.

Milestone 1.1 repository scanning is active. M1.1A implements deterministic basic discovery
and metadata collection, M1.1C adds repository-root `.gitignore` matching, and M1.1B
enforces configured file/count/repository resource limits. External file-symlink safety and
broader filesystem diagnostics remain planned in `.agent/plans/m1-1-repository-scanner.md`.

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
