"""Check or explicitly update canonical Milestone 1 fixture gold."""

from __future__ import annotations

import argparse
import difflib
import shutil
import tempfile
from pathlib import Path

from repolens.config import RuntimeConfig
from repolens.graph.serialization import canonical_index_json, parse_index_json
from repolens.indexer import index_repository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_IDS = (
    "python_service",
    "markdown_documented_project",
    "fullstack_fastapi_react",
    "typescript_frontend",
)
GOLD_FILENAME = "m1-graph.json"
M1_POST_MILESTONE_IGNORE = "*.js\n*.ts\n*.jsx\n*.tsx\n"


def _generated_graph(fixture_id: str, temporary_root: Path) -> str:
    source = PROJECT_ROOT / "harness" / "fixtures" / fixture_id / "repo"
    repository = temporary_root / fixture_id / "repo"
    shutil.copytree(source, repository)
    (repository / ".gitignore").write_text(
        M1_POST_MILESTONE_IGNORE,
        encoding="utf-8",
        newline="\n",
    )
    generated_path = temporary_root / fixture_id / "graph.json"
    generated_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = canonical_index_json(index_repository(repository, RuntimeConfig()))
    generated_path.write_text(rendered, encoding="utf-8", newline="\n")
    validated = parse_index_json(generated_path.read_text(encoding="utf-8"))
    if canonical_index_json(validated) != rendered:
        raise ValueError(f"canonical round-trip changed output for {fixture_id}")
    return rendered


def _difference(fixture_id: str, expected: str, actual: str) -> str:
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=f"{fixture_id}/{GOLD_FILENAME}",
            tofile=f"{fixture_id}/generated-graph.json",
        )
    )


def check_or_update(*, update: bool) -> tuple[str, ...]:
    messages: list[str] = []
    with tempfile.TemporaryDirectory(prefix="repolens-m1-gold-") as temporary:
        temporary_root = Path(temporary)
        for fixture_id in FIXTURE_IDS:
            fixture_root = PROJECT_ROOT / "harness" / "fixtures" / fixture_id
            gold_path = fixture_root / GOLD_FILENAME
            rendered = _generated_graph(fixture_id, temporary_root)
            if update:
                gold_path.write_text(rendered, encoding="utf-8", newline="\n")
                messages.append(f"updated {gold_path.relative_to(PROJECT_ROOT).as_posix()}")
                continue
            if not gold_path.is_file():
                messages.append(f"missing {gold_path.relative_to(PROJECT_ROOT).as_posix()}")
                continue
            expected = gold_path.read_text(encoding="utf-8")
            if expected != rendered:
                messages.append(_difference(fixture_id, expected, rendered))
    return tuple(messages)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="explicitly replace committed M1 gold after reviewing semantic changes",
    )
    arguments = parser.parse_args()
    messages = check_or_update(update=arguments.update)
    if arguments.update:
        print("\n".join(messages))
        return 0
    if messages:
        print("\n".join(messages))
        print("M1 gold differs; review the diff, then run with --update if intentional.")
        return 1
    print(f"M1 gold matches for {len(FIXTURE_IDS)} fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
