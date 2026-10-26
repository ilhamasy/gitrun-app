# Phase 4 Specification: Reasoning Chat Interface

**Status**: Done (local engine); model engine pending Phase 2  
**Focus**: Conversational surface powered by PageIndex tree-reasoning retrieval.

---

## 0. What shipped

- `app/chat/page.tsx` — server page; selects the line from `?repo=`, renders the real surface.
- `lib/chat.ts` — the stream contract, citation links, and curated starter questions.
- `lib/pageindex.ts` — the vectorless reader: heading parse, term ranking, verbatim quoting.
- `app/api/chat/route.ts` — `POST /api/chat` streaming SSE; proxies a reasoning service when
  `ROUTER_API_BASE` is set, otherwise answers locally from `content/`.
- `components/chat/*` — container, answer entry, question entry, starters, composer.

The local engine ranks node titles, summaries, and section bodies with an inverse-document-frequency
weighting, opens the top three sections, and quotes the passages that carry the question's terms.
Nothing is paraphrased: the answer is assembled from sentences that exist in the generated wiki, and
each block names the node it came from. A question the index cannot route says so and lists the nodes
it opened instead of inventing an answer.

Every answer labels its engine (`Local index reader` / `Reasoning service`), so a reader can tell a
quoted extract from a written synthesis.

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
app/chat/page.tsx (Server Component: reads ?repo=, loads trees, renders)
 └─ components/chat/chat-container.tsx (Client: thread state, SSE reader)
     ├─ repo selector + clear thread + node/page counts
     ├─ components/chat/starter-prompts.tsx (empty thread)
     ├─ components/chat/question-entry.tsx (asked question)
     ├─ components/chat/answer-entry.tsx
     │   ├─ step drawer (the real tree walk, not a scripted animation)
     │   ├─ components/reading-column.tsx (answer markdown, same renderer as the wiki)
     │   └─ citation list → /wiki/<repo>/<slug>#<anchor>
     └─ components/chat/chat-input.tsx (composer, Enter sends, Stop aborts)
```

The answer text is rendered by the wiki's own `ReadingColumn`, so a quoted section looks exactly
like the section it was read from — same measure, same code cells, same heading rules.

---

## 3. API Contract (`POST /api/chat`)
`app/api/chat/route.ts` implements the contract so the surface is never blocked on the Python
service.

- If `ROUTER_API_BASE` is set, the request is proxied to `<base>/api/chat` and its events are
  forwarded unchanged. A timeout, a non-OK reply, or a stream with no events falls through to the
  local engine rather than failing the turn.
- Otherwise the local PageIndex reader answers from `lib/pageindex.ts` and `pageindex_tree.json`.

Request:
```json
{ "repo": "payment-gateway", "messages": [{ "role": "user", "content": "…" }] }
```

One JSON object per `data:` line, `\n\n`-delimited:

| Event | Payload |
| :--- | :--- |
| `step` | `{"type":"step","step":"Ranked the tree","detail":"3 of 16 nodes match the question"}` |
| `nodes` | `{"type":"nodes","nodes":[{"node_id":"architecture#distributed-idempotency-protocol","title":"…","file":"architecture.md","summary":"…"}]}` |
| `token` | `{"type":"token","delta":"…"}` — word-aligned, never half a word |
| `done` | `{"type":"done","engine":"local"}` |
| `error` | `{"type":"error","message":"…"}` |

Status codes: `400` for a missing repo, missing user message, or unparseable body; `404` for a repo
with no `toc.json`. Repository names and page slugs are resolved through `contentPath()` in
`lib/wiki.ts`, which rejects anything escaping `content/` — the surface can read a compiled wiki and
nothing else.
