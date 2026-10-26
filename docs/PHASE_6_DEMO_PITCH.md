# Phase 6 Specification: Demo Runbook & Pitch Script

**Status**: Pending  
**Goal**: Flawless 3-minute hackathon pitch with zero network or rate-limit breakdowns.

---

## 1. Demo Flow (3 Minutes)

### Minute 0:00 - 0:45: The Problem & The Landing Page
- Open `http://localhost:3000`.
- Pitch hook: *"Every department has dozens of microservices with empty READMEs. Traditional RAG chops files into random 500-token chunks and hallucinates. We built GoWiki: autonomous doc generation powered by vectorless PageIndex tree reasoning."*

### Minute 0:45 - 1:45: Live Ingestion Stepper
- Click "Ingest New Repo" (`/generate`).
- Paste demo repository URL.
- Show live pipeline: Repomix bundle -> Pass 1 TOC -> Parallel Pass 2 Markdown -> PageIndex Tree Builder.
- Completes in ~30 seconds, automatically opening the newly minted Wiki.

### Minute 1:45 - 2:30: Wiki Reader Surface
- Show structured documentation (`overview`, `architecture`, `setup`, `api-reference`).
- Highlight copyable code blocks, architecture diagrams, and "On this page" right-rail anchors.

### Minute 2:30 - 3:00: PageIndex Reasoning Chat
- Jump to `/chat?repo=payment-gateway`.
- Ask complex architectural question: *"How does the system prevent double-charging?"*
- Point to the **Reasoning Pill**: show the LLM actively navigating the document tree, picking `architecture.md#distributed-idempotency-protocol`, and quoting exact invariants with a clickable citation badge.
- Closing line: *"No vector databases, no embeddings drift, 100% grounded in code."*

---

## 2. Emergency Fallbacks
1. **Wi-Fi Down**: Use pre-seeded repositories (`payment-gateway`, `auth-sentinel`). Local filesystem reads require zero internet.
2. **LLM Provider Latency**: Fallback cache in `app/api/chat/route.ts` provides instant simulated streaming if 9router network times out.
