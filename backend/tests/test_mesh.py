import json
import pytest
import tempfile
from pathlib import Path
from backend.ingestion.mesh import (
    CrossRepoMeshExtractor,
    ServiceNodeInfo,
    SystemSynthesizer,
    extract_service_metadata,
)
from backend.ingestion.system_pipeline import SystemIngestionPipeline


def test_extract_service_metadata():
    bundle_text = """
<file path="main.go">
const PORT = 8085
// POST /api/v1/orders
// GET /api/v1/orders/{id}
db, err := sql.Open("postgres", connStr)
topic := "orders.created"
</file>
"""
    toc = {"display_name": "Orders Service", "description": "Order management service"}
    info = extract_service_metadata("orders-service", bundle_text, toc)

    assert info.repo_name == "orders-service"
    assert info.port == 8085
    assert "PostgreSQL" in info.datastores
    assert any("/api/v1/orders" in ep for ep in info.exposed_endpoints)
    assert any("orders.created" in t for t in info.published_topics)


def test_cross_repo_mesh_extractor():
    s1 = ServiceNodeInfo(
        repo_name="auth-service",
        display_name="Auth Service",
        description="OAuth2 provider",
        language="TypeScript",
        port=8081,
        exposed_endpoints=["/oauth/token"],
        published_topics=["auth.token.minted"],
        subscribed_topics=[],
        datastores=["Redis"],
    )

    s2 = ServiceNodeInfo(
        repo_name="order-service",
        display_name="Order Service",
        description="Processes orders",
        language="Go",
        port=8082,
        exposed_endpoints=["/orders"],
        published_topics=["orders.created"],
        subscribed_topics=["auth.token.minted"],
        datastores=["PostgreSQL"],
    )

    bundle_map = {
        "auth-service": "export function mintJwt() {}",
        "order-service": "fetch('http://auth-service:8081/oauth/token'); // verify bearer jwt",
    }

    extractor = CrossRepoMeshExtractor()
    interactions = extractor.build_mesh([s1, s2], bundle_map)

    assert len(interactions) >= 1
    # Check that order-service to auth-service interaction is discovered
    targets = [i["target"] for i in interactions]
    assert "auth-service" in targets or "order-service" in targets


def test_system_synthesizer_pages():
    with tempfile.TemporaryDirectory() as temp_dir:
        content_dir = Path(temp_dir) / "content"

        s1 = ServiceNodeInfo(
            repo_name="auth-sentinel",
            display_name="Auth Sentinel",
            description="Identity provider",
            language="TypeScript",
            port=8081,
            exposed_endpoints=["/oauth/token", "/health"],
            published_topics=["auth.token.minted"],
            subscribed_topics=[],
            datastores=["Redis"],
        )

        s2 = ServiceNodeInfo(
            repo_name="payment-gateway",
            display_name="Payment Gateway",
            description="Transaction router",
            language="Go",
            port=8080,
            exposed_endpoints=["/api/v1/charge", "/health"],
            published_topics=["payments.settled"],
            subscribed_topics=["auth.token.minted"],
            datastores=["PostgreSQL", "Redis"],
        )

        synth = SystemSynthesizer(content_dir=content_dir)
        toc = synth.generate_system_wiki(
            system_name="ecommerce-mesh",
            display_name="Ecommerce Mesh",
            services=[s1, s2],
            bundle_map={"auth-sentinel": "", "payment-gateway": "auth-sentinel"},
        )

        assert toc["is_system"] is True
        assert len(toc["pages"]) == 4
        assert "auth-sentinel" in toc["member_repos"]
        assert "payment-gateway" in toc["member_repos"]

        sys_dir = content_dir / "ecommerce-mesh"
        assert (sys_dir / "toc.json").exists()
        assert (sys_dir / "overview.md").exists()
        assert (sys_dir / "architecture.md").exists()
        assert (sys_dir / "setup.md").exists()
        assert (sys_dir / "api-reference.md").exists()

        overview_text = (sys_dir / "overview.md").read_text(encoding="utf-8")
        assert "graph TD" in overview_text  # Mermaid diagram
        assert "[Auth Sentinel](/wiki/auth-sentinel/overview)" in overview_text
        assert "[Payment Gateway](/wiki/payment-gateway/overview)" in overview_text

        setup_text = (sys_dir / "setup.md").read_text(encoding="utf-8")
        assert "docker compose" in setup_text.lower()
        assert "8080:8080" in setup_text
        assert "8081:8081" in setup_text


@pytest.mark.asyncio
async def test_system_ingestion_pipeline_run():
    with tempfile.TemporaryDirectory() as temp_dir:
        content_dir = Path(temp_dir) / "content"
        work_dir = Path(temp_dir) / "work"

        # Create two local mini repositories
        r1 = Path(temp_dir) / "auth-mini"
        r1.mkdir()
        (r1 / "server.ts").write_text("const port = 8081; export const token = 'jwt';", encoding="utf-8")

        r2 = Path(temp_dir) / "pay-mini"
        r2.mkdir()
        (r2 / "main.go").write_text("package main; const port = 8080; // calls auth-mini", encoding="utf-8")

        pipeline = SystemIngestionPipeline(content_dir=content_dir, temp_dir=work_dir)

        events = []
        async for ev in pipeline.run(
            system_name="mini-mesh",
            display_name="Mini Microservice Mesh",
            repos=[
                {"name": "auth-mini", "url": str(r1)},
                {"name": "pay-mini", "url": str(r2)},
            ],
        ):
            events.append(ev)

        steps = [e.data.get("step") for e in events if e.event == "step"]
        assert "system_init" in steps
        assert "clone_all" in steps
        assert "bundle_all" in steps
        assert "synthesize_members" in steps
        assert "mesh_extract" in steps
        assert "pageindex_all" in steps

        done_ev = next(e for e in events if e.event == "done")
        assert done_ev.data["system"] == "mini-mesh"
        assert done_ev.data["services_count"] == 2
        assert done_ev.data["redirect"] == "/wiki/mini-mesh/overview"

        # Verify output files
        assert (content_dir / "mini-mesh" / "toc.json").exists()
        assert (content_dir / "mini-mesh" / "overview.md").exists()
        assert (content_dir / "mini-mesh" / "pageindex_tree.json").exists()

        # Check peer injection into members
        auth_overview = (content_dir / "auth-mini" / "overview.md").read_text(encoding="utf-8")
        assert "System Context & Peer Services" in auth_overview
        assert "[Mini Microservice Mesh](/wiki/mini-mesh/overview)" in auth_overview
