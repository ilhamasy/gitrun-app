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
from backend.ingestion.synthesizer import DocSynthesizer
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

    # The literal is recorded, but its direction is not guessed from its name.
    # Only a publish/consume call site may assign a direction.
    assert "orders.created" in info.declared_topics
    assert info.published_topics == []
    assert info.subscribed_topics == []


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


def test_no_fabricated_infrastructure_in_system_wiki():
    """
    Regression guard for the reported bug: a mesh of two trivial services used
    to be documented with Kafka, Redis, PostgreSQL, a payment gateway, an auth
    service, and idempotency headers — none of which existed in the repos.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        content_dir = Path(temp_dir) / "content"

        s1 = ServiceNodeInfo(
            repo_name="sys-svc-1",
            display_name="System Service 1",
            description="Minimal Node.js stub.",
            language="JavaScript",
        )
        s2 = ServiceNodeInfo(
            repo_name="sys-svc-2",
            display_name="System Service 2",
            description="Minimal Python stub.",
            language="Python",
        )

        synth = SystemSynthesizer(content_dir=content_dir)
        synth.generate_system_wiki(
            system_name="test-mesh",
            display_name="Test Microservice Mesh",
            services=[s1, s2],
            bundle_map={
                "sys-svc-1": "console.log('svc1')",
                "sys-svc-2": "print('svc2')",
            },
        )

        sys_dir = content_dir / "test-mesh"
        combined = "\n".join(
            (sys_dir / f"{slug}.md").read_text(encoding="utf-8")
            for slug in ["overview", "architecture", "setup", "api-reference"]
        )

        for invented in (
            "Kafka",
            "kafka",
            "Redis",
            "PostgreSQL",
            "Stripe",
            "Adyen",
            "Auth Sentinel",
            "Payment Gateway",
            "Idempotency-Key",
            "payment.settled",
            "OpenTelemetry",
        ):
            assert invented not in combined, f"system wiki invented '{invented}'"

        # It must also say plainly that nothing was found.
        assert "No inter-service communication was detected" in combined
        assert "No message broker library" in combined


def test_no_synthetic_edge_when_repos_do_not_reference_each_other():
    """A sparse mesh must stay sparse instead of gaining a demo edge."""
    s1 = ServiceNodeInfo(
        repo_name="alpha-svc",
        display_name="Alpha",
        description="unrelated",
        language="Go",
        published_topics=["alpha.events"],
    )
    s2 = ServiceNodeInfo(
        repo_name="beta-svc",
        display_name="Beta",
        description="unrelated",
        language="Go",
        subscribed_topics=["beta.events"],
    )

    extractor = CrossRepoMeshExtractor()
    interactions = extractor.build_mesh(
        [s1, s2],
        {"alpha-svc": "package main", "beta-svc": "package main"},
    )
    assert interactions == []


def test_real_reference_is_detected_with_evidence():
    """A genuine call site is still discovered, and carries its evidence."""
    s1 = ServiceNodeInfo(
        repo_name="checkout-api",
        display_name="Checkout API",
        description="frontend",
        language="Go",
        env_vars=["INVENTORY_SERVICE_URL"],
    )
    s2 = ServiceNodeInfo(
        repo_name="inventory-service",
        display_name="Inventory Service",
        description="stock",
        language="Go",
        port=8090,
    )

    extractor = CrossRepoMeshExtractor()
    interactions = extractor.build_mesh(
        [s1, s2],
        {
            "checkout-api": 'fetch("http://inventory-service:8090/stock")',
            "inventory-service": "package main",
        },
    )

    assert len(interactions) == 1
    assert interactions[0]["source"] == "checkout-api"
    assert interactions[0]["target"] == "inventory-service"
    assert interactions[0]["evidence"]


def test_member_fallback_pages_do_not_invent_endpoints():
    """Offline member pages must not print made-up routes or env vars."""
    with tempfile.TemporaryDirectory() as temp_dir:
        content_dir = Path(temp_dir) / "content"
        synth = DocSynthesizer(content_dir=content_dir)

        bundle = """<repository name="tiny-svc">
<file path="tiny-svc/main.go">package main
func main() { http.ListenAndServe(":8099", nil) }
</file>
</repository>"""

        toc = {"display_name": "Tiny Service", "language": "Go", "description": "tiny"}
        for slug in ["overview", "architecture", "setup", "api-reference"]:
            md = synth._fallback_page_markdown(
                repo_name="tiny-svc",
                slug=slug,
                title=slug.title(),
                description="",
                bundle_content=bundle,
                toc=toc,
            )
            assert "/api/v1/execute" not in md
            assert "/api/v1/status" not in md
            assert "Redis" not in md
            assert "Kafka" not in md
            assert "Bearer tokens" not in md


def test_filenames_are_not_detected_as_message_topics():
    """`main.py` matches a dotted-identifier regex; it is a filename, not a topic."""
    bundle = '<file path="main.py">import os\nprint("svc2")\nx = "main.py"\n</file>'
    info = extract_service_metadata("sys-svc-2", bundle, {})
    assert info.declared_topics == []

    real = extract_service_metadata("svc", 'producer.send("orders.created", p)', {})
    assert real.declared_topics == ["orders.created"]
    assert real.published_topics == ["orders.created"]
