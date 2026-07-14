from backend.api import read_task


def test_read_task() -> None:
    assert read_task(1).title == "Ship RepoLens"
