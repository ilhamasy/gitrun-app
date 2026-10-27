# GoWiki

> **Autonomous Department Codebase Documentation & Vectorless Reasoning Chatbot**  
> Compiles undocumented repositories into browsable, transit-wayfinding technical wikis with a hierarchical PageIndex tree index. Every claim in chat is grounded and cited to the exact documentation section.

---

## Why GoWiki?

Department microservices suffer from documentation rot: engineers write code, not docs, and new hires struggle to trace architectures across dozens of repositories.

Traditional vector RAG fails on codebases:
- Random chunking destroys file hierarchies and class/module relationships.
- Semantic similarity search returns text that sounds similar instead of what is logically relevant.
- Opaque chunk IDs hallucinate without traceable context.

**GoWiki uses vectorless PageIndex retrieval:**
1. **Two-Pass Doc Synthesis**: Repomix bundles the codebase into a noise-free XML skeleton; LLM pass 1 extracts a structured Table of Contents, and parallel pass 2 generates comprehensive Markdown pages (`overview`, `architecture`, `setup`, `api-reference`).
2. **Hierarchical PageIndex Tree**: Markdown headings (`#`, `##`, `###`) are compiled into a structured tree index (`pageindex_tree.json`) with section summaries.
3. **Reasoning-Based Chat**: An LLM (or deterministic local reader) reasons down the tree like an engineer reading a table of contents, citing the exact document node and section anchor (`/wiki/<repo>/<slug>#<anchor>`).

---

## Tech Stack

- **Frontend**: Next.js 16 (App Router, Turbopack, Cache Components, React 19, Tailwind CSS v4)
- **UI Design System**: Transit wayfinding metaphor ("The Signal Box"), zero border-radius, hairline rules, WCAG AA compliance
- **Backend Service**: Python 3.11+ FastAPI, Uvicorn, Pydantic v2, HTTPX
- **PageIndex Engine**: Hierarchical Markdown AST parser, tree summarizer, and multi-step reasoning engine
- **LLM Gateway**: 9router / OpenAI-compatible endpoint (`gpt-4o-mini`, etc.)

---

## Architecture

```
User / Browser
   │
   ▼
Frontend (Next.js :3000)
├── Wiki Reader (`/wiki/:repo/:slug`) ──── Read disk ───┐
├── Reasoning Chat (`/chat?repo=:repo`)                 │
└── Ingestion Stepper (`/generate`)                     │
   │                                                    │
   ▼ SSE Stream                                         ▼
Backend API (FastAPI :8000)                   content/<repo>/
├── POST /api/chat (PageIndex Reasoning)       ├── toc.json
├── GET  /api/repos                            ├── pageindex_tree.json
├── GET  /api/repos/{repo}/tree                ├── overview.md
├── POST /api/repos/{repo}/index               ├── architecture.md
└── POST /api/generate/stream                  ├── setup.md
   │                                           └── api-reference.md
   ▼
LLM Gateway (9router / OpenAI)
```

---

## Project Structure

```
go-wiki/
├── app/
│   ├── api/chat/route.ts       # SSE chat route: proxies to FastAPI, local PageIndex fallback
│   ├── chat/page.tsx           # Reasoning chat surface with line selector & starters
│   ├── generate/page.tsx       # Live ingestion progress stepper
│   ├── wiki/                   # Wiki line board & reader (/wiki/:repo/:slug)
│   ├── globals.css             # Transit design tokens, typography, and theme definitions
│   └── layout.tsx              # Root shell with enamel Masthead
├── backend/
│   ├── main.py                 # FastAPI application and route endpoints
│   ├── requirements.txt        # Backend dependencies
│   ├── pageindex/
│   │   ├── parser.py           # Markdown AST heading parser and section extractor
│   │   ├── indexer.py          # Builds and validates pageindex_tree.json
│   │   ├── llm.py              # LLM client for 9router / OpenAI endpoints
│   │   └── reasoning.py        # 3-step vectorless reasoning & streaming engine
│   └── tests/                  # Pytest test suite for parser, indexer, API, reasoning
├── components/
│   ├── chat/                   # Container, answer entry, question entry, starters, input
│   ├── line-rail.tsx           # Vertical / horizontal transit rail line navigation
│   ├── reading-column.tsx      # Markdown typography column with section anchor links
│   ├── route-strip.tsx         # Full-width line identity and node count strip
│   └── masthead.tsx            # Enamel masthead with primary destinations
├── content/                    # Seeded and generated repository documentation
│   ├── payment-gateway/        # 4-page Go payment router fixture
│   └── auth-sentinel/          # 3-page TypeScript OAuth2 identity provider fixture
├── lib/
│   ├── chat.ts                 # Chat types, stream contracts, and starter prompt catalogue
│   ├── pageindex.ts            # Local TypeScript PageIndex reader & section extractor
│   ├── stations.ts             # Line hues, slugging, heading numbering, and schemas
│   └── wiki.ts                 # Disk loader with path traversal security containment
├── docs/                       # Phase specifications (Phase 1 through Phase 6)
├── DESIGN.md                   # Formal transit wayfinding design standard
├── PLAN.md                     # Master roadmap and contract specification
└── PRODUCT.md                  # Product purpose, positioning, and operating principles
```

---

## Getting Started

### Prerequisites

- Node.js 20+ and npm
- Python 3.11+
- Git

### 1. Frontend Setup

```bash
# Install dependencies
npm install

# Run Next.js in development mode
npm run dev
```

Frontend runs on [http://localhost:3000](http://localhost:3000).

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI backend
uvicorn backend.main:app --reload --port 8000
```

Backend API runs on [http://localhost:8000](http://localhost:8000) (Swagger docs at `/docs`).

---

## Environment Variables

### Frontend (`.env.local`)
Optional. Defaults to `http://localhost:8000`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

*If backend is offline, the frontend automatically falls back to the local TypeScript PageIndex reader.*

### Backend (`backend/.env`)
Optional for offline grounded mode; required for live LLM reasoning:

```env
ROUTER_API_BASE=https://api.openai.com/v1
ROUTER_API_KEY=your_key_here
ROUTER_MODEL=gpt-4o-mini
CONTENT_DIR=../content
PORT=8000
```

---

## Verification & Tests

### Frontend
```bash
# Typecheck
npx tsc --noEmit

# Lint
npx eslint app components lib

# Production build
npm run build
```

### Backend
```bash
# Activate venv and run pytest
venv\Scripts\activate
pytest backend/tests
```

---

## Phase Status

- **Phase 1: Backend Ingestion Engine** — In progress (clone, repomix, doc generator).
- **Phase 2: PageIndex Tree Engine** — Complete (FastAPI backend + 13 passing unit tests).
- **Phase 3: Frontend Wiki Reader** — Complete (transit-styled reader, syntax cells, anchor margins).
- **Phase 4: Reasoning Chat Surface** — Complete (SSE streaming, reasoning drawer, node citation links, local fallback).
- **Phase 5: Live Ingestion Stepper** — Pending (`/generate` stepper UI).
- **Phase 6: End-to-End Demo** — Pending (pitch script & rehearsal).

---

## License

MIT
