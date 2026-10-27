"""
GitRun Backend Service (FastAPI).
Provides /api/chat SSE streaming with PageIndex vectorless reasoning,
repository discovery, and tree indexing endpoints.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.pageindex.indexer import TreeIndexer
from backend.pageindex.llm import LLMClient
from backend.pageindex.reasoning import PageIndexEngine

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONTENT_DIR = (BASE_DIR.parent / "content").resolve()
raw_content = os.environ.get("CONTENT_DIR")
if raw_content:
    p = Path(raw_content)
    CONTENT_DIR = p.resolve() if p.is_absolute() else (BASE_DIR / p).resolve()
else:
    CONTENT_DIR = DEFAULT_CONTENT_DIR

app = FastAPI(
    title="GitRun Backend API",
    description="Vectorless tree search, document reasoning, and repository documentation service.",
    version="0.2.0",
)

# CORS setup for local Next.js development and demo surfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate engine and indexer
llm_client = LLMClient()
engine = PageIndexEngine(content_dir=CONTENT_DIR, llm_client=llm_client)
indexer = TreeIndexer(content_dir=CONTENT_DIR, llm_client=llm_client)


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    repo: str = Field(..., description="Target repository name (e.g. 'payment-gateway')")
    messages: List[ChatMessage] = Field(..., description="Conversation history messages")


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "gitrun-backend",
        "llm_configured": llm_client.is_configured(),
        "content_dir": str(CONTENT_DIR),
    }


@app.get("/api/repos")
async def list_repositories():
    """List all available documented repositories."""
    repos = []
    if not CONTENT_DIR.exists():
        return {"repos": []}

    for child in sorted(CONTENT_DIR.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            toc_file = child / "toc.json"
            if toc_file.exists():
                try:
                    with open(toc_file, "r", encoding="utf-8") as f:
                        repos.append(json.load(f))
                except Exception:
                    continue
            else:
                # Basic metadata if toc.json is absent
                repos.append({
                    "repo_name": child.name,
                    "display_name": child.name,
                    "description": "Repository documentation",
                    "pages": [],
                })

    return {"repos": repos}


@app.get("/api/repos/{repo}/tree")
async def get_repository_tree(repo: str):
    """Get the PageIndex tree index for a repository."""
    try:
        tree = engine.load_tree(repo)
        return tree
    except FileNotFoundError:
        # If tree does not exist, build it on the fly
        try:
            return await indexer.build_repo_tree(repo)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/repos/{repo}/index")
async def reindex_repository(repo: str):
    """Trigger re-indexing of a repository's documentation into pageindex_tree.json."""
    try:
        tree = await indexer.build_repo_tree(repo)
        return {
            "status": "success",
            "repo": repo,
            "nodes_indexed": len(tree.get("nodes", [])),
            "generated_at": tree.get("generated_at"),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Repository '{repo}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    """
    PageIndex Reasoning Chat endpoint.
    Navigates tree index, extracts section text, and streams response over SSE.
    """
    repo_path = CONTENT_DIR / payload.repo
    if not repo_path.is_dir():
        raise HTTPException(status_code=404, detail=f"Repository '{payload.repo}' not found")

    # If pageindex_tree.json is missing, build it first
    tree_path = repo_path / "pageindex_tree.json"
    if not tree_path.exists():
        try:
            await indexer.build_repo_tree(payload.repo)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to build PageIndex tree for {payload.repo}: {e}",
            )

    messages_payload = [m.model_dump() for m in payload.messages]

    async def sse_event_stream():
        try:
            async for event in engine.stream_chat(
                repo_name=payload.repo,
                messages=messages_payload,
            ):
                yield event.to_sse()
        except Exception as e:
            err_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {err_data}\n\n"

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
