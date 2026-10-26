# Setup & Configuration

Instructions for running `payment-gateway` locally or deploying within internal Kubernetes clusters.

## Prerequisites

- Go 1.23+ installed locally
- Docker and Docker Compose v2+
- `golang-migrate` CLI for database migrations
- GNU Make or compatible task runner

## Quickstart via Docker Compose

Spin up PostgreSQL 16, Redis 7, and mock PSP stubs:

```bash
# 1. Clone repository
git clone https://github.com/my-org/payment-gateway.git
cd payment-gateway

# 2. Boot dependencies
docker compose up -d postgres redis mock-psp

# 3. Apply schema migrations
make migrate-up

# 4. Run service locally with hot-reload
make dev
```

The HTTP server binds to `http://localhost:8080`, and gRPC server binds to `localhost:9090`.

## Environment Variables

| Variable | Required | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `SERVER_HTTP_PORT` | No | `8080` | Port for REST API server |
| `SERVER_GRPC_PORT` | No | `9090` | Port for internal gRPC listener |
| `DATABASE_URL` | Yes | - | PostgreSQL DSN with connection pool flags |
| `REDIS_URL` | Yes | - | Redis URI for locks and idempotency caches |
| `STRIPE_SECRET_KEY` | No | `sk_test_mock` | PSP API credentials |
| `LOG_LEVEL` | No | `info` | Logging verbosity (`debug`, `info`, `warn`, `error`) |

## Verification & Health Check

Confirm service readiness:

```bash
curl http://localhost:8080/healthz
# Response: {"status":"healthy","database":"up","redis":"up","timestamp":"2026-10-26T12:00:00Z"}
```
