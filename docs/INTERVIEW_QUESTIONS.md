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
