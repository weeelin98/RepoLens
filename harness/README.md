# RepoLens Evaluation Harness

Each directory under `fixtures/` is a synthetic repository with a versioned manifest,
human-readable source corpus, future resolver/query graph expectations, question JSONL,
and at least one Git diff case. The existing `gold.json` files remain forward-looking
evaluation contracts. They intentionally include relationships that Milestone 1 does not
resolve.

Run `uv run repolens harness-smoke`. This command is deterministic and network-free.

Milestone 1 acceptance separately commits `m1-graph.json` for `python_service`,
`markdown_documented_project`, `fullstack_fastapi_react`, and `typescript_frontend`.
These files are complete canonical `RepositoryIndexResult` outputs from the current
syntax/direct-fact indexer. Focused tests pair their byte comparison with independently
authored semantic assertions so production output is not its own behavioral oracle.

Check the committed M1 gold without writing files:

```bash
uv run python scripts/update_m1_acceptance_gold.py
```

After an intentional schema, parser, ID, or fixture change, inspect the semantic test
failures and generated unified diff. Explicitly update the four records only after review:

```bash
uv run python scripts/update_m1_acceptance_gold.py --update
uv run pytest tests/test_milestone1_acceptance.py -v
```

The helper indexes each fixture repository, writes a temporary `graph.json`, validates it
through `RepositoryIndexResult`, verifies canonical round-trip stability, and then compares
or updates the committed bytes. Tests and normal check mode never overwrite gold.
