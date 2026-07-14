# RepoLens Agent Contract

RepoLens is a local-first context compiler for AI coding agents. Read `CODEX.md` before
changing scope, architecture, graph contracts, outputs, or milestones. For multi-file,
multi-hour, or uncertain work, create and maintain an ExecPlan using `.agent/PLANS.md`.

## Working Agreement

- Work one milestone or one coherent, reviewable slice at a time.
- State observable acceptance criteria before behavioral implementation.
- Prefer helping the developer attempt core logic: hints, then pseudocode, then a minimal
  local example. Do not replace a subsystem when a focused change is enough.
- After implementation, explain the changed data flow and ask the developer to explain the
  milestone's learning checkpoint in their own words.
- Review correctness, edge cases, tests, types, errors, complexity, and architecture.
- Use only abstractions the developer can explain.
- Update tests and harness gold data for every behavioral change.
- Keep unresolved or ambiguous static-analysis relationships explicit; never promote a
  heuristic to a fact.
- Do not silently broaden language support or MVP scope.
- Do not copy implementation code, prompts, or skills from Graphify or another reference.
- Never invent benchmark results, users, accuracy, performance, or token savings.
- Keep milestone-generated interview questions in `docs/INTERVIEW_QUESTIONS.md`.

## Required Commands

Preferred setup: `uv sync --dev`

Pip fallback: `python3.11 -m venv .venv && .venv/bin/pip install -e '.[dev]'`

- Format: `make format` (`uv run ruff format .`)
- Lint: `make lint` (`uv run ruff check .`)
- Type check: `make typecheck` (`uv run mypy src tests`)
- Unit tests: `make test` (`uv run pytest`)
- Harness validation: `make harness-smoke` (`uv run repolens harness-smoke`)
- Full verification: `make check`

All tests and harness commands must run without external network access. Before finishing,
run `make check`, report exact results, inspect the tree for accidental scope growth, and
update the progress, decisions, discoveries, and learning checkpoint in `CODEX.md`.

## Current Boundary

Milestone 0 implements contracts, deterministic IDs/serialization, the extractor registry,
evaluation schemas and metrics, fixture validation, CLI diagnostics, and explicit command
placeholders. It does not implement scanners, parsers, resolvers, traversal, ranking,
impact analysis, overview generation, or MCP service behavior.
