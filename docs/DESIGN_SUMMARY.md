# Milestone 0 Design Summary

RepoLens begins as a Python 3.11+ `src`-layout package with four foundation seams:

1. **Typed graph contract** — immutable-enough Pydantic models describe nodes, edges,
   source evidence, and deterministic graph snapshots without implementing extraction.
2. **Deterministic identity and normalization** — stable IDs are derived only from
   normalized repository-relative facts; canonical JSON excludes clocks and runtime state.
3. **Extractor boundary** — a small protocol and extension registry let later parsers plug
   in without coupling them to graph traversal, rendering, CLI, or MCP code.
4. **Evaluation before implementation** — versioned fixture manifests, gold schemas,
   question JSONL, diff cases, pure metrics, and a network-free smoke validator establish
   how later milestones will be judged.

The CLI exposes the planned product surface now. Only `--version`, `doctor`, and
`harness-smoke` work in Milestone 0; every other command exits loudly with its target
milestone. The MCP package contains contracts only and cannot pretend to serve results.

Dependencies stay deliberately small: Pydantic and Typer at runtime; pytest, Ruff, and
Mypy for development. Parser, graph, ignore-matching, and Markdown libraries are deferred
until the milestone that exercises them. No reference implementation code is copied.
