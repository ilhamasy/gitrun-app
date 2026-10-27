# Auth Sentinel Service API Reference

Specification of REST endpoints, data transfer objects, and error conventions for **Auth Sentinel Service**.

## Protocol Conventions

- **Content-Type**: `application/json`
- **Encoding**: UTF-8
- **Authentication**: Bearer tokens or API keys via `Authorization` header

## Endpoint Catalog

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service health probe |
| `GET` | `/api/v1/status` | Runtime status and operational metrics |
| `POST` | `/api/v1/execute` | Main business transaction pipeline |

## Error Codes

| Code | Status | Meaning |
| :--- | :--- | :--- |
| `400` | Bad Request | Schema validation failure or malformed body |
| `401` | Unauthorized | Missing or expired credentials |
| `404` | Not Found | Target resource does not exist |
| `500` | Internal Error | Unhandled service exception |
