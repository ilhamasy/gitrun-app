"""
GoWiki Backend Service (FastAPI).
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

from backend.ingestion.pipeline import IngestionPipeline
from backend.ingestion.system_pipeline import SystemIngestionPipeline
from backend.pageindex.indexer import TreeIndexer
from backend.pageindex.llm import LLMClient
from backend.pageindex.reasoning import PageIndexEngine
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONTENT_DIR = (BASE_DIR.parent / "content").resolve()
DEFAULT_TEMP_DIR = (BASE_DIR.parent / "temp").resolve()

def _resolve_dir(env_val: Optional[str], default_path: Path) -> Path:
    if not env_val:
        return default_path
    p = Path(env_val)
    return (BASE_DIR / p).resolve() if not p.is_absolute() else p.resolve()

CONTENT_DIR = _resolve_dir(os.environ.get("CONTENT_DIR"), DEFAULT_CONTENT_DIR)
TEMP_DIR = _resolve_dir(os.environ.get("TEMP_DIR"), DEFAULT_TEMP_DIR)

app = FastAPI(
    title="GoWiki Backend API",
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
pipeline = IngestionPipeline(content_dir=CONTENT_DIR, temp_dir=TEMP_DIR, llm_client=llm_client)
system_pipeline = SystemIngestionPipeline(content_dir=CONTENT_DIR, temp_dir=TEMP_DIR, llm_client=llm_client)

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    repo: str = Field(..., description="Target repository name (e.g. 'payment-gateway')")
    messages: List[ChatMessage] = Field(..., description="Conversation history messages")


class GenerateRequest(BaseModel):
    url: str = Field(..., description="Git clone URL or local repository path")
    branch: Optional[str] = Field(None, description="Optional branch or tag to clone")


class RepoItem(BaseModel):
    name: str = Field(..., description="Repository / service name")
    url: str = Field(..., description="Git clone URL or local directory name")
    branch: Optional[str] = Field(None, description="Branch or tag")


class SystemGenerateRequest(BaseModel):
    system_name: str = Field(..., description="Unique slug for the multi-repo system")
    display_name: Optional[str] = Field(None, description="Human readable system title")
    repos: List[RepoItem] = Field(..., description="List of microservice repositories")
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "gowiki-backend",
        "llm_configured": llm_client.is_configured(),
        "content_dir": str(CONTENT_DIR),
        "temp_dir": str(TEMP_DIR),
        "pipeline_ready": True,
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


async def _stream_generation(source: str, branch: Optional[str] = None):
    async for event in pipeline.run(source=source, branch=branch):
        yield event.to_sse()


@app.post("/api/generate")
async def generate_endpoint(payload: GenerateRequest):
    """
    Triggers repository ingestion pipeline and streams SSE progress events.
    Supports remote Git repository URLs and local file system paths.
    """
    return StreamingResponse(
        _stream_generation(source=payload.url, branch=payload.branch),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/generate/stream")
async def generate_stream_endpoint(url: str, branch: Optional[str] = None):
    """
    EventSource / SSE GET endpoint for real-time live ingestion streaming.
    """
    return StreamingResponse(
        _stream_generation(source=url, branch=branch),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_system_generation(
    system_name: str,
    repos: List[Dict[str, Any]],
    display_name: Optional[str] = None,
):
    async for event in system_pipeline.run(
        system_name=system_name,
        repos=repos,
        display_name=display_name,
    ):
        yield event.to_sse()


@app.post("/api/generate/system")
async def generate_system_endpoint(payload: SystemGenerateRequest):
    """
    Triggers Multi-Repo Microservice Mesh ingestion.
    Clones all member repositories in parallel, extracts inter-service interactions,
    synthesizes federated architecture with cross-links, and builds PageIndex trees.
    """
    repos_payload = [r.model_dump() for r in payload.repos]
    return StreamingResponse(
        _stream_system_generation(
            system_name=payload.system_name,
            repos=repos_payload,
            display_name=payload.display_name,
        ),
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
