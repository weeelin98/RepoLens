from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from repolens.config import RuntimeConfig
from repolens.scanner import ScanDiagnosticCode, ScanResult, SourceFile, scan_repository


def write_file(root: Path, relative_path: str, content: str = "x") -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def result_paths(result: ScanResult) -> tuple[str, ...]:
    return tuple(file.relative_path for file in result.files)


def diagnostic_pairs(result: ScanResult) -> tuple[tuple[str | None, ScanDiagnosticCode], ...]:
    return tuple((diagnostic.path, diagnostic.code) for diagnostic in result.diagnostics)


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
def test_prunes_default_ignored_directories(tmp_path: Path, ignored_directory: str) -> None:
    write_file(tmp_path, f"{ignored_directory}/hidden.py")
    write_file(tmp_path, "visible.py")

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(result) == ("visible.py",)


def test_respects_root_gitignore_and_file_negation(tmp_path: Path) -> None:
    write_file(tmp_path, ".gitignore", "*.py\n!important.py\nignored/\n")
    write_file(tmp_path, "ignored/hidden.md")
    write_file(tmp_path, "important.py")
    write_file(tmp_path, "ordinary.py")
    write_file(tmp_path, "guide.md")

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(result) == ("guide.md", "important.py")


def test_missing_root_gitignore_preserves_scan_behavior(tmp_path: Path) -> None:
    write_file(tmp_path, "module.py", "python")
    write_file(tmp_path, "guide.md", "markdown")

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(result) == ("guide.md", "module.py")
    assert result.diagnostics == ()
    assert result.total_bytes == 14


def test_nested_gitignore_is_not_loaded(tmp_path: Path) -> None:
    write_file(tmp_path, "nested/.gitignore", "*.py\n")
    write_file(tmp_path, "nested/visible.py", "visible")

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(result) == ("nested/visible.py",)


def test_ignored_file_is_excluded_before_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_file(tmp_path, ".gitignore", "ignored.py\n")
    write_file(tmp_path, "ignored.py", "ignored")
    write_file(tmp_path, "visible.py", "visible")
    original_stat = Path.stat

    def guarded_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        if path.name == "ignored.py":
            raise AssertionError("ignored files must not be statted")
        return original_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", guarded_stat)

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result_paths(result) == ("visible.py",)
    assert result.total_bytes == 7


def test_ignored_directory_is_pruned_before_descent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_file(tmp_path, ".gitignore", "ignored/\n")
    write_file(tmp_path, "ignored/hidden.py")
    write_file(tmp_path, "visible/kept.py")
    visited: list[str] = []

    def fake_walk(
        root: Path,
        *,
        topdown: bool,
        followlinks: bool,
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        assert root == tmp_path.resolve()
        assert topdown is True
        assert followlinks is False
        dirnames = ["visible", "ignored"]
        yield str(root), dirnames, []
        for dirname in dirnames:
            visited.append(dirname)
            yield str(root / dirname), [], ["hidden.py" if dirname == "ignored" else "kept.py"]

    monkeypatch.setattr(os, "walk", fake_walk)

    result = scan_repository(tmp_path, RuntimeConfig())

    assert visited == ["visible"]
    assert result_paths(result) == ("visible/kept.py",)


def test_enforces_maximum_file_bytes_and_continues(tmp_path: Path) -> None:
    write_file(tmp_path, "large.py", "1234")
    write_file(tmp_path, "small.py", "12")
    config = RuntimeConfig(maximum_file_bytes=3)

    result = scan_repository(tmp_path, config)

    assert result_paths(result) == ("small.py",)
    assert result.total_bytes == 2
    assert diagnostic_pairs(result) == (("large.py", ScanDiagnosticCode.FILE_TOO_LARGE),)


def test_enforces_maximum_file_count_at_first_excluded_file(tmp_path: Path) -> None:
    write_file(tmp_path, "a.py")
    write_file(tmp_path, "b.py")
    config = RuntimeConfig(maximum_file_count=1)

    result = scan_repository(tmp_path, config)

    assert result_paths(result) == ("a.py",)
    assert diagnostic_pairs(result) == (("b.py", ScanDiagnosticCode.FILE_COUNT_LIMIT_REACHED),)


def test_enforces_maximum_repository_bytes_at_first_excluded_file(tmp_path: Path) -> None:
    write_file(tmp_path, "a.py", "12")
    write_file(tmp_path, "b.py", "34")
    config = RuntimeConfig(maximum_repository_bytes=3)

    result = scan_repository(tmp_path, config)

    assert result_paths(result) == ("a.py",)
    assert result.total_bytes == 2
    assert diagnostic_pairs(result) == (("b.py", ScanDiagnosticCode.REPOSITORY_SIZE_LIMIT_REACHED),)


def test_accepts_file_at_exact_individual_byte_limit(tmp_path: Path) -> None:
    write_file(tmp_path, "exact.py", "123")

    result = scan_repository(tmp_path, RuntimeConfig(maximum_file_bytes=3))

    assert result_paths(result) == ("exact.py",)
    assert result.total_bytes == 3
    assert result.diagnostics == ()


def test_accepts_proposed_total_at_exact_repository_byte_limit(tmp_path: Path) -> None:
    write_file(tmp_path, "a.py", "12")
    write_file(tmp_path, "b.py", "34")

    result = scan_repository(tmp_path, RuntimeConfig(maximum_repository_bytes=4))

    assert result_paths(result) == ("a.py", "b.py")
    assert result.total_bytes == 4
    assert result.diagnostics == ()


def test_gitignored_file_does_not_consume_file_count(tmp_path: Path) -> None:
    write_file(tmp_path, ".gitignore", "ignored.py\n")
    write_file(tmp_path, "ignored.py")
    write_file(tmp_path, "kept.py")

    result = scan_repository(tmp_path, RuntimeConfig(maximum_file_count=1))

    assert result_paths(result) == ("kept.py",)
    assert result.diagnostics == ()


def test_unsupported_file_does_not_consume_file_count(tmp_path: Path) -> None:
    write_file(tmp_path, "a.txt")
    write_file(tmp_path, "b.py")

    result = scan_repository(tmp_path, RuntimeConfig(maximum_file_count=1))

    assert result_paths(result) == ("b.py",)
    assert result.diagnostics == ()


def test_restrictive_limit_results_are_repeatable(tmp_path: Path) -> None:
    write_file(tmp_path, "a.py")
    write_file(tmp_path, "b.py")
    write_file(tmp_path, "c.py")
    config = RuntimeConfig(maximum_file_count=1)

    first = scan_repository(tmp_path, config)
    second = scan_repository(tmp_path, config)

    assert first == second
    assert result_paths(first) == ("a.py",)
    assert diagnostic_pairs(first) == (("b.py", ScanDiagnosticCode.FILE_COUNT_LIMIT_REACHED),)


@pytest.mark.parametrize(
    ("root_kind", "expected_code"),
    [
        ("missing", ScanDiagnosticCode.REPOSITORY_NOT_FOUND),
        ("file", ScanDiagnosticCode.REPOSITORY_NOT_DIRECTORY),
    ],
)
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


def test_prunes_symlinked_directory_before_descent_without_platform_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_file(tmp_path, "linked/hidden.py")
    write_file(tmp_path, "visible/kept.py")
    visited: list[str] = []
    original_is_symlink = Path.is_symlink

    def fake_is_symlink(path: Path) -> bool:
        if path == tmp_path.resolve() / "linked":
            return True
        return original_is_symlink(path)

    def fake_walk(
        root: Path,
        *,
        topdown: bool,
        followlinks: bool,
    ) -> Iterator[tuple[str, list[str], list[str]]]:
        assert root == tmp_path.resolve()
        assert topdown is True
        assert followlinks is False
        dirnames = ["visible", "linked"]
        yield str(root), dirnames, []
        for dirname in dirnames:
            visited.append(dirname)
            yield str(root / dirname), [], ["kept.py" if dirname == "visible" else "hidden.py"]

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    monkeypatch.setattr(os, "walk", fake_walk)

    result = scan_repository(tmp_path, RuntimeConfig())

    assert visited == ["visible"]
    assert result_paths(result) == ("visible/kept.py",)


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


def test_includes_contained_file_symlink_under_lexical_path(tmp_path: Path) -> None:
    target = write_file(tmp_path, "target.txt", "target")
    link = tmp_path / "alias.py"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"file symlinks unavailable: {error}")

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result.files == (SourceFile(relative_path="alias.py", suffix=".py", size_bytes=6),)
    assert result.diagnostics == ()


def test_external_file_symlink_is_excluded_before_limits_without_platform_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    escape = write_file(repository, "a_escape.py", "escape")
    write_file(repository, "z_valid.py", "v")
    outside = write_file(tmp_path, "outside.py", "outside").resolve()
    original_is_symlink = Path.is_symlink
    original_resolve = Path.resolve

    def fake_is_symlink(path: Path) -> bool:
        if path == escape:
            return True
        return original_is_symlink(path)

    def fake_resolve(path: Path, strict: bool = False) -> Path:
        if path == escape:
            assert strict is True
            return outside
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    monkeypatch.setattr(Path, "resolve", fake_resolve)

    result = scan_repository(
        repository,
        RuntimeConfig(maximum_file_count=1, maximum_repository_bytes=1),
    )

    assert result_paths(result) == ("z_valid.py",)
    assert result.total_bytes == 1
    assert diagnostic_pairs(result) == (
        ("a_escape.py", ScanDiagnosticCode.OUTSIDE_REPOSITORY_SYMLINK),
    )
    assert str(outside) not in result.diagnostics[0].message


def test_contained_file_symlink_uses_lexical_path_without_platform_symlinks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alias = write_file(tmp_path, "alias.py", "target")
    target = write_file(tmp_path, "target.txt", "target").resolve()
    original_is_symlink = Path.is_symlink
    original_resolve = Path.resolve

    def fake_is_symlink(path: Path) -> bool:
        if path == alias:
            return True
        return original_is_symlink(path)

    def fake_resolve(path: Path, strict: bool = False) -> Path:
        if path == alias:
            assert strict is True
            return target
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    monkeypatch.setattr(Path, "resolve", fake_resolve)

    result = scan_repository(tmp_path, RuntimeConfig())

    assert result.files == (SourceFile(relative_path="alias.py", suffix=".py", size_bytes=6),)
    assert result.diagnostics == ()


def test_symlink_resolution_failures_are_deterministic_and_do_not_consume_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken = write_file(tmp_path, "a_broken.py")
    denied = write_file(tmp_path, "b_denied.py")
    write_file(tmp_path, "c_valid.py")
    original_is_symlink = Path.is_symlink
    original_resolve = Path.resolve

    def fake_is_symlink(path: Path) -> bool:
        if path in {broken, denied}:
            return True
        return original_is_symlink(path)

    def fake_resolve(path: Path, strict: bool = False) -> Path:
        if path == broken:
            raise FileNotFoundError
        if path == denied:
            raise PermissionError
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    monkeypatch.setattr(Path, "resolve", fake_resolve)
    config = RuntimeConfig(maximum_file_count=1, maximum_repository_bytes=1)

    first = scan_repository(tmp_path, config)
    second = scan_repository(tmp_path, config)

    assert first == second
    assert result_paths(first) == ("c_valid.py",)
    assert first.total_bytes == 1
    assert diagnostic_pairs(first) == (
        ("a_broken.py", ScanDiagnosticCode.STAT_FAILED),
        ("b_denied.py", ScanDiagnosticCode.PERMISSION_DENIED),
    )


def test_symlink_metadata_failures_are_deterministic_and_do_not_consume_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed = write_file(tmp_path, "a_failed.py")
    denied = write_file(tmp_path, "b_denied.py")
    write_file(tmp_path, "c_valid.py")
    original_is_symlink = Path.is_symlink

    def fake_is_symlink(path: Path) -> bool:
        if path == failed:
            raise OSError
        if path == denied:
            raise PermissionError
        return original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    config = RuntimeConfig(maximum_file_count=1, maximum_repository_bytes=1)

    first = scan_repository(tmp_path, config)
    second = scan_repository(tmp_path, config)

    assert first == second
    assert result_paths(first) == ("c_valid.py",)
    assert first.total_bytes == 1
    assert diagnostic_pairs(first) == (
        ("a_failed.py", ScanDiagnosticCode.STAT_FAILED),
        ("b_denied.py", ScanDiagnosticCode.PERMISSION_DENIED),
    )


def test_stat_failures_are_deterministic_and_do_not_consume_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed = write_file(tmp_path, "a_failed.py")
    denied = write_file(tmp_path, "b_denied.py")
    write_file(tmp_path, "c_valid.py")
    original_stat = Path.stat

    def fake_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        if path == failed and follow_symlinks:
            raise OSError
        if path == denied and follow_symlinks:
            raise PermissionError
        return original_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", fake_stat)
    config = RuntimeConfig(maximum_file_count=1, maximum_repository_bytes=1)

    first = scan_repository(tmp_path, config)
    second = scan_repository(tmp_path, config)

    assert first == second
    assert result_paths(first) == ("c_valid.py",)
    assert first.total_bytes == 1
    assert diagnostic_pairs(first) == (
        ("a_failed.py", ScanDiagnosticCode.STAT_FAILED),
        ("b_denied.py", ScanDiagnosticCode.PERMISSION_DENIED),
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


def test_supported_suffixes_override_is_normalized(tmp_path: Path) -> None:
    write_file(tmp_path, "notes.TXT", "hello")
    write_file(tmp_path, "module.py", "ignored")

    result = scan_repository(tmp_path, RuntimeConfig(), supported_suffixes=frozenset({"TXT"}))

    assert result.files == (SourceFile(relative_path="notes.TXT", suffix=".txt", size_bytes=5),)
    assert result.total_bytes == 5


def test_configured_output_directory_is_pruned_before_limits(tmp_path: Path) -> None:
    output_file = write_file(tmp_path, "a-output/preserved.py", "output")
    write_file(tmp_path, "z-source/visible.py", "v")
    config = RuntimeConfig(
        output_directory=Path("a-output"),
        maximum_file_count=1,
        maximum_repository_bytes=1,
    )

    result = scan_repository(tmp_path, config)

    assert result.files == (
        SourceFile(relative_path="z-source/visible.py", suffix=".py", size_bytes=1),
    )
    assert result.total_bytes == 1
    assert result.diagnostics == ()
    assert output_file.read_text(encoding="utf-8") == "output"
