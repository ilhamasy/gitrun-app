# Internal Architecture

This document details the code organization, concurrency primitives, and data consistency models implemented inside `payment-gateway`.

## Directory Structure

```
cmd/
  server/            # Application bootstrap, CLI flags, graceful shutdown hooks
internal/
  adapter/           # External client integrations (Stripe, Adyen, BankRails)
  config/            # Strongly-typed environment configuration loader
  domain/            # Core business entities (Transaction, Account, FeeSchedule)
  handler/
    http/            # REST controllers, input DTO validation, HTTP response mappers
    grpc/            # Protobuf server implementations
  middleware/        # Auth verification, rate limiting, request tracing, CORS
  repository/        # PostgreSQL queries using pgx/v5 and sqlc generated code
  service/           # Business workflow orchestrators (PaymentService, LedgerService)
pkg/
  idempotency/       # Reusable Redis-backed distributed idempotency key manager
  money/             # Safe arbitrary-precision currency representation
```

## Concurrency and Worker Pools

High-volume webhook ingestion is decoupled from database transactions using a bounded worker pool:

```go
type WebhookWorkerPool struct {
    jobs       chan WebhookEvent
    maxWorkers int
    wg         sync.WaitGroup
}

func (p *WebhookWorkerPool) Start(ctx context.Context) {
    for i := 0; i < p.maxWorkers; i++ {
        p.wg.Add(1)
        go p.worker(ctx)
    }
}
```

- Inbound requests enqueue events into a non-blocking channel buffered to 5,000 items.
- Workers pull jobs and execute provider verification and signature matching concurrently.
- If queue depth reaches 90% threshold, HTTP 429 Backpressure responses are emitted to non-critical ingestion endpoints.

## Distributed Idempotency Protocol

Every write operation requires an `Idempotency-Key` header:

1. **Acquire Key**: `SET idempotency:<key> PENDING NX EX 120`. If key exists and status is `RESOLVED`, immediate return of cached payload.
2. **Execute Transaction**: Run debit/credit workflow against external PSP adapter.
3. **Persist State**: Commit database ledger rows inside SQL transaction.
4. **Update Key Status**: `SET idempotency:<key> COMPLETED:<payload> EX 86400`.
5. **Release On Error**: If network fault occurs before external confirmation, key is marked `FAILED` or unlocked for retry after backoff.

## Database Schema & Partitioning

The `ledger_entries` table is partitioned monthly by `created_at` timestamp:

```sql
CREATE TABLE ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL,
    amount_cents BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL,
    direction VARCHAR(6) CHECK (direction IN ('DEBIT', 'CREDIT')),
    reference_id VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);
```

All financial totals are stored as 64-bit integer cents to prevent floating point drift.
