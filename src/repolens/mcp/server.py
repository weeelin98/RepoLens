"""Future MCP service boundary.

Milestone 6 will adapt these deterministic application services to MCP transport. Parsing,
traversal, ranking, and impact analysis must remain outside this package.
"""

from __future__ import annotations

from typing import Protocol


class RepoLensServices(Protocol):
    def get_codebase_overview(self) -> str: ...

    def find_symbol(self, symbol: str) -> str: ...

    def get_symbol_context(self, symbol: str) -> str: ...

    def trace_dependency_path(self, source: str, target: str) -> str: ...

    def analyze_change_impact(self, git_range: str) -> str: ...
