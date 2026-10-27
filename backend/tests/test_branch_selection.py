"""
Branch selection end to end: ref discovery, ingestion at a chosen ref, and the
provenance recorded on the published wiki.

The wiki has to state which revision it documents, and the ingest form has to be
able to ask what revisions exist without cloning anything.
"""

import json
import subprocess
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.ingestion.pipeline import IngestionPipeline


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture()
def remote_repo(tmp_path: Path) -> Path:
    """Bare remote with `trunk` as default, a divergent `main`, and a tag."""
    work = tmp_path / "work"
    work.mkdir()
    _git(["init", "-q", "-b", "trunk"], work)
    _git(["config", "user.email", "test@example.com"], work)
    _git(["config", "user.name", "Test"], work)
    (work / "app.py").write_text("VERSION = 'trunk'\n", encoding="utf-8")
    _git(["add", "."], work)
    _git(["commit", "-qm", "trunk"], work)
    _git(["tag", "v1.0.0"], work)

    _git(["checkout", "-qb", "main"], work)
    (work / "app.py").write_text("VERSION = 'main'\n", encoding="utf-8")
    _git(["commit", "-qam", "main"], work)
    _git(["checkout", "-q", "trunk"], work)

    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(work), str(remote)],
        check=True,
        capture_output=True,
    )
    return remote


@pytest.mark.asyncio
async def test_refs_endpoint_lists_branches_and_default(remote_repo):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/refs", params={"url": f"file://{remote_repo}"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["default_branch"] == "trunk"
    assert "main" in data["branches"]
    assert data["tags"] == ["v1.0.0"]


@pytest.mark.asyncio
async def test_refs_endpoint_reports_bad_source():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/refs", params={"url": "/nope/not/a/repository"})

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_ingestion_records_requested_branch_and_commit(remote_repo, tmp_path):
    content_dir = tmp_path / "content"
    pipeline = IngestionPipeline(
        content_dir=content_dir,
        temp_dir=tmp_path / "temp",
    )

    events = []
    async for ev in pipeline.run(f"file://{remote_repo}", branch="main"):
        events.append(ev)

    done = next(e for e in events if e.event == "done")
    assert done.data["ref"] == "main"
    assert done.data["branch"] == "main"
    assert done.data["commit"]
    assert done.data["repo"] == "remote"

    toc = json.loads((content_dir / "remote" / "toc.json").read_text(encoding="utf-8"))
    assert toc["ref"] == "main"
    assert toc["branch"] == "main"
    assert toc["commit"] == done.data["commit"]
    assert toc["source"] == f"file://{remote_repo}"


@pytest.mark.asyncio
async def test_ingestion_without_branch_records_the_default_branch(remote_repo, tmp_path):
    content_dir = tmp_path / "content"
    pipeline = IngestionPipeline(
        content_dir=content_dir,
        temp_dir=tmp_path / "temp",
    )

    async for _ in pipeline.run(f"file://{remote_repo}"):
        pass

    toc = json.loads((content_dir / "remote" / "toc.json").read_text(encoding="utf-8"))
    # The remote's default is `trunk`; nothing may claim `main`.
    assert toc["branch"] == "trunk"
    assert toc["ref"] == "trunk"
    assert toc["commit"]


@pytest.mark.asyncio
async def test_tag_ingestion_records_the_tag(remote_repo, tmp_path):
    content_dir = tmp_path / "content"
    pipeline = IngestionPipeline(
        content_dir=content_dir,
        temp_dir=tmp_path / "temp",
    )

    async for _ in pipeline.run(f"file://{remote_repo}", branch="v1.0.0"):
        pass

    toc = json.loads((content_dir / "remote" / "toc.json").read_text(encoding="utf-8"))
    assert toc["ref"] == "v1.0.0"
    assert toc["commit"]


@pytest.mark.asyncio
async def test_unknown_branch_streams_an_error(remote_repo, tmp_path):
    pipeline = IngestionPipeline(
        content_dir=tmp_path / "content",
        temp_dir=tmp_path / "temp",
    )

    events = [ev async for ev in pipeline.run(f"file://{remote_repo}", branch="nope")]

    errors = [e for e in events if e.event == "error"]
    assert errors, "an unknown ref must fail the stream, not publish a wiki"
    assert not any(e.event == "done" for e in events)


@pytest.mark.asyncio
async def test_explicit_name_controls_the_wiki_line(remote_repo, tmp_path):
    content_dir = tmp_path / "content"
    pipeline = IngestionPipeline(
        content_dir=content_dir,
        temp_dir=tmp_path / "temp",
    )

    async for _ in pipeline.run(f"file://{remote_repo}", name="custom-line"):
        pass

    assert (content_dir / "custom-line" / "toc.json").exists()
    assert not (content_dir / "remote").exists()
