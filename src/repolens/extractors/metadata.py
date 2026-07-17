"""Direct project metadata facts from exact supported manifest basenames."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path, PureWindowsPath
from typing import Any, Never

import jsonc

from repolens.config import PROJECT_METADATA_FILENAMES
from repolens.extractors.base import (
    ExtractionResult,
    MetadataEcosystem,
    ProjectMetadataFact,
)
from repolens.ids import normalize_repo_path

_PYPROJECT_FIELDS = (
    "name",
    "version",
    "description",
    "requires-python",
    "dependencies",
    "optional-dependencies",
    "scripts",
    "gui-scripts",
    "entry-points",
    "dynamic",
)
_BUILD_SYSTEM_FIELDS = ("requires", "build-backend")
_PACKAGE_FIELDS = (
    "name",
    "version",
    "description",
    "private",
    "type",
    "main",
    "module",
    "types",
    "exports",
    "scripts",
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
    "engines",
    "workspaces",
)
_TSCONFIG_FIELDS = ("extends", "files", "include", "exclude")
_COMPILER_OPTION_FIELDS = (
    "target",
    "module",
    "moduleResolution",
    "jsx",
    "baseUrl",
    "rootDir",
    "outDir",
    "allowJs",
    "checkJs",
    "strict",
    "paths",
    "types",
    "lib",
)


def _normalized_source_path(path: Path) -> str:
    rendered = path.as_posix()
    if path.is_absolute() or PureWindowsPath(rendered).is_absolute():
        raise ValueError("extractor paths must be repository-relative")
    normalized = normalize_repo_path(rendered)
    if normalized == ".":
        raise ValueError("extractor path must name a file")
    return normalized


def _reject_constant(value: str) -> Never:
    raise ValueError(f"non-finite JSON constant is not supported: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is not supported: {key}")
        result[key] = value
    return result


def _require_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("metadata root must be an object")
    return value


def _optional_table(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key, {})
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"metadata table {key!r} must be an object")
    return value


def _sorted_string_list(value: Any) -> Any:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return sorted(value)
    return value


def _sorted_string_list_mapping(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return {key: _sorted_string_list(value[key]) for key in sorted(value) if isinstance(key, str)}


def _facts_for_fields(
    table: dict[str, Any],
    fields: tuple[str, ...],
    *,
    prefix: str,
    ecosystem: MetadataEcosystem,
    source_path: str,
    set_like_fields: frozenset[str] = frozenset(),
    grouped_set_like_fields: frozenset[str] = frozenset(),
) -> list[ProjectMetadataFact]:
    facts: list[ProjectMetadataFact] = []
    for field in fields:
        if field not in table:
            continue
        value = table[field]
        if field in set_like_fields:
            value = _sorted_string_list(value)
        elif field in grouped_set_like_fields:
            value = _sorted_string_list_mapping(value)
        facts.append(
            ProjectMetadataFact(
                ecosystem=ecosystem,
                field=f"{prefix}.{field}" if prefix else field,
                value=value,
                source_path=source_path,
            )
        )
    return facts


def _parse_pyproject(source: str, source_path: str) -> list[ProjectMetadataFact]:
    root = _require_object(tomllib.loads(source))
    project = _optional_table(root, "project")
    build_system = _optional_table(root, "build-system")
    facts = _facts_for_fields(
        project,
        _PYPROJECT_FIELDS,
        prefix="project",
        ecosystem=MetadataEcosystem.PYTHON_PROJECT,
        source_path=source_path,
        set_like_fields=frozenset({"dependencies", "dynamic"}),
        grouped_set_like_fields=frozenset({"optional-dependencies"}),
    )
    facts.extend(
        _facts_for_fields(
            build_system,
            _BUILD_SYSTEM_FIELDS,
            prefix="build-system",
            ecosystem=MetadataEcosystem.PYTHON_PROJECT,
            source_path=source_path,
            set_like_fields=frozenset({"requires"}),
        )
    )
    return facts


def _strict_json_loads(source: str) -> dict[str, Any]:
    return _require_object(
        json.loads(
            source,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    )


def _parse_package(source: str, source_path: str) -> list[ProjectMetadataFact]:
    root = _strict_json_loads(source)
    return _facts_for_fields(
        root,
        _PACKAGE_FIELDS,
        prefix="",
        ecosystem=MetadataEcosystem.NODE_PACKAGE,
        source_path=source_path,
        set_like_fields=frozenset({"workspaces"}),
    )


def _parse_tsconfig(source: str, source_path: str) -> list[ProjectMetadataFact]:
    root = _require_object(
        jsonc.loads(
            source,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    )
    facts = _facts_for_fields(
        root,
        _TSCONFIG_FIELDS,
        prefix="",
        ecosystem=MetadataEcosystem.TYPESCRIPT_CONFIG,
        source_path=source_path,
    )
    facts.extend(
        _facts_for_fields(
            _optional_table(root, "compilerOptions"),
            _COMPILER_OPTION_FIELDS,
            prefix="compilerOptions",
            ecosystem=MetadataEcosystem.TYPESCRIPT_CONFIG,
            source_path=source_path,
        )
    )
    return facts


class ProjectMetadataExtractor:
    """Extract allowlisted project metadata without executing declared behavior."""

    @property
    def extensions(self) -> frozenset[str]:
        return frozenset()

    @property
    def filenames(self) -> frozenset[str]:
        return PROJECT_METADATA_FILENAMES

    def extract(self, path: Path, source: str) -> ExtractionResult:
        source_path = _normalized_source_path(path)
        parser = {
            "pyproject.toml": ("toml", _parse_pyproject),
            "package.json": ("json", _parse_package),
            "tsconfig.json": ("jsonc", _parse_tsconfig),
        }.get(path.name)
        if parser is None:
            raise ValueError("metadata extractor requires a supported exact filename")
        format_name, parse = parser
        try:
            facts = parse(source, source_path)
        except (TypeError, ValueError):
            return ExtractionResult(
                diagnostics=(f"metadata_parse_error:{source_path}:{format_name}",)
            )
        return ExtractionResult(
            metadata_facts=tuple(sorted(facts, key=ProjectMetadataFact.sort_key))
        )
