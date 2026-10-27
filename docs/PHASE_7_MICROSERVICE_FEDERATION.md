# Phase 7 Specification: Multi-Repo Microservice Mesh Federation

**Status**: Completed  
**Scope**: Ingestion and synthesis across multi-repository microservice architectures (1 service = 1 Git repository).  
**Target Paths**: `backend/ingestion/mesh.py`, `backend/ingestion/system_pipeline.py`, `components/ingestion-stepper.tsx`, `components/line-rail.tsx`.

---

## 1. Responsibilities

1. **Multi-Repo Ingestion**:
   - Ingest a list of microservice repositories simultaneously via `POST /api/generate/system`.
   - Parallel shallow clone (`--depth 1`) and Repomix XML bundling across member repositories.
2. **Interface & Topology Extraction (`backend/ingestion/mesh.py`)**:
   - Extract ports, exposed REST routes, and datastores.
   - Detect inter-service relationships: synchronous HTTP/gRPC client calls, shared message topics (Apache Kafka), and JWT issuer/verifier dependencies.
   - Construct interactive Mermaid system topology diagrams.
3. **Cross-Service Bidirectional Linking**:
   - Every individual microservice documentation receives an injected `## System Context & Peer Services` section with direct links to peer microservices and the federated system overview.
   - The federated system wiki (`content/<system_name>/`) links directly to every member microservice wiki.
4. **Federated PageIndex Tree**:
   - Generates hierarchical tree nodes tagged with service names so cross-service chat queries can cite multiple repositories in one answer.
5. **Interactive UI (`components/ingestion-stepper.tsx` & `components/line-rail.tsx`)**:
   - Tab switcher for "Single Repo" vs "Microservice Mesh".
   - Dynamic repository list with add/remove rows and demo quick-fill button.
   - Transit LineRail sidebar badges federated systems and displays peer microservice jumping links.
