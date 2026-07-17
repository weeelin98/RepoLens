from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from repolens.extractors import (
    ExtractionResult,
    MetadataEcosystem,
    ProjectMetadataExtractor,
    ProjectMetadataFact,
)


def extract(filename: str, source: str, directory: str = "") -> ExtractionResult:
    path = Path(directory) / filename if directory else Path(filename)
    return ProjectMetadataExtractor().extract(path, source)


def values_by_field(result: ExtractionResult) -> dict[str, object]:
    return {fact.field: fact.value for fact in result.metadata_facts}


def test_metadata_extractor_declares_only_exact_supported_filenames() -> None:
    extractor = ProjectMetadataExtractor()

    assert extractor.extensions == frozenset()
    assert extractor.filenames == frozenset({"package.json", "pyproject.toml", "tsconfig.json"})


def test_pyproject_extracts_documented_project_and_build_fields() -> None:
    source = """
[project]
name = "example"
version = "1.2.3"
description = "Example project"
requires-python = ">=3.11"
dependencies = ["zeta>=2", "alpha==1"]

[project.optional-dependencies]
test = ["pytest", "coverage"]

[project.scripts]
example = "example.cli:main"

[project.gui-scripts]
example-gui = "example.gui:main"

[project.entry-points."example.plugins"]
demo = "example.plugin:Demo"

[build-system]
requires = ["wheel", "hatchling"]
build-backend = "hatchling.build"
"""

    result = extract("pyproject.toml", source)
    values = values_by_field(result)

    assert values == {
        "build-system.build-backend": "hatchling.build",
        "build-system.requires": ["hatchling", "wheel"],
        "project.dependencies": ["alpha==1", "zeta>=2"],
        "project.description": "Example project",
        "project.entry-points": {"example.plugins": {"demo": "example.plugin:Demo"}},
        "project.gui-scripts": {"example-gui": "example.gui:main"},
        "project.name": "example",
        "project.optional-dependencies": {"test": ["coverage", "pytest"]},
        "project.requires-python": ">=3.11",
        "project.scripts": {"example": "example.cli:main"},
        "project.version": "1.2.3",
    }
    assert all(fact.ecosystem is MetadataEcosystem.PYTHON_PROJECT for fact in result.metadata_facts)
    assert all(fact.span is None for fact in result.metadata_facts)


def test_pyproject_dynamic_fields_are_named_but_not_evaluated() -> None:
    result = extract("pyproject.toml", '[project]\nname = "example"\ndynamic = ["version"]\n')

    assert values_by_field(result) == {
        "project.dynamic": ["version"],
        "project.name": "example",
    }
    assert "project.version" not in values_by_field(result)


def test_pyproject_ignores_undocumented_tables_and_fields() -> None:
    result = extract(
        "pyproject.toml",
        '[project]\nname = "example"\nreadme = "README.md"\n[tool.secret]\ntoken = "x"\n',
    )

    assert values_by_field(result) == {"project.name": "example"}


def test_malformed_pyproject_returns_one_deterministic_diagnostic() -> None:
    first = extract("pyproject.toml", "[project\n")
    second = extract("pyproject.toml", "[project\n")

    assert first == second
    assert first.metadata_facts == ()
    assert first.diagnostics == ("metadata_parse_error:pyproject.toml:toml",)


def test_package_extracts_only_documented_fields_and_distinct_dependency_groups() -> None:
    source = """
{
  "name": "example",
  "version": "1.0.0",
  "description": "Example package",
  "private": true,
  "type": "module",
  "main": "dist/index.js",
  "module": "src/index.js",
  "types": "dist/index.d.ts",
  "exports": {".": {"types": "./dist/index.d.ts", "import": "./dist/index.js"}},
  "scripts": {"build": "node dangerous.js"},
  "dependencies": {"zeta": "^2", "alpha": "^1"},
  "devDependencies": {"vitest": "^3"},
  "peerDependencies": {"react": ">=18"},
  "optionalDependencies": {"native": "1"},
  "engines": {"node": ">=20"},
  "workspaces": ["packages/z", "packages/a"],
  "repository": "ignored"
}
"""

    result = extract("package.json", source)
    values = values_by_field(result)

    assert values["name"] == "example"
    assert values["version"] == "1.0.0"
    assert values["type"] == "module"
    assert values["scripts"] == {"build": "node dangerous.js"}
    assert values["dependencies"] == {"alpha": "^1", "zeta": "^2"}
    assert values["devDependencies"] == {"vitest": "^3"}
    assert values["peerDependencies"] == {"react": ">=18"}
    assert values["optionalDependencies"] == {"native": "1"}
    assert values["workspaces"] == ["packages/a", "packages/z"]
    assert "repository" not in values
    assert all(fact.ecosystem is MetadataEcosystem.NODE_PACKAGE for fact in result.metadata_facts)


def test_package_scripts_are_stored_but_never_executed(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed.txt"
    source = json.dumps({"scripts": {"build": f"echo executed > {sentinel}"}})

    result = extract("package.json", source)

    assert values_by_field(result)["scripts"] == {"build": f"echo executed > {sentinel}"}
    assert not sentinel.exists()


@pytest.mark.parametrize(
    "source",
    ["{", '{"name":"one","name":"two"}', '{"value":NaN}'],
)
def test_malformed_or_nonstrict_package_json_returns_diagnostic(source: str) -> None:
    result = extract("package.json", source)

    assert result.metadata_facts == ()
    assert result.diagnostics == ("metadata_parse_error:package.json:json",)


def test_tsconfig_supports_comments_trailing_commas_and_documented_fields() -> None:
    source = """
{
  // direct structure
  "extends": "./base.json",
  "files": ["src/main.ts"],
  "include": ["src/**/*.ts"],
  "exclude": ["dist"],
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "jsx": "react-jsx",
    "baseUrl": ".",
    "rootDir": "src",
    "outDir": "dist",
    "allowJs": false,
    "checkJs": false,
    "strict": true,
    "paths": {"@/*": ["src/*",],},
    "types": ["node"],
    "lib": ["ES2022", "DOM"],
    "noEmit": true,
  },
}
"""

    result = extract("tsconfig.json", source)
    values = values_by_field(result)

    assert values["extends"] == "./base.json"
    assert values["include"] == ["src/**/*.ts"]
    assert values["compilerOptions.strict"] is True
    assert values["compilerOptions.baseUrl"] == "."
    assert values["compilerOptions.paths"] == {"@/*": ["src/*"]}
    assert values["compilerOptions.lib"] == ["ES2022", "DOM"]
    assert "compilerOptions.noEmit" not in values
    assert result.diagnostics == ()


def test_tsconfig_paths_and_extends_remain_unresolved_direct_values() -> None:
    result = extract(
        "tsconfig.json",
        '{"extends":"@scope/config","compilerOptions":{"baseUrl":"src",'
        '"paths":{"@app/*":["app/*","generated/*"]}}}',
    )

    assert values_by_field(result) == {
        "compilerOptions.baseUrl": "src",
        "compilerOptions.paths": {"@app/*": ["app/*", "generated/*"]},
        "extends": "@scope/config",
    }


def test_malformed_jsonc_returns_one_diagnostic() -> None:
    result = extract("tsconfig.json", '{"compilerOptions": { /* unfinished')

    assert result.metadata_facts == ()
    assert result.diagnostics == ("metadata_parse_error:tsconfig.json:jsonc",)


def test_metadata_paths_are_repository_relative_posix_and_have_no_guessed_span() -> None:
    result = extract("package.json", '{"name":"example"}', r"packages\web")

    assert result.metadata_facts[0].source_path == "packages/web/package.json"
    assert result.metadata_facts[0].span is None


def test_repeated_extraction_is_equal_and_facts_are_sorted() -> None:
    source = '{"version":"1","name":"example","dependencies":{"z":"2","a":"1"}}'
    extractor = ProjectMetadataExtractor()

    first = extractor.extract(Path("package.json"), source)
    second = extractor.extract(Path("package.json"), source)

    assert first == second
    assert [fact.field for fact in first.metadata_facts] == [
        "dependencies",
        "name",
        "version",
    ]
    assert first.metadata_facts[0].value == {"a": "1", "z": "2"}


def test_unsupported_filename_is_rejected() -> None:
    with pytest.raises(ValueError, match="supported exact filename"):
        extract("config.json", "{}")


def test_metadata_fact_rejects_absolute_paths_and_non_json_values(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        ProjectMetadataFact(
            ecosystem=MetadataEcosystem.NODE_PACKAGE,
            field="name",
            value="example",
            source_path=str(tmp_path / "package.json"),
        )
    with pytest.raises(ValidationError, match="JSON-compatible"):
        ProjectMetadataFact(
            ecosystem=MetadataEcosystem.NODE_PACKAGE,
            field="bad",
            value=object(),
            source_path="package.json",
        )
