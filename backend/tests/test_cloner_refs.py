"""
Cloner guarantees around refs, provenance, and name collisions.

These cover the three things the ingest form now relies on: listing refs
without cloning, reporting what was actually checked out, and refusing to let
two repositories share one wiki line name.
"""

import json
import subprocess
from pathlib import Path

import pytest

from backend.ingestion.cloner import (
    RepoCloner,
    RepoNameCollisionError,
    extract_repo_name_from_source,
    sanitize_repo_name,
)


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture()
def remote_repo(tmp_path: Path) -> Path:
    """
    A bare remote whose default branch is `trunk`, with a divergent `main`
    branch and a tag. Nothing here is `master`, so a hardcoded default would
    show up as a wrong file.
    """
    work = tmp_path / "work"
    work.mkdir()
    _git(["init", "-q", "-b", "trunk"], work)
    _git(["config", "user.email", "test@example.com"], work)
    _git(["config", "user.name", "Test"], work)
    (work / "code.txt").write_text("trunk", encoding="utf-8")
    _git(["add", "."], work)
    _git(["commit", "-qm", "trunk commit"], work)
    _git(["tag", "v1.0.0"], work)

    _git(["checkout", "-qb", "main"], work)
    (work / "code.txt").write_text("main", encoding="utf-8")
    _git(["commit", "-qam", "main commit"], work)
    _git(["checkout", "-q", "trunk"], work)

    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(work), str(remote)],
        check=True,
        capture_output=True,
    )
    return remote


def test_list_refs_reports_default_branch_branches_and_tags(remote_repo, tmp_path):
    cloner = RepoCloner(temp_dir=tmp_path / "temp")

    listing = cloner.list_refs(f"file://{remote_repo}")

    assert listing.default_branch == "trunk"
    assert "trunk" in listing.branches
    assert "main" in listing.branches
    assert listing.tags == ["v1.0.0"]
    # Listing must not create a checkout.
    assert list((tmp_path / "temp").iterdir()) == []


def test_clone_defaults_to_remote_default_branch(remote_repo, tmp_path):
    cloner = RepoCloner(temp_dir=tmp_path / "temp")

    result = cloner.clone(f"file://{remote_repo}")

    assert (result.repo_dir / "code.txt").read_text(encoding="utf-8") == "trunk"
    assert result.branch == "trunk"
    assert result.ref is None
    assert result.commit and len(result.commit) == 40
    assert result.short_commit == result.commit[:7]


def test_clone_honours_explicit_branch(remote_repo, tmp_path):
    cloner = RepoCloner(temp_dir=tmp_path / "temp")

    result = cloner.clone(f"file://{remote_repo}", branch="main")

    assert (result.repo_dir / "code.txt").read_text(encoding="utf-8") == "main"
    assert result.branch == "main"
    assert result.ref == "main"


def test_clone_honours_tag_and_records_it_as_the_ref(remote_repo, tmp_path):
    cloner = RepoCloner(temp_dir=tmp_path / "temp")

    result = cloner.clone(f"file://{remote_repo}", branch="v1.0.0")

    # A tag clone lands in detached HEAD, so only the requested ref is honest.
    assert result.ref == "v1.0.0"
    assert result.branch == "v1.0.0"
    assert result.commit


def test_clone_result_unpacks_as_name_and_path(remote_repo, tmp_path):
    """Existing call sites destructure a 2-tuple; that must keep working."""
    cloner = RepoCloner(temp_dir=tmp_path / "temp")

    name, path = cloner.clone(f"file://{remote_repo}")

    assert name == "remote"
    assert path.is_dir()


def test_unknown_branch_fails_with_git_message(remote_repo, tmp_path):
    cloner = RepoCloner(temp_dir=tmp_path / "temp")

    with pytest.raises(RuntimeError, match="Git clone failed"):
        cloner.clone(f"file://{remote_repo}", branch="does-not-exist")


def test_leading_dash_source_is_rejected():
    with pytest.raises(ValueError, match="command-line flag"):
        extract_repo_name_from_source("--upload-pack=touch /tmp/pwned")


def test_dash_separator_makes_source_a_pathname(remote_repo, tmp_path):
    """
    Sources cannot be smuggled in as git options: `--` ends option parsing in
    the clone command, so a dashed value is treated as a repository path.
    """
    cloner = RepoCloner(temp_dir=tmp_path / "temp")
    marker = tmp_path / "INJECTED"

    with pytest.raises((ValueError, RuntimeError)):
        cloner.clone(f"--upload-pack=touch {marker}")
    assert not marker.exists()


# -- name collisions ------------------------------------------------------


def test_owner_qualification_distinguishes_same_named_repositories():
    plain = extract_repo_name_from_source("https://github.com/org1/api")
    assert plain == "api", "the readable name is the default for URL stability"
    assert (
        extract_repo_name_from_source("https://github.com/org1/api", include_owner=True)
        == "org1-api"
    )
    assert (
        extract_repo_name_from_source("https://github.com/org2/api", include_owner=True)
        == "org2-api"
    )


def test_bare_local_paths_keep_their_plain_name():
    """Fixtures are local directories with no owner; they must not be renamed."""
    assert extract_repo_name_from_source("payment-gateway") == "payment-gateway"
    assert extract_repo_name_from_source("/home/user/projects/auth-sentinel") == "auth-sentinel"


def test_owner_qualification_is_optional():
    assert (
        extract_repo_name_from_source("https://github.com/org1/api", include_owner=False)
        == "api"
    )


def test_second_repo_from_another_owner_does_not_overwrite(tmp_path):
    """
    The published line records its source. A different repository asking for the
    same name is a conflict, not a silent overwrite.
    """
    content_dir = tmp_path / "content"
    published = content_dir / "api"
    published.mkdir(parents=True)
    (published / "toc.json").write_text(
        json.dumps({"repo_name": "api", "source": "https://github.com/org1/api"}),
        encoding="utf-8",
    )

    cloner = RepoCloner(temp_dir=tmp_path / "temp", content_dir=content_dir)

    # The plain name belongs to org1, so the second repo is qualified instead
    # of overwriting the published line.
    assert (
        cloner.resolve_repo_name("https://github.com/org2/api") == "org2-api"
    )

    # An explicit name that is already taken is a hard conflict.
    with pytest.raises(RepoNameCollisionError):
        cloner.resolve_repo_name(
            "https://github.com/org2/other", name="api"
        )


def test_reingesting_the_same_source_keeps_its_name(tmp_path):
    content_dir = tmp_path / "content"
    published = content_dir / "api"
    published.mkdir(parents=True)
    (published / "toc.json").write_text(
        json.dumps({"repo_name": "api", "source": "https://github.com/org1/api"}),
        encoding="utf-8",
    )

    cloner = RepoCloner(temp_dir=tmp_path / "temp", content_dir=content_dir)

    assert cloner.resolve_repo_name("https://github.com/org1/api") == "api"


def test_explicit_name_wins_for_a_member_service(tmp_path):
    """System ingestion names its members, so the URL never decides."""
    cloner = RepoCloner(temp_dir=tmp_path / "temp")

    assert (
        cloner.resolve_repo_name("https://github.com/org1/billing-api", name="billing")
        == "billing"
    )


def test_sanitize_still_strips_path_escapes():
    assert sanitize_repo_name("../../escape-attempt") == "escape-attempt"
