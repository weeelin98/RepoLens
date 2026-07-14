# RepoLens Evaluation Harness

Each directory under `fixtures/` is a synthetic repository with a versioned manifest,
human-readable source corpus, graph expectations, question JSONL, and at least one Git diff
case. Milestone 0 validates schemas and references only; later milestones compare production
outputs against the same gold contracts.

Run `uv run repolens harness-smoke`. This command is deterministic and network-free.
