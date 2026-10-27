"""
Multi-Repo Microservice Mesh Extractor & System Synthesizer.

Everything this module states about a system must be traceable to the ingested
repositories. It therefore does two things and nothing else:

1. `extract_service_metadata` reads a code bundle and records *evidence*:
   listening ports, route declarations, datastore drivers, message brokers,
   topic literals, environment variables, and header names.
2. `SystemSynthesizer` renders that evidence. Where a fact was not found, the
   page says so instead of filling the gap with a plausible-sounding stack.

There is deliberately no "make the demo graph look connected" fallback: an
ecosystem with no detected calls is documented as an ecosystem with no
detected calls.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.pageindex.llm import LLMClient

# Marker used across every rendered page where evidence is absent.
UNKNOWN = "not detected"


@dataclass
class ServiceNodeInfo:
    """Facts about one repository, as observed in its code bundle."""

    repo_name: str
    display_name: str
    description: str
    language: str
    port: Optional[int] = None
    exposed_endpoints: List[str] = field(default_factory=list)
    consumed_services: List[str] = field(default_factory=list)
    published_topics: List[str] = field(default_factory=list)
    subscribed_topics: List[str] = field(default_factory=list)
    datastores: List[str] = field(default_factory=list)

    # Additional observed evidence, appended by `extract_service_metadata`.
    brokers: List[str] = field(default_factory=list)
    declared_topics: List[str] = field(default_factory=list)
    env_vars: List[str] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)
    observability: List[str] = field(default_factory=list)

    @property
    def port_label(self) -> str:
        return f":{self.port}" if self.port else UNKNOWN

    @property
    def hosts_label(self) -> str:
        return ", ".join(self.datastores) if self.datastores else UNKNOWN

    @property
    def routes_label(self) -> str:
        if not self.exposed_endpoints:
            return UNKNOWN
        return ", ".join(f"`{e}`" for e in self.exposed_endpoints[:4])


# ---------------------------------------------------------------------------
# Evidence extraction
# ---------------------------------------------------------------------------

# `PORT=8080`, `port: 8081`, `listen(8082)`, `EXPOSE 8083`, `:8084`.
_PORT_PATTERNS = (
    re.compile(r"\bPORT\b\s*[:=]\s*[\"']?(\d{2,5})"),
    re.compile(r"\.listen\s*\(\s*(?:process\.env\.PORT\s*\|\|\s*)?[\"']?(\d{2,5})"),
    re.compile(r"\bEXPOSE\s+(\d{2,5})"),
    re.compile(r"(?:address|addr|host)\s*[:=]\s*[\"'][^\"':]*:(\d{2,5})"),
)

# Route declarations across the common frameworks.
_ROUTE_PATTERNS = (
    re.compile(r"\b(?:GET|POST|PUT|DELETE|PATCH)\s+(/[A-Za-z0-9_\-./{}:]+)"),
    re.compile(r"""\.(?:get|post|put|delete|patch|all)\s*\(\s*["'`](/[^"'`\s]*)["'`]"""),
    re.compile(r"""@(?:Get|Post|Put|Delete|Patch)Mapping\s*\(\s*["']([^"']+)["']"""),
    re.compile(r"""HandleFunc\s*\(\s*["'](/[^"']*)["']"""),
    re.compile(r"""@(?:app|router)\.(?:get|post|put|delete|patch)\s*\(\s*["'](/[^"']*)["']"""),
    re.compile(r"""Handle\s*\(\s*["'](?:GET|POST|PUT|DELETE)\s+(/[^"']*)["']"""),
)

# Driver / dependency markers per datastore.
_DATASTORE_SIGNATURES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("PostgreSQL", ("postgres", "postgresql", "pgx", "psycopg", "psql", "pg_")),
    ("MySQL", ("mysql", "mariadb")),
    ("MongoDB", ("mongodb", "mongoose", "pymongo")),
    ("Redis", ("redis", "redlock", "ioredis")),
    ("SQLite", ("sqlite",)),
    ("DynamoDB", ("dynamodb",)),
)

_BROKER_SIGNATURES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Apache Kafka", ("kafka", "kafkajs", "confluent")),
    ("RabbitMQ", ("rabbitmq", "amqplib", "amqp")),
    ("NATS", ("nats.io", "nats", "stan.")),
    ("AWS SQS/SNS", ("sqs", "sns", "aws-sdk/client-sqs")),
    ("Google Pub/Sub", ("pubsub", "@google-cloud/pubsub")),
    ("MQTT", ("mqtt", "paho")),
)

_OBSERVABILITY_SIGNATURES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("OpenTelemetry", ("opentelemetry", "otel")),
    ("Prometheus", ("prometheus",)),
    ("Jaeger", ("jaeger",)),
    ("Zipkin", ("zipkin",)),
    ("Sentry", ("sentry",)),
    ("Datadog", ("datadog", "dd-trace")),
)

_HEADER_SIGNATURES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Authorization", ("authorization",)),
    ("Idempotency-Key", ("idempotency-key", "idempotency_key", "idempotencykey")),
    ("X-Correlation-ID", ("x-correlation-id",)),
    ("X-Request-ID", ("x-request-id",)),
    ("traceparent", ("traceparent",)),
    ("Content-Type", ("content-type",)),
)

# A topic literal: dotted lowercase identifier, 2-4 segments.
_TOPIC_RE = re.compile(r"""["'`]([a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+){1,3})["'`]""")

_TOPIC_NOISE_SEGMENTS = {
    "json", "js", "ts", "tsx", "jsx", "mjs", "cjs", "py", "go", "rs", "java",
    "rb", "php", "html", "css", "yml", "yaml", "toml", "ini", "cfg", "env",
    "map", "lock", "min", "test", "spec", "config", "txt", "sh", "sql",
    "com", "org", "net", "io", "dev", "local", "example",
}

# A literal that names a file (`main.py`, `app.test.js`) is not a topic.
_FILE_LIKE = re.compile(
    r"\.(?:py|go|rs|java|rb|php|js|jsx|ts|tsx|mjs|cjs|json|ya?ml|toml|ini|cfg|"
    r"env|txt|sh|sql|html|css|md|lock|map|min|test|spec)$",
    re.IGNORECASE,
)

_PUBLISH_CONTEXT = ("publish", "produce", ".send(", "emit", "dispatch", "writer")
_SUBSCRIBE_CONTEXT = ("subscribe", "consume", "receive", "listen", "reader", "handler")


def _detect_port(bundle_text: str) -> Optional[int]:
    for pattern in _PORT_PATTERNS:
        match = pattern.search(bundle_text)
        if not match:
            continue
        try:
            port = int(match.group(1))
        except (TypeError, ValueError):
            continue
        if 1024 <= port <= 65535:
            return port
    return None


def _detect_routes(bundle_text: str) -> List[str]:
    endpoints: List[str] = []
    for pattern in _ROUTE_PATTERNS:
        for match in pattern.finditer(bundle_text):
            route = match.group(1).strip()
            if not route.startswith("/") or len(route) < 2:
                continue
            if route in endpoints:
                continue
            endpoints.append(route)
    return endpoints[:12]


def _detect_keywords(
    bundle_lower: str,
    signatures: Tuple[Tuple[str, Tuple[str, ...]], ...],
) -> List[str]:
    return [name for name, markers in signatures if any(m in bundle_lower for m in markers)]


def _detect_env_vars(bundle_text: str) -> List[str]:
    found: List[str] = []
    patterns = (
        re.compile(r"process\.env\.([A-Z][A-Z0-9_]+)"),
        re.compile(r"os\.environ(?:\.get)?\s*[\[(]\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
        re.compile(r"os\.(?:Getenv|LookupEnv)\s*\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
        re.compile(r"getenv\s*\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
        re.compile(r"(?:getenv|require_env|env)\s*\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
        re.compile(r"ENV\s+([A-Z][A-Z0-9_]+)"),
    )
    for pattern in patterns:
        for match in pattern.finditer(bundle_text):
            name = match.group(1)
            if name not in found:
                found.append(name)
    return found[:20]


def _detect_topics(bundle_text: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Returns (declared, published, subscribed).

    A dotted string literal is only treated as a topic when it looks like one;
    direction is assigned solely from an adjacent publish/subscribe call.
    """
    declared: List[str] = []
    published: List[str] = []
    subscribed: List[str] = []

    for match in _TOPIC_RE.finditer(bundle_text):
        topic = match.group(1)
        segments = topic.split(".")
        if len(segments) < 2 or len(topic) < 5:
            continue
        if _FILE_LIKE.search(topic):
            continue
        if any(seg in _TOPIC_NOISE_SEGMENTS for seg in segments):
            continue
        if topic in declared:
            continue

        declared.append(topic)
        context = bundle_text[max(0, match.start() - 160) : match.start()].lower()
        if any(marker in context for marker in _PUBLISH_CONTEXT):
            published.append(topic)
        elif any(marker in context for marker in _SUBSCRIBE_CONTEXT):
            subscribed.append(topic)

    return declared[:12], published[:8], subscribed[:8]


def extract_service_metadata(
    repo_name: str,
    bundle_text: str,
    toc: Dict[str, Any],
) -> ServiceNodeInfo:
    """Read ports, routes, stores, brokers, topics and headers out of a bundle."""
    display_name = toc.get("display_name", repo_name.replace("-", " ").title())
    description = toc.get("description", f"Repository `{repo_name}`.")
    language = toc.get("language", "Generic")

    bundle_lower = bundle_text.lower()
    declared, published, subscribed = _detect_topics(bundle_text)

    return ServiceNodeInfo(
        repo_name=repo_name,
        display_name=display_name,
        description=description,
        language=language,
        port=_detect_port(bundle_text),
        exposed_endpoints=_detect_routes(bundle_text),
        consumed_services=[],
        published_topics=published,
        subscribed_topics=subscribed,
        datastores=_detect_keywords(bundle_lower, _DATASTORE_SIGNATURES),
        brokers=_detect_keywords(bundle_lower, _BROKER_SIGNATURES),
        declared_topics=declared,
        env_vars=_detect_env_vars(bundle_text),
        headers=_detect_keywords(bundle_lower, _HEADER_SIGNATURES),
        observability=_detect_keywords(bundle_lower, _OBSERVABILITY_SIGNATURES),
    )


# ---------------------------------------------------------------------------
# Cross-repository relationship detection
# ---------------------------------------------------------------------------

class CrossRepoMeshExtractor:
    """Finds inter-service references that actually appear in the code."""

    def _reference_evidence(
        self,
        src: ServiceNodeInfo,
        target: ServiceNodeInfo,
        src_bundle: str,
        src_lower: str,
    ) -> Optional[str]:
        """Return a human-readable reason if `src` demonstrably touches `target`."""
        # 1. The target's repository name appears in the source.
        for needle in {
            target.repo_name.lower(),
            target.repo_name.lower().replace("-", "_"),
            target.repo_name.lower().replace("_", "-"),
        }:
            if needle and needle in src_lower:
                return f"`{target.repo_name}` is referenced in source"

        # 2. The target's listening port appears in a URL/host position.
        if target.port:
            port_pattern = re.compile(
                rf"(?:https?://[^\s\"'`]*|[\w.-]+):{target.port}\b"
            )
            port_match = port_pattern.search(src_bundle)
            if port_match:
                return f"host reference `{port_match.group(0)}` matches {target.port_label}"

        # 3. An environment variable names the target (e.g. AUTH_SERVICE_URL).
        token = re.sub(r"[^a-z0-9]", "", target.repo_name.lower())
        for var in src.env_vars:
            normalized = re.sub(r"[^a-z0-9]", "", var.lower())
            if token and token in normalized and any(
                suffix in var.upper() for suffix in ("_URL", "_HOST", "_ADDR", "_ENDPOINT")
            ):
                return f"environment variable `{var}` points at this service"

        return None

    def build_mesh(
        self,
        services: List[ServiceNodeInfo],
        bundle_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Identify cross-service dependencies backed by observable evidence."""
        interactions: List[Dict[str, Any]] = []

        for src in services:
            src_bundle = bundle_map.get(src.repo_name, "")
            src_lower = src_bundle.lower()

            for target in services:
                if src.repo_name == target.repo_name:
                    continue

                evidence = self._reference_evidence(src, target, src_bundle, src_lower)
                if evidence:
                    protocol = "gRPC" if "grpc" in src_lower else "HTTP / REST"
                    interactions.append({
                        "source": src.repo_name,
                        "source_display": src.display_name,
                        "target": target.repo_name,
                        "target_display": target.display_name,
                        "type": "Synchronous RPC",
                        "protocol": protocol,
                        "purpose": f"Call site detected — {evidence}",
                        "evidence": evidence,
                    })

                for pub in src.published_topics:
                    for sub in target.subscribed_topics:
                        if pub == sub:
                            interactions.append({
                                "source": src.repo_name,
                                "source_display": src.display_name,
                                "target": target.repo_name,
                                "target_display": target.display_name,
                                "type": "Asynchronous Event",
                                "protocol": f"Topic: `{pub}`",
                                "purpose": f"Topic `{pub}` is published here and consumed there",
                                "evidence": f"shared topic `{pub}`",
                            })

        return interactions


# ---------------------------------------------------------------------------
# Federated wiki synthesis
# ---------------------------------------------------------------------------

class SystemSynthesizer:
    """Renders a federated wiki from extracted evidence only."""

    def __init__(self, content_dir: str | Path, llm_client: Optional[LLMClient] = None):
        self.content_dir = Path(content_dir).resolve()
        self.llm = llm_client or LLMClient()
        self.mesh_extractor = CrossRepoMeshExtractor()

    def generate_system_wiki(
        self,
        system_name: str,
        display_name: str,
        services: List[ServiceNodeInfo],
        bundle_map: Dict[str, str],
        interactions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Writes the federated TOC and four cross-service pages."""
        system_dir = self.content_dir / system_name
        system_dir.mkdir(parents=True, exist_ok=True)

        if interactions is None:
            interactions = self.mesh_extractor.build_mesh(services, bundle_map)

        toc = {
            "repo_name": system_name,
            "display_name": display_name,
            "description": (
                f"Federated documentation for {len(services)} ingested repositories: "
                + ", ".join(s.repo_name for s in services)
                + "."
            ),
            "language": "Polyglot Mesh",
            "is_system": True,
            "member_repos": [s.repo_name for s in services],
            "pages": [
                {
                    "slug": "overview",
                    "title": "System Topology & Overview",
                    "description": "Member inventory and interaction graph derived from repository evidence.",
                },
                {
                    "slug": "architecture",
                    "title": "Distributed Interaction & Sagas",
                    "description": "Observed call sites, message topics, and communication contracts.",
                },
                {
                    "slug": "setup",
                    "title": "Unified Orchestration & Setup",
                    "description": "Compose topology limited to detected runtimes and backing services.",
                },
                {
                    "slug": "api-reference",
                    "title": "Ingress Routing & Gateway Catalog",
                    "description": "Routes and headers declared in the member repositories.",
                },
            ],
        }

        (system_dir / "toc.json").write_text(json.dumps(toc, indent=2), encoding="utf-8")

        pages = {
            "overview": self._render_system_overview(system_name, display_name, services, interactions),
            "architecture": self._render_system_architecture(display_name, services, interactions),
            "setup": self._render_system_setup(system_name, display_name, services),
            "api-reference": self._render_system_api_reference(display_name, services),
        }
        for slug, markdown in pages.items():
            (system_dir / f"{slug}.md").write_text(markdown, encoding="utf-8")

        return toc

    def inject_system_context_into_member_repos(
        self,
        system_name: str,
        system_display: str,
        services: List[ServiceNodeInfo],
        interactions: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Adds a peer-services section to each member's own wiki."""
        for current_svc in services:
            repo_dir = self.content_dir / current_svc.repo_name
            if not repo_dir.exists():
                continue

            peer_services = [s for s in services if s.repo_name != current_svc.repo_name]

            member_toc_file = repo_dir / "toc.json"
            if member_toc_file.exists():
                try:
                    data = json.loads(member_toc_file.read_text(encoding="utf-8"))
                    data["system"] = {
                        "system_name": system_name,
                        "display_name": system_display,
                        "peer_services": [
                            {
                                "repo_name": p.repo_name,
                                "display_name": p.display_name,
                                "role": p.description,
                            }
                            for p in peer_services
                        ],
                    }
                    member_toc_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                except Exception:
                    pass

            overview_path = repo_dir / "overview.md"
            if not overview_path.exists():
                continue

            text = overview_path.read_text(encoding="utf-8")
            if "## System Context & Peer Services" in text:
                continue

            peer_table_rows = "\n".join(
                f"| [{p.display_name}](/wiki/{p.repo_name}/overview) | `{p.language}` | `{p.port_label}` | {p.description} |"
                for p in peer_services
            )

            observed_links = [
                i
                for i in (interactions or [])
                if current_svc.repo_name in (i["source"], i["target"])
            ]
            if observed_links:
                link_lines = "\n".join(
                    f"- {i['type']}: [{i['source_display']}](/wiki/{i['source']}/overview) → "
                    f"[{i['target_display']}](/wiki/{i['target']}/overview) — {i['evidence']}"
                    for i in observed_links
                )
            else:
                link_lines = (
                    "- No direct call site or shared message topic was detected between this "
                    "service and its peers during ingestion."
                )

            injection = f"""

## System Context & Peer Services

This repository was ingested as a member of **[{system_display}](/wiki/{system_name}/overview)**.

| Peer Microservice | Language | Port | Description |
| :--- | :--- | :--- | :--- |
{peer_table_rows}

### Observed Links

{link_lines}

- **System Topology**: [{system_display} Overview](/wiki/{system_name}/overview)
- **Local Multi-Service Orchestration**: [{system_display} Setup](/wiki/{system_name}/setup)
"""
            overview_path.write_text(text + injection, encoding="utf-8")

    # -- shared helpers ----------------------------------------------------

    @staticmethod
    def _interaction_summary(interactions: List[Dict[str, Any]]) -> str:
        if not interactions:
            return (
                "No cross-repository call sites, shared message topics, or service "
                "references were detected between these repositories during ingestion. "
                "The repositories are documented together here, but nothing in the code "
                "shows them communicating."
            )
        sync = sum(1 for i in interactions if i["type"] == "Synchronous RPC")
        async_ = len(interactions) - sync
        return (
            f"{len(interactions)} inter-service reference(s) were detected: "
            f"{sync} synchronous call site(s) and {async_} shared message topic(s). "
            "Each is listed below with the evidence that produced it."
        )

    @staticmethod
    def _backend_services(services: List[ServiceNodeInfo]) -> Dict[str, str]:
        """Map detected backing service -> compose image, for setup rendering."""
        detected: Dict[str, str] = {}
        images = {
            "PostgreSQL": "postgres:16-alpine",
            "MySQL": "mysql:8",
            "MongoDB": "mongo:7",
            "Redis": "redis:7-alpine",
            "Apache Kafka": "bitnami/kafka:3.7",
            "RabbitMQ": "rabbitmq:3-management-alpine",
            "NATS": "nats:2-alpine",
        }
        for service in services:
            for store in list(service.datastores) + list(service.brokers):
                if store in images and store not in detected:
                    detected[store] = images[store]
        return detected

    # -- page renderers ----------------------------------------------------

    def _render_system_overview(
        self,
        system_name: str,
        display_name: str,
        services: List[ServiceNodeInfo],
        interactions: List[Dict[str, Any]],
    ) -> str:
        svc_rows = "\n".join(
            f"| [{s.display_name}](/wiki/{s.repo_name}/overview) | `{s.repo_name}` | "
            f"`{s.language}` | `{s.port_label}` | {s.hosts_label} | {s.routes_label} |"
            for s in services
        )

        mermaid_lines = ["graph TD"]
        for s in services:
            node_id = s.repo_name.replace("-", "_").replace(".", "_")
            mermaid_lines.append(
                f'  {node_id}["{s.display_name}<br/><i>{s.port_label} · {s.language}</i>"]'
            )
        drawn: set = set()
        for inter in interactions:
            s_id = inter["source"].replace("-", "_").replace(".", "_")
            t_id = inter["target"].replace("-", "_").replace(".", "_")
            key = (s_id, t_id, inter["protocol"])
            if key in drawn:
                continue
            drawn.add(key)
            arrow = "-.->|async|" if inter["type"] == "Asynchronous Event" else f"-->|{inter['protocol']}|"
            mermaid_lines.append(f"  {s_id} {arrow} {t_id}")

        return f"""# {display_name} Overview

**{display_name}** federates {len(services)} ingested repositories:
{chr(10).join(f"- [{s.display_name}](/wiki/{s.repo_name}/overview) (`{s.repo_name}`)" for s in services)}

Every statement on these pages comes from those repositories. Fields shown as
`{UNKNOWN}` were searched for and not found.

## Microservice Inventory

| Microservice | Repository | Language | Port | Datastores | Declared Routes |
| :--- | :--- | :--- | :--- | :--- | :--- |
{svc_rows}

## Detected Interaction Graph

```mermaid
{chr(10).join(mermaid_lines)}
```

## What the Repositories Show

{self._interaction_summary(interactions)}

## Documentation Scope

- Only relationships with an observable reference (a repo name, a host:port, a
  service URL variable, or a shared topic) are drawn as edges.
- Absence of an edge means no such reference was found — not that the services
  are necessarily independent.
"""

    def _render_system_architecture(
        self,
        display_name: str,
        services: List[ServiceNodeInfo],
        interactions: List[Dict[str, Any]],
    ) -> str:
        if interactions:
            inter_table = "\n".join(
                f"| [{i['source_display']}](/wiki/{i['source']}/overview) | "
                f"[{i['target_display']}](/wiki/{i['target']}/overview) | `{i['type']}` | "
                f"{i['protocol']} | {i['evidence']} |"
                for i in interactions
            )
            communication_section = f"""## Inter-Service Communication

| Source Service | Target Service | Interaction Type | Protocol | Evidence |
| :--- | :--- | :--- | :--- | :--- |
{inter_table}"""
        else:
            communication_section = """## Inter-Service Communication

No inter-service communication was detected between the ingested repositories.
No call sites, no shared topics, and no environment variables pointing at a
peer were found."""

        topic_rows: List[str] = []
        for s in services:
            for topic in s.declared_topics:
                if topic in s.published_topics:
                    direction = "published"
                elif topic in s.subscribed_topics:
                    direction = "subscribed"
                else:
                    direction = "declared (direction not determined)"
                topic_rows.append(f"| `{topic}` | [{s.display_name}](/wiki/{s.repo_name}/overview) | {direction} |")

        brokers = sorted({b for s in services for b in s.brokers})
        if topic_rows:
            if brokers:
                broker_note = f"Broker libraries detected: {', '.join(brokers)}."
            else:
                broker_note = (
                    "Topic strings were found, but no broker client library was "
                    "detected, so the transport is undocumented."
                )
            messaging_section = f"""## Messaging

{broker_note}

| Topic | Repository | Role |
| :--- | :--- | :--- |
{chr(10).join(topic_rows)}"""
        else:
            messaging_section = """## Messaging

No message broker library and no topic literal were detected in the ingested
repositories, so no messaging topology is documented."""

        sequence = ""
        if interactions:
            participant_ids = []
            for inter in interactions:
                for repo in (inter["source"], inter["target"]):
                    if repo not in participant_ids:
                        participant_ids.append(repo)
            names = {s.repo_name: s.display_name for s in services}
            lines = ["```mermaid", "sequenceDiagram", "  autonumber"]
            for idx, repo in enumerate(participant_ids, start=1):
                lines.append(f"  participant S{idx} as {names.get(repo, repo)}")
            index = {repo: f"S{idx}" for idx, repo in enumerate(participant_ids, start=1)}
            for inter in interactions:
                label = "event" if inter["type"] == "Asynchronous Event" else inter["protocol"]
                lines.append(
                    f"  {index[inter['source']]}->>{index[inter['target']]}: {label}"
                )
            lines.append("```")
            sequence = "\n".join(lines)
        else:
            sequence = "_No interaction sequence can be drawn: no edges were detected._"

        return f"""# {display_name} Distributed Architecture

This page documents only the communication that could be read out of the
ingested repositories.

{communication_section}

## Observed Interaction Sequence

{sequence}

{messaging_section}

## Consistency Notes

- Consistency guarantees are documented per service in that service's own wiki,
  where the storage layer is visible.
- No saga, ledger, or distributed-transaction mechanism is described here
  because none was detected across repositories.
"""

    def _render_system_setup(
        self,
        system_name: str,
        display_name: str,
        services: List[ServiceNodeInfo],
    ) -> str:
        compose_services = []
        for s in services:
            ports_block = (
                f"""    ports:
      - "{s.port}:{s.port}"
"""
                if s.port
                else "    # No listening port was detected in this repository.\n"
            )
            compose_services.append(f"""  {s.repo_name}:
    build:
      context: ../{s.repo_name}
    container_name: {s.repo_name}
{ports_block}    environment:
      - ENV=development""")

        compose_yaml = "\n\n".join(compose_services)

        backing = self._backend_services(services)
        backing_blocks = []
        for name, image in backing.items():
            block = f"""  {name.split()[0].lower()}:
    image: {image}
    container_name: {system_name}-{name.split()[0].lower()}"""
            default_port = {
                "PostgreSQL": "5432:5432",
                "MySQL": "3306:3306",
                "MongoDB": "27017:27017",
                "Redis": "6379:6379",
                "Apache Kafka": "9092:9092",
                "RabbitMQ": "5672:5672",
                "NATS": "4222:4222",
            }.get(name)
            if default_port:
                block += f'\n    ports:\n      - "{default_port}"'
            backing_blocks.append(block)

        if backing_blocks:
            backing_section = (
                "\n\n  # Detected backing services\n" + "\n\n".join(backing_blocks)
            )
            backing_note = (
                "Backing services are included only where a matching driver or "
                "broker library was found: " + ", ".join(backing) + "."
            )
        else:
            backing_section = ""
            backing_note = (
                "No datastore driver or message broker library was detected in any "
                "member repository, so no backing services are declared."
            )

        health_lines = []
        for s in services:
            if s.port and "/health" in s.exposed_endpoints:
                health_lines.append(f"curl -s http://localhost:{s.port}/health")
        if health_lines:
            health_cmd = "\n".join(health_lines)
        else:
            health_cmd = "# No /health route was detected; check each service's own wiki."

        port_known = [s for s in services if s.port]
        port_note = (
            "Ports shown above were read from the repositories."
            if port_known
            else "No member repository declared a listening port."
        )

        return f"""# {display_name} System Orchestration & Setup

Local orchestration for the repositories ingested into this system.

## Prerequisites

- **Docker & Docker Compose**: v2.20+
- **Git**: configured with access to all member repositories

## Unified Docker Compose Specification

{backing_note}

```yaml
networks:
  {system_name}-mesh:
    driver: bridge

services:
{compose_yaml}{backing_section}
```

## Quickstart

1. **Clone all member repositories side by side**:
   ```bash
   mkdir {system_name} && cd {system_name}
   {" && ".join(f"git clone <url_to_{s.repo_name}>" for s in services)}
   ```

2. **Start the mesh**:
   ```bash
   docker compose up -d --build
   ```

3. **Check service reachability**:
   ```bash
   {health_cmd}
   ```

{port_note}
"""

    def _render_system_api_reference(
        self,
        display_name: str,
        services: List[ServiceNodeInfo],
    ) -> str:
        route_rows = []
        for s in services:
            for endpoint in s.exposed_endpoints:
                upstream = (
                    f"`http://{s.repo_name}:{s.port}{endpoint}`"
                    if s.port
                    else f"`{endpoint}` (host {UNKNOWN})"
                )
                route_rows.append(
                    f"| [{s.display_name}](/wiki/{s.repo_name}/overview) | `{endpoint}` | {upstream} |"
                )

        if route_rows:
            routing_section = f"""## Declared Routes

Routes below are declarations found in the member repositories. No ingress
mapping is inferred: the table describes what each service exposes, not what a
gateway forwards.

| Microservice | Declared Route | Service Upstream |
| :--- | :--- | :--- |
{chr(10).join(route_rows)}"""
        else:
            routing_section = """## Declared Routes

No route declarations were detected in the ingested repositories."""

        header_rows = []
        for s in services:
            for header in s.headers:
                header_rows.append(
                    f"| `{header}` | [{s.display_name}](/wiki/{s.repo_name}/overview) |"
                )
        if header_rows:
            header_section = f"""## Detected Header Names

| Header | Observed In |
| :--- | :--- |
{chr(10).join(sorted(set(header_rows)))}"""
        else:
            header_section = """## Detected Header Names

No shared header contract was detected in the ingested repositories."""

        observability = sorted({o for s in services for o in s.observability})
        observability_section = (
            f"## Observability\n\nInstrumentation detected: {', '.join(observability)}."
            if observability
            else "## Observability\n\nNo instrumentation library was detected."
        )

        return f"""# {display_name} Ingress Routing & Gateway Catalog

Routing and header facts collected from the member repositories.

{routing_section}

{header_section}

{observability_section}

## Error Conventions

No cross-service error contract was detected. Each service documents its own
error handling in its individual wiki.
"""
