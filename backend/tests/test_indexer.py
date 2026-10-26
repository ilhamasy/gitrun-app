import pytest
from pathlib import Path
from backend.pageindex.indexer import TreeIndexer


@pytest.mark.asyncio
async def test_tree_indexer_dry_run():
    content_dir = Path("content")
    indexer = TreeIndexer(content_dir=content_dir)

    tree = await indexer.build_repo_tree("payment-gateway", dry_run=True)
    assert tree["repo"] == "payment-gateway"
    assert "generated_at" in tree
    assert len(tree["nodes"]) == 16

    node_ids = [n["node_id"] for n in tree["nodes"]]
    assert "overview#core-capabilities" in node_ids
    assert "architecture#distributed-idempotency-protocol" in node_ids

    for node in tree["nodes"]:
        assert "node_id" in node
        assert "title" in node
        assert "file" in node
        assert "level" in node
        assert "summary" in node
        assert len(node["summary"]) > 0


@pytest.mark.asyncio
async def test_tree_indexer_auth_sentinel():
    content_dir = Path("content")
    indexer = TreeIndexer(content_dir=content_dir)

    tree = await indexer.build_repo_tree("auth-sentinel", dry_run=True)
    assert tree["repo"] == "auth-sentinel"
    assert len(tree["nodes"]) >= 5

    node_ids = [n["node_id"] for n in tree["nodes"]]
    assert "overview#supported-protocols" in node_ids
    assert "architecture#asymmetric-key-rotation" in node_ids
