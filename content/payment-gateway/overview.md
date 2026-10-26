# Payment Gateway Service Overview

The **Payment Gateway Service** acts as the centralized financial transaction processing router for our department's ecommerce and subscription products. It isolates upstream checkout domains from external Payment Service Providers (PSPs) including Stripe, Adyen, and regional bank rails.

## Core Capabilities

- **Idempotent Charge Pipeline**: Guaranteed exactly-once execution for debit and credit operations through Redis-backed distributed mutex locks and database uniqueness constraints.
- **Provider Multi-Tenancy**: Dynamic routing between PSP adapters based on currency, fee optimization tables, and real-time provider health probes.
- **Asynchronous Webhook Ingestion**: Ingests PSP webhook callbacks with cryptographically verified HMAC signatures, buffering events into Apache Kafka for replayability.
- **Immutable Financial Ledger**: Dual-entry accounting transaction entries written to PostgreSQL using strict serializable transaction isolation.

## Architecture Context

```
[ Checkout Frontend ] ──> [ API Gateway ] ──> [ Payment Gateway Service ]
                                                     │
                             ┌───────────────────────┼───────────────────────┐
                             ▼                       ▼                       ▼
                     [ Redis Mutex ]          [ PostgreSQL Ledger ]   [ Kafka Broker ]
                             │                       │                       │
                             └───────────────┬───────┴───────────────────────┘
                                             ▼
                                     [ Stripe / Adyen ]
```

## Tech Stack Summary

| Layer | Technology | Details |
| :--- | :--- | :--- |
| Runtime | Go 1.23 | Strict concurrency isolation via Goroutines & Worker Pools |
| API Layer | Gin + gRPC | Dual HTTP/REST and Protobuf RPC servers on separate ports |
| Primary Store | PostgreSQL 16 | Partitioned ledger ledger_entries table with pgx connection pool |
| State & Locks | Redis 7.2 | Redlock algorithm for distributed request deduplication |
| Messaging | Apache Kafka | Event topics: `payments.initiated`, `payments.settled`, `payments.failed` |
| Metrics | OpenTelemetry + Prometheus | Trace context propagation across upstream and downstream boundaries |

## Key Invariants

1. **Never double-bill**: Any request carrying an `Idempotency-Key` header returns identical cached responses if invoked within 24 hours.
2. **Deterministic PSP fallback**: If primary provider returns HTTP 5xx or times out past 3000ms, transaction gracefully degrades to secondary rail with zero duplicate authorization.
3. **Audit Log Trail**: All configuration changes and manual operator balance adjustments are persisted into an append-only audit table.
