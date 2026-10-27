# Checkout & Identity Mesh Ingress Routing & Gateway Catalog

Global Edge Ingress routing specification, header propagation standards, and cross-service error conventions for **Checkout & Identity Mesh**.

## Global Ingress Route Mapping

Public clients communicate exclusively with the Edge Gateway. The gateway forwards requests to target microservices based on prefix paths:

| Public Gateway Route | Target Microservice | Internal Upstream URL | Description |
| :--- | :--- | :--- | :--- |
| `/api/auth-sentinel/health` | [Auth Sentinel Service](/wiki/auth-sentinel/overview) | `http://auth-sentinel:8080/health` | Direct service route |
| `/api/auth-sentinel/api/v1/auth-sentinel` | [Auth Sentinel Service](/wiki/auth-sentinel/overview) | `http://auth-sentinel:8080/api/v1/auth-sentinel` | Direct service route |
| `/api/payment-gateway/api/v1/payments` | [Payment Gateway Service](/wiki/payment-gateway/overview) | `http://payment-gateway:8080/api/v1/payments` | Direct service route |
| `/api/payment-gateway/api/v1/payments/{payment_id}/refunds` | [Payment Gateway Service](/wiki/payment-gateway/overview) | `http://payment-gateway:8080/api/v1/payments/{payment_id}/refunds` | Direct service route |
| `/api/payment-gateway/api/v1/payments/{paymentid}/refunds` | [Payment Gateway Service](/wiki/payment-gateway/overview) | `http://payment-gateway:8080/api/v1/payments/{paymentid}/refunds` | Direct service route |

## Distributed Header Propagation Standard

Every internal HTTP and gRPC request between microservices MUST forward these headers:

| Header Name | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `Authorization` | Bearer Token | RS256 JWT | Issued exclusively by [Auth Sentinel](/wiki/auth-sentinel/overview) |
| `Idempotency-Key` | UUIDv4 | Unique per mutation | Enforced by [Payment Gateway](/wiki/payment-gateway/overview) |
| `X-Correlation-ID` | UUIDv4 | Unchanged across hops | Injected at gateway, propagated across all RPCs and Kafka headers |
| `X-Client-Timestamp` | ISO 8601 | Client UTC time | Used for clock skew and replay protection |

## System Error Standards

| Status Code | Code String | Meaning |
| :--- | :--- | :--- |
| `400` | `INVALID_SCHEMA` | Malformed body or schema violation |
| `401` | `AUTH_TOKEN_EXPIRED` | Expired or invalid cryptographic signature |
| `409` | `IDEMPOTENCY_CONFLICT` | Concurrent request in progress for key |
| `502` | `PEER_SERVICE_UNAVAILABLE` | Downstream microservice circuit breaker tripped |
| `504` | `GATEWAY_TIMEOUT` | Internal RPC call exceeded 3000ms SLA |
