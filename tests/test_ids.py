from __future__ import annotations

import pytest

from repolens.ids import normalize_repo_path, stable_node_id
from repolens.models import NodeKind


def test_stable_id_determinism() -> None:
    first = stable_node_id(
        NodeKind.FUNCTION,
        source_path="src\\service.py",
        qualified_name="service.load",
        start_line=8,
    )
    second = stable_node_id(
        NodeKind.FUNCTION,
        source_path="src/service.py",
        qualified_name="service.load",
        start_line=8,
    )
    assert first == second


def test_stable_id_differentiation() -> None:
    first = stable_node_id(NodeKind.FUNCTION, source_path="a.py", qualified_name="load")
    second = stable_node_id(NodeKind.FUNCTION, source_path="b.py", qualified_name="load")
    assert first != second


def test_normalize_repo_path_rejects_escape_and_absolute_paths() -> None:
    with pytest.raises(ValueError, match="repository-relative"):
        normalize_repo_path("../secret.py")
    with pytest.raises(ValueError, match="repository-relative"):
        normalize_repo_path("/tmp/secret.py")
