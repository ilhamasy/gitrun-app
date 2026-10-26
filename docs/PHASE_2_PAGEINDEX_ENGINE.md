# Phase 2 Specification: PageIndex Tree Search & Reasoning Engine

**Status**: Completed  
**Core Innovation**: Vectorless, reasoning-based document retrieval. No embeddings, no vector databases.

---

## 1. Indexing Workflow
1. Triggered immediately after Phase 1 markdown generation.
2. For each markdown file in `content/<repo_name>/`:
   - Parse markdown headings (`#`, `##`, `###`) and section boundaries.
   - For each section, prompt 9router for a dense 1–2 sentence semantic summary.
   - Construct tree structure:
     - `node_id`: `<slug>#<kebab-case-heading>`
     - `title`: heading text
     - `file`: `<slug>.md`
     - `summary`: dense summary
3. Write `content/<repo_name>/pageindex_tree.json`.

---

## 2. Retrieval & Reasoning Workflow (`/api/chat`)
1. User submits prompt: `"How does the service handle database reconnection?"`
2. **Step 1: Tree Navigation (Reasoning)**:
   - Provide LLM with tree index (hierarchy + node titles + summaries).
   - LLM analyzes question and selects 1–3 most relevant `node_id`s in JSON array.
3. **Step 2: Section Extraction**:
   - Backend reads exact markdown text corresponding to selected `node_id`s.
4. **Step 3: Synthesis & Streaming**:
   - Backend constructs synthesis prompt with retrieved sections as authoritative source.
   - Streams answer token-by-token with clickable citations.
