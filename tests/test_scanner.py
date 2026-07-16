from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from repolens.config import RuntimeConfig
from repolens.scanner import ScanDiagnosticCode, ScanResult, SourceFile, scan_repository

MISSING_SCANNER = pytest.mark.xfail(
    reason="Milestone 1.1: repository traversal and resource-limit behavior is not implemented",
    strict=True,
)


def write_file(root: Path, relative_path: str, content: str = "x") -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def result_paths(result: ScanResult) -> tuple[str, ...]:
    return tuple(file.relative_path for file in result.files)


def diagnostic_pairs(result: ScanResult) -> tuple[tuple[str | None, ScanDiagnosticCode], ...]:
    return tuple((diagnostic.path, diagnostic.code) for diagnostic in result.diagnostics)


@MISSING_SCANNER
def test_finds_supported_files_with_normalized_deterministic_paths(tmp_path: Path) -> None:
    write_file(tmp_path, "nested/module.PY")
    write_file(tmp_path, "README.MD")
    write_file(tmp_path, "notes.txt")
    write_file(tmp_path, "LICENSE")

    first = scan_repository(tmp_path, RuntimeConfig())
    second = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(first) == ("README.MD", "nested/module.PY")
    assert tuple(file.suffix for file in first.files) == (".md", ".py")
    assert first == second


@pytest.mark.parametrize("ignored_directory", [".git", ".venv", "venv", "__pycache__"])
@MISSING_SCANNER
def test_prunes_default_ignored_directories(tmp_path: Path, ignored_directory: str) -> None:
    write_file(tmp_path, f"{ignored_directory}/hidden.py")
    write_file(tmp_path, "visible.py")

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(result) == ("visible.py",)


@MISSING_SCANNER
def test_respects_root_gitignore_and_file_negation(tmp_path: Path) -> None:
    write_file(tmp_path, ".gitignore", "*.py\n!important.py\nignored/\n")
    write_file(tmp_path, "ignored/hidden.md")
    write_file(tmp_path, "important.py")
    write_file(tmp_path, "ordinary.py")
    write_file(tmp_path, "guide.md")

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(result) == ("guide.md", "important.py")


@MISSING_SCANNER
def test_enforces_maximum_file_bytes_and_continues(tmp_path: Path) -> None:
    write_file(tmp_path, "large.py", "1234")
    write_file(tmp_path, "small.py", "12")
    config = RuntimeConfig(maximum_file_bytes=3)

    result = scan_repository(tmp_path, config)

    assert result_paths(result) == ("small.py",)
    assert result.total_bytes == 2
    assert diagnostic_pairs(result) == (("large.py", ScanDiagnosticCode.FILE_TOO_LARGE),)


@MISSING_SCANNER
def test_enforces_maximum_file_count_at_first_excluded_file(tmp_path: Path) -> None:
    write_file(tmp_path, "a.py")
    write_file(tmp_path, "b.py")
    config = RuntimeConfig(maximum_file_count=1)

    result = scan_repository(tmp_path, config)

    assert result_paths(result) == ("a.py",)
    assert diagnostic_pairs(result) == (("b.py", ScanDiagnosticCode.FILE_COUNT_LIMIT_REACHED),)


@MISSING_SCANNER
def test_enforces_maximum_repository_bytes_at_first_excluded_file(tmp_path: Path) -> None:
    write_file(tmp_path, "a.py", "12")
    write_file(tmp_path, "b.py", "34")
    config = RuntimeConfig(maximum_repository_bytes=3)

    result = scan_repository(tmp_path, config)

    assert result_paths(result) == ("a.py",)
    assert result.total_bytes == 2
    assert diagnostic_pairs(result) == (("b.py", ScanDiagnosticCode.REPOSITORY_SIZE_LIMIT_REACHED),)


@pytest.mark.parametrize(
    ("root_kind", "expected_code"),
    [
        ("missing", ScanDiagnosticCode.REPOSITORY_NOT_FOUND),
        ("file", ScanDiagnosticCode.REPOSITORY_NOT_DIRECTORY),
    ],
)
@MISSING_SCANNER
def test_rejects_invalid_repository_roots(
    tmp_path: Path,
    root_kind: str,
    expected_code: ScanDiagnosticCode,
) -> None:
    root = tmp_path / root_kind
    if root_kind == "file":
        root.write_text("not a directory", encoding="utf-8")

    result = scan_repository(root, RuntimeConfig())

    assert result.files == ()
    assert result.total_bytes == 0
    assert tuple(diagnostic.code for diagnostic in result.diagnostics) == (expected_code,)


@MISSING_SCANNER
def test_scanning_never_executes_python_files(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed.txt"
    write_file(
        tmp_path,
        "danger.py",
        f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('executed')\n",
    )

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(result) == ("danger.py",)
    assert not sentinel.exists()


@MISSING_SCANNER
def test_does_not_follow_symlinked_directory(tmp_path: Path) -> None:
    target = tmp_path / "target"
    write_file(target, "nested.py")
    link = tmp_path / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(result) == ("target/nested.py",)


@MISSING_SCANNER
def test_excludes_file_symlink_that_escapes_repository(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    outside = write_file(tmp_path, "outside.py")
    link = repository / "escape.py"
    try:
        link.symlink_to(outside)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"file symlinks unavailable: {error}")

    result = scan_repository(repository, RuntimeConfig())

    assert result.files == ()
    assert diagnostic_pairs(result) == (
        ("escape.py", ScanDiagnosticCode.OUTSIDE_REPOSITORY_SYMLINK),
    )


def test_scan_diagnostic_codes_are_stable() -> None:
    assert tuple(code.value for code in ScanDiagnosticCode) == (
        "repository_not_found",
        "repository_not_directory",
        "file_too_large",
        "file_count_limit_reached",
        "repository_size_limit_reached",
        "outside_repository_symlink",
        "stat_failed",
        "permission_denied",
    )


def test_source_file_contract_normalizes_without_absolute_paths() -> None:
    source = SourceFile(relative_path=r"src\MODULE.PY", suffix=".PY", size_bytes=4)

    assert source.relative_path == "src/MODULE.PY"
    assert source.suffix == ".py"
    assert source.model_dump() == {
        "relative_path": "src/MODULE.PY",
        "suffix": ".py",
        "size_bytes": 4,
    }
    with pytest.raises(ValidationError, match="repository-relative"):
        SourceFile(relative_path=r"C:\repo\module.py", suffix=".py", size_bytes=4)
