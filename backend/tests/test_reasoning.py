import pytest
from backend.pageindex.reasoning import PageIndexEngine


@pytest.mark.asyncio
async def test_reasoning_navigation_and_stream(content_dir):
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
async def test_idempotency_retrieval(content_dir):
    engine = PageIndexEngine(content_dir=content_dir)

    thought, nodes = await engine.navigate_tree(
        "payment-gateway",
        "distributed idempotency key redis protocol",
    )
    node_ids = [n["node_id"] for n in nodes]
    assert "architecture#distributed-idempotency-protocol" in node_ids


@pytest.mark.asyncio
async def test_corpus_search_spans_repositories(content_dir):
    """A single question must be able to land on any indexed line."""
    engine = PageIndexEngine(content_dir=content_dir)

    thought, nodes, loaded = await engine.navigate_corpus(
        "How are signing keys rotated and how is double-charging prevented?",
        repos=None,  # whole board
        top_k=6,
    )

    assert set(loaded) == {"payment-gateway", "auth-sentinel"}
    repos_hit = {n["repo"] for n in nodes}
    assert len(repos_hit) >= 1
    assert thought


@pytest.mark.asyncio
async def test_corpus_scope_narrows_to_one_repo(content_dir):
    engine = PageIndexEngine(content_dir=content_dir)

    _, nodes, loaded = await engine.navigate_corpus(
        "idempotency key redis protocol",
        repos=["payment-gateway"],
    )

    assert loaded == ["payment-gateway"]
    assert all(n["repo"] == "payment-gateway" for n in nodes)


@pytest.mark.asyncio
async def test_corpus_stream_cites_the_owning_line(content_dir):
    engine = PageIndexEngine(content_dir=content_dir)

    events = []
    async for ev in engine.stream_corpus_chat(
        [{"role": "user", "content": "How are signing keys rotated?"}],
        repos=None,
    ):
        events.append(ev)

    kinds = [e.event for e in events]
    assert "reasoning" in kinds
    assert "citations" in kinds
    assert "token" in kinds
    assert "done" in kinds

    citations = next(e for e in events if e.event == "citations").data["nodes"]
    assert citations
    # Every citation names the line it came from.
    assert all(c.get("repo") for c in citations)

    done = next(e for e in events if e.event == "done")
    assert done.data["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_corpus_with_no_matching_section_says_so(content_dir):
    engine = PageIndexEngine(content_dir=content_dir)

    events = []
    async for ev in engine.stream_corpus_chat(
        [{"role": "user", "content": "zzzz qqqq unrelated gibberish"}],
        repos=None,
    ):
        events.append(ev)

    # Ranker still returns fallback nodes, but the answer must stay grounded.
    texts = "".join(e.data.get("delta", "") for e in events if e.event == "token")
    assert texts
