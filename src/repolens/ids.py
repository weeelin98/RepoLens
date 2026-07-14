"""Deterministic identity and repository-path normalization."""

from __future__ import annotations

import hashlib
import unicodedata
from pathlib import PurePosixPath

from repolens.models import NodeKind

ID_NAMESPACE = "repolens:v1"


def normalize_text(value: str) -> str:
    """Normalize Unicode without changing meaningful case or whitespace."""

    return unicodedata.normalize("NFC", value)


def normalize_repo_path(value: str) -> str:
    """Return a safe POSIX repository-relative path."""

    normalized = normalize_text(value.replace("\\", "/"))
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("source paths must be repository-relative and cannot contain '..'")
    rendered = path.as_posix()
    if rendered in {"", "."}:
        return "."
    return rendered.removeprefix("./")


def stable_node_id(
    kind: NodeKind | str,
    *,
    source_path: str = ".",
    qualified_name: str = "",
    start_line: int | None = None,
    disambiguator: str = "",
) -> str:
    """Build a compact deterministic ID from versioned semantic coordinates."""

    kind_value = kind.value if isinstance(kind, NodeKind) else normalize_text(kind)
    fields = (
        ID_NAMESPACE,
        kind_value,
        normalize_repo_path(source_path),
        normalize_text(qualified_name),
        "" if start_line is None else str(start_line),
        normalize_text(disambiguator),
    )
    digest = hashlib.sha256("\x1f".join(fields).encode()).hexdigest()[:20]
    return f"{kind_value}:{digest}"
