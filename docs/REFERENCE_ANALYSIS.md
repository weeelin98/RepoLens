# Reference Analysis: Graphify

## Research boundary

Graphify is an architectural reference, not a code base for reuse. This document is based
on a public README inspection on 2026-07-14 and on RepoLens's supplied project brief. No
source file, prompt, skill, or implementation fragment was copied or adapted.

## Direct observations

The public README presents a local code-to-graph workflow with deterministic parsing, a
serialized complete graph, human-facing report output, and graph queries. Relationships
carry evidence/confidence categories that distinguish direct extraction from resolution or
ambiguity. It also describes test/benchmark assets and a broad set of optional languages,
media types, databases, visual outputs, and coding-assistant integrations.

These are observations about the documented product surface, not claims about unseen code
quality or internals. We did not inspect private material or vendor the repository.

## Ideas adopted at a high level

- A staged pipeline separating discovery, extraction, resolution, graph assembly, and
  presentation.
- Normalized typed nodes and directed edges rather than prose-only indexing.
- Evidence-backed relationships with uncertainty preserved.
- A complete machine-readable graph paired with a bounded human report.
- Query-first consumption by coding agents instead of repeated full-repository reads.
- Deterministic local code parsing where syntax permits it.
- Synthetic fixtures, gold data, and measured baselines as product components.

Each adopted idea is re-specified independently in `CODEX.md` for RepoLens's narrower
Python/TypeScript cross-stack mission.

## Ideas changed

- RepoLens uses Python's standard `ast` for Python and tree-sitter only for the JS/TS
  family, reducing dependencies and giving Python-specific source semantics.
- Evidence uses four explicit classes: syntax-direct, resolver-derived, heuristic, and
  ambiguous/unresolved.
- The default human artifact is a bounded orientation document; detailed evidence moves
  into token-budgeted query context packs.
- The showcase is deliberately narrow: React HTTP calls linked to FastAPI routes and then
  to Python services/models.

## Ideas rejected or deferred

- Dozens of languages; support stays limited to the declared tiers.
- PDF, image, audio, and video extraction.
- LLM-invented semantic code relationships.
- HTML graph visualization and community detection in the MVP.
- Neo4j or any other graph database; deterministic JSON is the storage contract.
- Installation into many coding assistants; an MCP adapter comes only after services work.
- Claims based only on full-corpus token comparisons.

## Attribution statement

No implementation code was copied or adapted. If future work changes that fact, this file
and the affected source must identify the exact origin, license, modifications, and legally
required attribution before merge.
