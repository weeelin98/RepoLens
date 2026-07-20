"""Check or explicitly update canonical Milestone 2.2A partial gold."""

from __future__ import annotations

import argparse
import difflib
from pathlib import Path

from repolens.config import RuntimeConfig
from repolens.graph.serialization import canonical_index_json, parse_index_json
from repolens.indexer import index_repository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "harness" / "fixtures" / "typescript_frontend"
REPOSITORY = FIXTURE_ROOT / "repo"
GOLD_PATH = FIXTURE_ROOT / "m2-2a-graph.json"


def generated_graph() -> str:
    rendered = canonical_index_json(index_repository(REPOSITORY, RuntimeConfig()))
    validated = parse_index_json(rendered)
    if canonical_index_json(validated) != rendered:
        raise ValueError("canonical round-trip changed M2.2A partial output")
    return rendered


def difference(expected: str, actual: str) -> str:
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="typescript_frontend/m2-2a-graph.json",
            tofile="typescript_frontend/generated-m2-2a-graph.json",
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="explicitly replace committed M2.2A gold after reviewing semantic changes",
    )
    arguments = parser.parse_args()
    rendered = generated_graph()
    if arguments.update:
        GOLD_PATH.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"updated {GOLD_PATH.relative_to(PROJECT_ROOT).as_posix()}")
        return 0
    if not GOLD_PATH.is_file():
        print(f"missing {GOLD_PATH.relative_to(PROJECT_ROOT).as_posix()}")
        return 1
    expected = GOLD_PATH.read_text(encoding="utf-8")
    if expected != rendered:
        print(difference(expected, rendered))
        print("M2.2A gold differs; review the diff, then run with --update if intentional.")
        return 1
    print("M2.2A partial gold matches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
