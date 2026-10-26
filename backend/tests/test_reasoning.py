import pytest
from pathlib import Path
from backend.pageindex.reasoning import PageIndexEngine


@pytest.mark.asyncio
async def test_reasoning_navigation_and_stream():
    content_dir = Path("content")
    engine = PageIndexEngine(content_dir=content_dir)

    query = "How does the system prevent double-charging?"
    events = []
    async for ev in engine.stream_chat(
        "payment-gateway",
        [{"role": "user", "content": query}],
    ):
        events.append(ev)

    event_types = [e.event for e in events]
    assert "reasoning" in event_types
    assert "citations" in event_types
    assert "token" in event_types
    assert "done" in event_types

    reasoning_ev = next(e for e in events if e.event == "reasoning")
    assert reasoning_ev.data["step"] == "inspecting_tree"
    assert "thought" in reasoning_ev.data

    citations_ev = next(e for e in events if e.event == "citations")
    assert len(citations_ev.data["nodes"]) >= 1

    tokens = [e.data["delta"] for e in events if e.event == "token"]
    full_text = "".join(tokens)
    assert len(full_text) > 50

    done_ev = next(e for e in events if e.event == "done")
    assert done_ev.data["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_idempotency_retrieval():
    content_dir = Path("content")
    engine = PageIndexEngine(content_dir=content_dir)

    thought, nodes = await engine.navigate_tree(
        "payment-gateway",
        "distributed idempotency key redis protocol",
    )
    node_ids = [n["node_id"] for n in nodes]
    assert "architecture#distributed-idempotency-protocol" in node_ids
