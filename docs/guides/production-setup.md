# Production Setup Guide

This document provides essential notes and recommendations for deploying Fulcrum
to a production environment.

## System-Level Configuration

### Redis: Memory Overcommit

When running the application with `docker compose up`, you may see the following
warning from Redis:

```
WARNING Memory overcommit must be enabled! Without it, a background save or replication may fail under low memory condition...
```

**Recommendation:** For production deployments, it is highly recommended to
enable memory overcommit on the host machine running the Docker containers. This
ensures Redis can function reliably, especially under high memory pressure.

To fix this, add `vm.overcommit_memory = 1` to `/etc/sysctl.conf` on the host
machine and then either reboot or run `sysctl vm.overcommit_memory=1`.

## Environment Variables

### Rate Limiting

To enable rate limiting, you must configure the following environment variables:

- `RATE_LIMIT_REDIS_URL`: The URL of the Redis instance used for rate limiting (e.g., `redis://redis:6379/0`). If not provided, it defaults to `REDIS_URL`.
- `RATE_LIMIT_DEFAULT`: The default rate limit for endpoints (default: `100/minute`).

### Security Headers

The application automatically adds the following security headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy: default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';`

Ensure your frontend application is compatible with these CSP settings.
