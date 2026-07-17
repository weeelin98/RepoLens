# Interview Questions

## Milestone 0

1. Why must stable graph IDs exclude timestamps and machine-specific absolute paths?
2. What is the difference between schema validation and semantic fixture validation?
3. Why expose unimplemented CLI commands instead of hiding the planned interface?
4. How do pure precision/recall functions make an evaluation harness easier to trust?
5. Where should deterministic behavior be enforced: models, serializers, or both?

## Milestone 1.1 — Repository Scanner

1. Why does `SourceFile` exclude an absolute path even though scanning uses one internally?
2. How does mutating `dirnames` during a top-down `os.walk` differ from filtering results
   after traversal?
3. Why are the lexical file path and resolved symlink target both necessary?
4. Which files count toward each of the three resource limits, and why?
5. Why does an oversized individual file allow scanning to continue while an aggregate
   limit stops the scan?
6. What makes nested `.gitignore` support more complex than loading only the root file?

## Milestone 1.2A — Basic Python Definition Extraction

1. How does a repository-relative Python path become a module qualified name, and why is
   root `__init__.py` represented explicitly rather than guessed from a repository name?
2. How does the lexical scope stack distinguish a direct class method from a function
   nested inside that method?
3. Why do stable definition IDs include the qualified name and declaration start line?
4. How do Python AST line and column coordinates map into `SourceSpan`, including the
   exclusive end-column convention?
5. Why does each definition receive exactly one `contains` edge from its nearest named
   lexical scope?
6. Why can `ast.parse()` inspect definitions without importing or executing the source?

## Milestone 1.2B — Unresolved Python Import Facts

1. How do `ast.Import` and `ast.ImportFrom` represent different import syntax?
2. Why does one import statement containing several aliases produce several facts?
3. How are an imported name and its local alias different?
4. What does `ImportFrom.level` preserve, and why is it not enough to resolve an absolute
   module without package context?
5. Why must a star import remain an explicit unexpanded fact?
6. Why does AST extraction never execute the imported module?
7. Why are target nodes and cross-file `imports` edges deferred to a resolver?

## Milestone 1.3A — In-memory Repository Graph Assembly

1. Why does the repository node represent the root instead of adding a second root
   directory node?
2. How are parent directory nodes derived from accepted scanner paths without recreating
   ignored or resource-limited directories?
3. Why must extractor selection happen before source loading?
4. How do `tokenize.open()` and the post-scan containment check protect different parts of
   the source-loading contract?
5. Why do source-loading failures preserve a file node but omit a module node?
6. Where are node, edge, import, and diagnostic ordering enforced, and why are those
   explicit contracts rather than incidental insertion order?
7. Why do unresolved import facts remain outside `GraphSnapshot` while extractor nodes and
   direct containment edges are merged into it?

## Milestone 1.3B — CLI Index and Deterministic graph.json

1. How does Typer validate and pass a relative, absolute, or current-directory repository
   path without changing the process working directory?
2. How does `RuntimeConfig.output_directory` distinguish repository-relative and absolute
   output locations?
3. Why is the complete `RepositoryIndexResult` serialized instead of only its
   `GraphSnapshot`?
4. Why must nodes, edges, imports, and diagnostics be sorted before JSON encoding even when
   JSON keys are also sorted?
5. How does writing, flushing, syncing, closing, and replacing a sibling temporary file
   prevent a partially written `graph.json`?
6. Which diagnostics remain non-fatal, and why can the command still succeed while
   preserving them in output?
7. Why must the configured output directory be pruned before scanner resource accounting
   rather than filtered after scanning?

## Milestone 1.4A — Basic Deterministic Markdown Extraction

1. How do CommonMark block tokens and inline child tokens expose different source evidence?
2. How does the heading stack attach same-level, nested, and skipped-level headings?
3. Why must repeated heading names include source position in their stable IDs?
4. Why do Markdown links remain unresolved facts instead of `references` graph edges?
5. Why is fenced code recorded as bounded metadata rather than executed or parsed again?
6. How does inline-code syntax differ from a resolved symbol, path, command, or call?
7. Why is a containing block line span more honest than searching source for an inline
   token and claiming exact columns?
8. How do Markdown document/section nodes and unresolved facts flow into canonical
   `graph.json` without absolute repository paths?

## Milestone 1.4B — Deterministic Project Metadata Extraction

1. Why is accepting three exact basenames safer than adding `.json` and `.toml` suffixes?
2. How does `tomllib` parse pyproject data without importing the project or invoking its
   build backend?
3. Why can package scripts be retained safely as strings without running npm or Node?
4. Why do tsconfig `extends`, `baseUrl`, and `paths` remain unresolved in extraction?
5. Why do metadata facts use source-path-only evidence while Python AST and Markdown block
   tokens can provide spans?
6. Why are dependency declarations facts rather than `external_dependency` nodes here?
7. How do exact-filename registry precedence and an authoritative injected registry coexist?
8. Where are nested mappings, safe set-like arrays, fact collections, and JSON keys
   normalized for deterministic `graph.json` output?

## Milestone 1.5 — Fixture Gold and Deterministic Acceptance

1. Why are current canonical M1 outputs stored separately from the harness's future
   resolver/query `gold.json` contracts?
2. How do independently authored semantic assertions prevent committed generated bytes
   from becoming a self-fulfilling test oracle?
3. Which model and serializer layers normalize collections and mappings before byte
   comparison, and what determinism boundary is actually promised?
4. How do unique IDs, normalized edges, endpoint existence, path privacy, schema version,
   round-trip parsing, and canonical ordering jointly establish graph integrity?
5. How do harmless sentinels and blocked subprocess/network entry points prove that source,
   package scripts, Markdown fences, and build declarations remain inert data?
6. Why can invalid source still produce a useful valid partial graph and CLI exit 0, while
   an invalid root remains fatal?
7. Why is the completed M1 result a syntax/direct-fact graph rather than a resolved import,
   call, or dependency graph?
