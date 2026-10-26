# Phase 1 Specification: Backend Ingestion Engine

**Status**: Pending  
**Tech**: Python 3.11, FastAPI, Repomix CLI, 9router LLM gateway  
**Target Path**: `backend/`

---

## 1. Responsibilities
1. Receive Git repo URL or local path via `POST /api/generate`.
2. Execute shallow clone into isolated temporary folder: `temp/<repo_name>`.
3. Run Repomix packing with ignore filters:
   ```bash
   npx repomix --style xml --output temp/<repo_name>-bundle.xml --ignore "**/node_modules/**,**/.git/**,**/dist/**,**/*lock*,**/*.png,**/*.svg,**/*_test.go,**/*.spec.ts"
   ```
4. Execute **Two-Pass Doc Synthesis**:
   - **Pass 1**: Send bundle topology to 9router (`POST /v1/chat/completions`) with strict JSON output schema. Extracts repository summary, tech stack, and 4 standardized page definitions (`overview`, `architecture`, `setup`, `api-reference`). Saves `content/<repo_name>/toc.json`.
   - **Pass 2**: Fire 4 parallel LLM requests with `asyncio.gather()`, each tasked with generating one in-depth markdown file with diagrams, tables, and code snippets.
5. Save markdown files to `content/<repo_name>/<slug>.md`.
6. Stream progress updates over SSE (`GET /api/generate/stream?id=...`).
