import pytest
import tempfile
from pathlib import Path
from backend.ingestion.cloner import (
    RepoCloner,
    extract_repo_name_from_source,
    sanitize_repo_name,
)


def test_sanitize_repo_name():
    assert sanitize_repo_name("my-repo.git") == "my-repo"
    assert sanitize_repo_name("https://github.com/org/payment-gateway.git") == "payment-gateway"
    assert sanitize_repo_name("../../escape-attempt") == "escape-attempt"
    assert sanitize_repo_name("repo_with_underscores-and-dashes") == "repo_with_underscores-and-dashes"

    with pytest.raises(ValueError):
        sanitize_repo_name("")

    with pytest.raises(ValueError):
        sanitize_repo_name("///")


def test_extract_repo_name_from_source():
    assert extract_repo_name_from_source("https://github.com/torvalds/linux") == "linux"
    assert extract_repo_name_from_source("git@github.com:octocat/Hello-World.git") == "Hello-World"
    assert extract_repo_name_from_source("/home/user/projects/auth-sentinel") == "auth-sentinel"


def test_local_repo_clone():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock source directory
        src_dir = Path(temp_dir) / "source-repo"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')", encoding="utf-8")
        (src_dir / "README.md").write_text("# Test Repo", encoding="utf-8")

        work_dir = Path(temp_dir) / "work"
        cloner = RepoCloner(temp_dir=work_dir)

        repo_name, cloned_dir = cloner.clone(str(src_dir))

        assert repo_name == "source-repo"
        assert cloned_dir.is_dir()
        assert (cloned_dir / "main.py").exists()
        assert (cloned_dir / "README.md").exists()
