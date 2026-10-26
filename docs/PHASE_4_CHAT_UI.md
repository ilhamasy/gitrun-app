# Phase 4 Specification: Reasoning Chat Interface

**Status**: In Progress  
**Focus**: ChatGPT-style conversational surface powered by PageIndex tree-reasoning retrieval.

---

## 1. Objectives & User Experience
1. **Repository-Scoped Reasoning**:
   - Top bar contains a Repository Selector dropdown (e.g. `payment-gateway`, `auth-sentinel`).
   - Supports deep-linking via query parameter: `/chat?repo=payment-gateway`.
2. **Transparent PageIndex Citations**:
   - Unlike standard RAG that returns obscure chunk IDs, responses display explicit **PageIndex Node Badges**:
     - Example: `[Node: architecture.md#distributed-idempotency-protocol]`
     - Clicking badge links directly to that section in the Wiki reader (`/wiki/payment-gateway/architecture#distributed-idempotency-protocol`).
   - Collapsible reasoning drawer: "Inspected 2 PageIndex Tree Nodes".
3. **Streaming & Thinking Indicators**:
   - While the AI navigates the tree, UI shows real-time progress steps:
     - `Scanning document tree...`
     - `Inspecting: architecture.md#distributed-idempotency-protocol`
     - `Reading section markdown...`
     - `Synthesizing grounded response...`
4. **Starter Prompts**:
   - When thread is empty, render 3–4 repository-specific starter questions so judges can click and see instant reasoning during the pitch.

---

## 2. Component Hierarchy
```
app/chat/page.tsx (Server Component fetching repos)
 └─ components/chat/chat-container.tsx (Client Component managing message state)
     ├─ components/chat/chat-header.tsx (Repo dropdown, clear thread button)
     ├─ components/chat/chat-messages.tsx (Scrollable feed)
     │   ├─ components/chat/user-bubble.tsx
     │   ├─ components/chat/assistant-bubble.tsx
     │   │   ├─ components/chat/reasoning-steps.tsx (Collapsible step pill)
     │   │   ├─ components/chat/citations-bar.tsx (Clickable wiki node pills)
     │   │   └─ components/markdown-renderer.tsx (Answer text)
     │   └─ components/chat/starter-prompts.tsx (Clickable suggestions)
     └─ components/chat/chat-input.tsx (Prompt textarea, submit button)
```

---

## 3. API Contract (`POST /api/chat`)
To allow independent frontend development before the FastAPI service is deployed, Next.js implements `app/api/chat/route.ts`:
- Checks if FastAPI backend (`NEXT_PUBLIC_API_URL` or `http://localhost:8000/api/chat`) is available.
- If FastAPI is offline, falls back to a simulated local PageIndex tree-search reader using `lib/wiki.ts` and `pageindex_tree.json`.
- Streams response using standard SSE chunks:
  ```json
  {"type": "step", "message": "Inspecting PageIndex tree..."}
  {"type": "nodes", "nodes": [{"node_id": "architecture#distributed-idempotency-protocol", "title": "Distributed Idempotency Protocol", "file": "architecture.md"}]}
  {"type": "token", "delta": "The system prevents double-charging by..."}
  {"type": "done"}
  ```
