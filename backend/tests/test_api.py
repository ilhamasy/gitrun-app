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
