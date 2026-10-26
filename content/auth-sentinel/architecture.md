# Internal Architecture

## Asymmetric Key Rotation

Tokens are signed using RS256 private keys managed in Kubernetes secrets. Public keys are exported via standard JWKS (`/.well-known/jwks.json`) with automated `kid` rotation every 30 days.

## Token Revocation & Blocklist

While JWT access tokens are stateless, immediate revocation (e.g. on compromised credentials or password reset) is handled via a low-latency Redis bloom filter combined with a hot revocation set keyed by `sub` and `jti`.
