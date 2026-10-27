import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_repos():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/repos")
        assert resp.status_code == 200
        repos = resp.json().get("repos", [])
        repo_names = [r["repo_name"] for r in repos]
        assert "payment-gateway" in repo_names
        assert "auth-sentinel" in repo_names


@pytest.mark.asyncio
async def test_get_repo_tree():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/repos/payment-gateway/tree")
        assert resp.status_code == 200
        data = resp.json()
        assert data["repo"] == "payment-gateway"
        assert len(data["nodes"]) >= 10


@pytest.mark.asyncio
async def test_chat_sse_stream():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "repo": "payment-gateway",
            "messages": [
                {"role": "user", "content": "How does the system prevent double-charging?"}
            ],
        }
        resp = await ac.post("/api/chat", json=payload)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        content = resp.text
        assert "event: reasoning" in content
        assert "event: citations" in content
        assert "event: token" in content
        assert "event: done" in content


@pytest.mark.asyncio
async def test_generate_post_endpoint(tmp_path):
    # Create local demo repo for ingestion test
    demo_repo = tmp_path / "test-ingest-repo"
    demo_repo.mkdir()
    (demo_repo / "server.py").write_text("print('test server')", encoding="utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"url": str(demo_repo)}
        resp = await ac.post("/api/generate", json=payload)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        content = resp.text
        assert "event: step" in content
        assert "event: done" in content
        assert "test-ingest-repo" in content


@pytest.mark.asyncio
async def test_generate_get_stream_endpoint(tmp_path):
    demo_repo = tmp_path / "stream-test-repo"
    demo_repo.mkdir()
    (demo_repo / "main.go").write_text("package main", encoding="utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/generate/stream?url={demo_repo}")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        content = resp.text
        assert "event: step" in content
        assert "event: done" in content
        assert "stream-test-repo" in content


@pytest.mark.asyncio
async def test_generate_system_post_endpoint(tmp_path):
    s1 = tmp_path / "sys-svc-1"
    s1.mkdir()
    (s1 / "index.js").write_text("console.log('svc1')", encoding="utf-8")

    s2 = tmp_path / "sys-svc-2"
    s2.mkdir()
    (s2 / "main.py").write_text("print('svc2')", encoding="utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "system_name": "test-mesh",
            "display_name": "Test Microservice Mesh",
            "repos": [
                {"name": "sys-svc-1", "url": str(s1)},
                {"name": "sys-svc-2", "url": str(s2)},
            ],
        }
        resp = await ac.post("/api/generate/system", json=payload)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        content = resp.text
        assert "event: step" in content
        assert "event: done" in content
        assert "test-mesh" in content


@pytest.mark.asyncio
async def test_generation_never_writes_into_shipped_content(tmp_path, repo_content_dir, content_dir):
    """
    Regression guard: an API call must write into the configured content
    directory, never into the repository's own `content/` board. This suite
    once pointed CONTENT_DIR at `../content` (via backend/.env), so test runs
    published junk lines like "Test Microservice Mesh" onto the real wiki.
    """
    before = sorted(p.name for p in repo_content_dir.iterdir() if p.is_dir())

    demo_repo = tmp_path / "isolation-probe-repo"
    demo_repo.mkdir()
    (demo_repo / "main.py").write_text("print('probe')", encoding="utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/generate", json={"url": str(demo_repo)})
        assert resp.status_code == 200
        assert "event: done" in resp.text

    after = sorted(p.name for p in repo_content_dir.iterdir() if p.is_dir())
    assert after == before, f"test run leaked into content/: {set(after) - set(before)}"

    # The work landed in the sandbox instead.
    assert (content_dir / "isolation-probe-repo" / "toc.json").exists()


@pytest.mark.asyncio
async def test_chat_without_scope_searches_every_line():
    """No repo/repos means the whole board is searched — the default for chat."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat",
            json={
                "messages": [
                    {"role": "user", "content": "How are signing keys rotated?"}
                ]
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        content = resp.text
        assert "event: reasoning" in content
        assert "event: citations" in content
        assert "event: done" in content
        # Both seeded lines are in scope, so the reasoning step reports both.
        assert "payment-gateway" in content
        assert "auth-sentinel" in content


@pytest.mark.asyncio
async def test_chat_scope_narrows_to_named_repo():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat",
            json={
                "repo": "auth-sentinel",
                "messages": [
                    {"role": "user", "content": "How are signing keys rotated?"}
                ],
            },
        )
        assert resp.status_code == 200
        content = resp.text
        assert "event: done" in content
        assert "auth-sentinel" in content


@pytest.mark.asyncio
async def test_chat_unknown_scope_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/chat",
            json={
                "repo": "does-not-exist",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        assert resp.status_code == 404
