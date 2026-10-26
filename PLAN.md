# GoWiki: Master Project Plan & Architecture Contract

**Hackathon Project**: Autonomous Department Codebase Documentation & Vectorless Reasoning Chatbot  
**Tech Stack**: Next.js 16 (React 19, Tailwind v4, shadcn/ui) + Python 3.11 FastAPI + Repomix + 9router LLM + VectifyAI PageIndex Tree Search  
**Target Completion**: Hackathon Demo Ready

---

## 1. Problem & Product Vision

### The Problem
Department repositories suffer from documentation rot:
- High engineering friction: developers write code, not documentation.
- Onboarding pain: new hires struggle to trace architectures across tens of microservices.
- Traditional RAG fails for codebases: chunking destroys file hierarchy, loses class/module relationships, and hallucinates without whole-repo context.

### The Solution: GoWiki
1. **Automated Ingestion**: Repomix bundles repositories into token-efficient XML skeletons with noise stripped (tests, lockfiles, binaries).
2. **Two-Pass Doc Synthesis**:
   - *Pass 1*: Fast LLM scan generates structured Table of Contents (TOC) schema (`overview`, `architecture`, `setup`, `api-reference`).
   - *Pass 2*: Parallel worker pool generates comprehensive Markdown files per section.
3. **Interactive Wiki**: Next.js web application rendering instant documentation with breadcrumbs, syntax highlighting, and section anchors.
4. **PageIndex Tree-Reasoning AI**: Replaces vector databases. LLM reasons over the hierarchical tree index (TOC + node summaries) to pinpoint exact markdown nodes, retrieving verified context with verifiable citations.

---

## 2. System Architecture & Boundaries

```mermaid
graph TD
  User([User / Judge]) -->|Browser| Frontend[Next.js App :3000]

  subgraph Frontend Layer
    Nav[Navbar & Directory] --> WikiView[Wiki Reader /wiki/:repo/:slug]
    Nav --> ChatView[Reasoning Chat /chat]
    Nav --> IngestView[Ingest Stepper /generate]
  end

  subgraph Backend Service [FastAPI :8000]
    API_Gen[/api/generate/stream]
    API_Chat[/api/chat]
    API_Repos[/api/repos]
  end

  subgraph Core Pipeline
    GitClone[Git Shallow Clone] --> RepomixPack[Repomix XML Pack]
    RepomixPack --> Pass1[LLM Pass 1: TOC Schema]
    Pass1 --> Pass2[LLM Pass 2: Parallel Page Gen]
    Pass2 --> MarkdownStore[Local content/ Store]
    MarkdownStore --> TreeBuilder[PageIndex Tree Builder]
    TreeBuilder --> IndexFile[pageindex_tree.json]
  end

  subgraph LLM Provider [9router Gateway]
    Pass1 & Pass2 & TreeBuilder & API_Chat -->|OpenAI Compatible API| Router[9router Endpoint]
  end

  IngestView -->|SSE Stream| API_Gen
  ChatView -->|Streaming POST| API_Chat
  API_Gen --> CorePipeline
  WikiView -.->|Server Component Read| MarkdownStore
```

---

## 3. Shared Contracts & Data Schemas

### A. Repository TOC Schema (`content/<repo>/toc.json`)
Every documented repository must provide this file:
```json
{
  "repo_name": "payment-gateway",
  "display_name": "Payment Gateway Service",
  "description": "High-throughput transaction router with distributed idempotency.",
  "language": "Go",
  "stars": 128,
  "pages": [
    {
      "slug": "overview",
      "title": "System Overview",
      "description": "Core responsibilities, business domain, and high-level system boundaries."
    },
    {
      "slug": "architecture",
      "title": "Internal Architecture",
      "description": "Package organization, event queues, concurrency models, and ledger consistency."
    },
    {
      "slug": "setup",
      "title": "Setup & Configuration",
      "description": "Local development with Docker Compose, environment variables, and migration runs."
    },
    {
      "slug": "api-reference",
      "title": "API Reference",
      "description": "REST and gRPC contracts, error codes, and idempotent transaction flows."
    }
  ]
}
```

### B. PageIndex Tree Schema (`content/<repo>/pageindex_tree.json`)
The vectorless index parsed from Markdown headings:
```json
{
  "repo": "payment-gateway",
  "generated_at": "2026-10-26T12:00:00Z",
  "nodes": [
    {
      "node_id": "overview#core-capabilities",
      "file": "overview.md",
      "title": "Core Capabilities",
      "level": 2,
      "summary": "Outlines idempotent charge pipeline, provider multi-tenancy, webhook ingestion, and immutable financial ledger."
    },
    {
      "node_id": "architecture#distributed-idempotency-protocol",
      "file": "architecture.md",
      "title": "Distributed Idempotency Protocol",
      "level": 2,
      "summary": "Step-by-step Redis lock acquisition, execution, ledger persistence, and error release protocol."
    }
  ]
}
```

### C. Live Ingestion Event Stream (`GET /api/generate/stream`)
Server-Sent Events format emitted during live ingestion:
```json
event: step
data: {"step": "clone", "status": "running", "message": "Cloning repository (depth 1)..."}

event: step
data: {"step": "bundle", "status": "running", "message": "Packing codebase with Repomix..."}

event: step
data: {"step": "toc", "status": "running", "message": "Synthesizing Table of Contents..."}

event: step
data: {"step": "doc_gen", "status": "running", "progress": "3/4 pages generated"}

event: step
data: {"step": "pageindex", "status": "running", "message": "Building hierarchical tree index..."}

event: done
data: {"step": "completed", "repo": "payment-gateway", "redirect": "/wiki/payment-gateway/overview"}
```

### D. Chat Request & Reasoning SSE Protocol (`POST /api/chat`)
**Request**:
```json
{
  "repo": "payment-gateway",
  "messages": [
    { "role": "user", "content": "How does the system prevent double-charging?" }
  ]
}
```

**SSE Event Types**:
1. `event: reasoning`: `{"step": "inspecting_tree", "thought": "Searching tree for idempotency and charge deduplication..."}`
2. `event: citations`: `{"nodes": [{"node_id": "architecture#distributed-idempotency-protocol", "title": "Distributed Idempotency Protocol", "file": "architecture.md"}]}`
3. `event: token`: `{"delta": "The system enforces idempotency using Redis-backed distributed locks..."}`
4. `event: done`: `{"finish_reason": "stop"}`

---

## 4. Phase-by-Phase Roadmap & Ownership

| Phase | Title | Scope & Artifacts | Status | Owner |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | **Backend Ingestion Engine** | Python FastAPI, Git clone, Repomix runner, 2-Pass LLM generator, writes to `content/` | Pending | Backend |
| **Phase 2** | **PageIndex Tree Engine** | Markdown heading AST parser, LLM node summarizer, `/api/chat` tree-reasoning & streaming | **COMPLETED** | Backend / AI |
| **Phase 3** | **Frontend Wiki Reader** | Tailwind v4 + shadcn UI, layout, sidebar, markdown renderer, table of contents, seed data | **COMPLETED** | Frontend |
| **Phase 4** | **Reasoning Chat Surface** | Dedicated `/chat` page, ChatGPT-style layout, node citation drawer, SSE streaming reader | **IN PROGRESS** | Fullstack |
| **Phase 5** | **Live Ingestion Stepper** | `/generate` page, URL input, real-time SSE progress tracker, auto-redirect on finish | Pending | Frontend |
| **Phase 6** | **End-to-End Integration & Demo** | Docker compose / run script, 9router credentials, rehearse 3-minute pitch scenario | Pending | Team |

---

## 5. Development Conventions & Running the Project

### Environment Variables
`.env.local` (Next.js):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`backend/.env` (FastAPI):
```env
ROUTER_API_BASE=https://9router.your-domain.com/v1
ROUTER_API_KEY=your_key_here
ROUTER_MODEL=gpt-4o-mini
CONTENT_DIR=../content
TEMP_DIR=../temp
```

### Commands
```bash
# Frontend (Terminal 1)
npm run dev

# Backend (Terminal 2)
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
