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
