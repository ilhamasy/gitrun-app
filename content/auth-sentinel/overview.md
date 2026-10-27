# Auth Sentinel System Overview

**Auth Sentinel** is our department's unified identity and authorization service. It issues and validates cryptographically signed JSON Web Tokens (JWT) for microservices and Single Page Applications.

## Supported Protocols

- **OAuth 2.0 Authorization Code Flow with PKCE**: RFC 7636 compliant authorization flow for web and mobile clients.
- **Client Credentials Grant**: RFC 6749 flow for machine-to-machine service communication.
- **OpenID Connect Core 1.0**: Standard claims (`sub`, `iss`, `aud`, `exp`, `email`, `roles`) and discovery endpoint at `/.well-known/openid-configuration`.

## Security Boundaries

All access tokens are minted as RS256 signed JWTs with a strict 15-minute lifetime. Refresh tokens are opaque 256-bit cryptographically secure random tokens stored in Redis with rotating replay detection.

## System Context & Peer Services

This repository operates as the centralized identity provider within the **[Checkout & Identity Mesh](/wiki/checkout-mesh/overview)**.

| Peer Microservice | Language | Role & Domain Boundary |
| :--- | :--- | :--- |
| [Payment Gateway Service](/wiki/payment-gateway/overview) | Go 1.23 | Validates RS256 JWT claims before executing financial debit operations. |

- **System Topology**: View full distributed interaction flows in the [Checkout & Identity Mesh Architecture](/wiki/checkout-mesh/architecture).
- **Local Multi-Service Orchestration**: Run this service alongside all peers via the unified [Checkout & Identity Mesh Setup](/wiki/checkout-mesh/setup).
