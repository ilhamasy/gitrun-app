# Checkout & Identity Mesh System Orchestration & Setup

Instructions for provisioning, configuring, and launching the complete multi-service mesh locally.

## Prerequisites

- **Docker & Docker Compose**: v2.20+
- **Host Memory**: Minimum 8GB recommended to run all containerized services concurrently
- **Git**: Configured with access to all member repositories

## Unified Docker Compose Specification

Run all microservices together in an isolated bridge network:

```yaml
version: '3.8'

networks:
  checkout-mesh-mesh:
    driver: bridge

services:
  auth-sentinel:
    build:
      context: ../auth-sentinel
    container_name: auth-sentinel
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
      - ENV=development
      - SYSTEM_NAME=checkout-mesh
    networks:
      - checkout-mesh-mesh

  payment-gateway:
    build:
      context: ../payment-gateway
    container_name: payment-gateway
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
      - ENV=development
      - SYSTEM_NAME=checkout-mesh
    networks:
      - checkout-mesh-mesh

  redis:
    image: redis:7-alpine
    container_name: checkout-mesh-redis
    ports:
      - "6379:6379"
    networks:
      - checkout-mesh-mesh

  postgres:
    image: postgres:16-alpine
    container_name: checkout-mesh-postgres
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=checkout-mesh
    ports:
      - "5432:5432"
    networks:
      - checkout-mesh-mesh
```

## Quickstart Instructions

1. **Clone all member repositories side by side**:
   ```bash
   mkdir checkout-mesh && cd checkout-mesh
   git clone <url_to_auth-sentinel> && git clone <url_to_payment-gateway>
   ```

2. **Boot the complete microservice mesh**:
   ```bash
   docker compose -f docker-compose.yml up -d --build
   ```

3. **Verify cluster health**:
   ```bash
   curl -s http://localhost:8080/health && curl -s http://localhost:8080/health
   ```
