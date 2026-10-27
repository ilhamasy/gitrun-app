# Phase 7 Specification: Microservices Network & Cross-Service Reasoning

**Status**: Planned  
**Focus**: Multi-service architecture synthesis, two-tier PageIndex (Tree-of-Trees) retrieval, and cross-service interchange transit mapping.

---

## 1. Objectives & Architectural Context

Department architectures are networks of microservices rather than isolated monoliths:
- Services communicate over **synchronous RPC** (gRPC / HTTP REST) and **asynchronous event brokers** (Kafka / RabbitMQ).
- Inquiries from engineers and new hires are frequently cross-cutting (*"What happens end-to-end when a customer submits checkout?"*, *"Which services consume payments.settled events?"*).
- Single-repo retrieval fails on cross-cutting questions because context is partitioned into independent repositories.

---

## 2. Ingestion & Storage Topology

```
content/
├── system_tree.json                     # Tier-1 Department Network Tree
├── payment-gateway/                     # Line 1 (Cedar)
│   ├── toc.json
│   ├── pageindex_tree.json              # Tier-2 Service Tree
│   ├── overview.md
│   ├── architecture.md
│   ├── setup.md
│   ├── api-reference.md
│   └── dependencies.md                  # Inbound/outbound RPC & event contracts
└── auth-sentinel/                       # Line 2 (Harbour)
    ├── toc.json
    ├── pageindex_tree.json              # Tier-2 Service Tree
    ├── overview.md
    ├── architecture.md
    ├── setup.md
    └── dependencies.md
```

### Ingestion Modes:
1. **Multi-Repo**: Each microservice repo is cloned, bundled with Repomix, and synthesized into `content/<service>/`.
2. **Monorepo**: A monorepo root (e.g. `services/*`) runs targeted Repomix passes per service directory, flattening output into `content/<service>/`.
3. **Network Builder**: Once individual services are documented, an automated pass scans all `dependencies.md` / `architecture.md` files to compile `content/system_tree.json`.

---

## 3. Two-Tier PageIndex Tree Search (Tree-of-Trees)

```
                         [ User Question ]
                                │
                                ▼
                   [ Tier 1: System Navigator ]
                   (Reads content/system_tree.json)
                                │
          ┌─────────────────────┴─────────────────────┐
          ▼                                           ▼
[ Service Tree: payment-gateway ]          [ Service Tree: auth-sentinel ]
  - distributed-idempotency-protocol         - asymmetric-key-rotation
  - database-schema-partitioning             - token-revocation-blocklist
          │                                           │
          └─────────────────────┬─────────────────────┘
                                ▼
                   [ Cross-Service Synthesis ]
                   (Cites nodes from both lines)
```

### Protocol Steps:
1. **System Navigation**:
   - Query input with optional `repo="system"` or global scope.
   - LLM analyzes query against `system_tree.json` (service summaries + interchange contracts).
   - Selects 1–3 target services that own the answer.
2. **Parallel Service Tree Search**:
   - Dispatches parallel PageIndex searches across selected service trees.
   - Collects 1–3 high-relevance node IDs per service.
3. **Cross-Service Synthesis**:
   - Extracts section markdown from each selected service.
   - Emits unified SSE stream quoting both services with clickable citations (`/wiki/payment-gateway/...` and `/wiki/auth-sentinel/...`).

---

## 4. UI: Transit Network & Interchange Stations

1. **System Network Map (`/network` or `/wiki`)**:
   - Render an interactive SVG transit map where each microservice is a colored transit line (Harbour, Cedar, Bramble, Amber, Violet).
   - Shared infrastructure (Kafka, Redis, API Gateways, Identity Providers) render as **Interchange Hub Stations**.
2. **Multi-Service Citation Display**:
   - Chat badges display line swatches alongside node codes:
     - `[Cedar · payment-gateway#distributed-idempotency-protocol]`
     - `[Harbour · auth-sentinel#security-boundaries]`
3. **Dependency Rail Tab**:
   - Wiki reader includes a dedicated "Interchanges" panel showing callers, downstreams, and event topics.
