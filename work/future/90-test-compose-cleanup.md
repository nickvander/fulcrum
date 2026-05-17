# 90: docker-compose.test.yml — usable for both pytest AND interactive serving

`docker-compose.test.yml` was written for one job (running pytest in a
fresh DB), but it's the only compose file currently configured to use
the `db-test` Postgres + the `pgvector/pgvector:pg15` image with the
vector extension. That means it's the most natural target for
interactive dev too — except for two papercuts that make the backend
crash the moment you try to use it without pytest's env shimming.

## What's wrong

1. **`MARKETPLACE_ENCRYPTION_KEY` is missing from the compose env.**
   `pytest.ini` injects it via the `env =` directive, so pytest works.
   But `uvicorn` (the container's actual CMD) reads from process env
   only, so it crashes at import time with:

   ```
   pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
   MARKETPLACE_ENCRYPTION_KEY
     Field required [type=missing, ...]
   ```

   Workaround used during the live UI walkthrough on 2026-05-17 was
   to `docker compose exec -e MARKETPLACE_ENCRYPTION_KEY=... backend
   bash -c "pkill uvicorn; uvicorn ..."` — ugly.

2. **`TESTING=1` is hard-set in the compose env.** That flag in
   `src/main.py` skips default-superuser creation, and in
   `src/core/ratelimit.py` disables slowapi. So:
   - Login fails because no admin user exists (the seeded one from
     `FIRST_SUPERUSER_*` env never gets created)
   - Rate limiting is silently off

   It belongs in `pytest.ini` (already there), not in the compose
   service env.

## Fix

Two-line patch to `docker-compose.test.yml` under the `backend`
service `environment:` block:

```yaml
- MARKETPLACE_ENCRYPTION_KEY=H35Vk1qaARMj/yX6EC0QrCYvmkWW/lgRdB7aQbsSivE=
# Remove this line:
# - TESTING=1
```

(Or, if anyone genuinely relies on TESTING=1 being set at compose
boot time, move it under an explicit `pytest` profile in the
compose file.)

After the patch, `docker compose -f docker-compose.test.yml up -d`
yields a backend that:
- Serves `localhost:${FULCRUM_TEST_BACKEND_PORT:-8201}` correctly
- Has a working `test@example.com` / `SecurePass123!` superuser
- Has rate limiting enabled
- Still runs `pytest tests/` correctly (the `env =` in `pytest.ini`
  sets `TESTING=1` only for the test process, which is the right
  scope)

## Bonus cleanup

The `redis` service in the same compose file pins host port `6379:6379`
which collides with the dev compose. The workaround is the override
in `/tmp/docker-compose.override.yml` (untracked) that drops the
port mapping. Either move redis behind `${FULCRUM_TEST_REDIS_PORT:-6379}:6379`
or drop the host port mapping entirely — inter-container traffic
doesn't need it.

## Why this matters

Without this fix, every dev who wants to click through the app against
a real backend has to either:
- Bring up the heavier dev `docker-compose.yml` (which has its own
  port conflicts when multiple worktrees are active), OR
- Patch the test compose at runtime like the May 17 session did

Both are friction at the worst possible time (when you're trying to
verify a fix in the browser). Fixing this unblocks the standard
`docker compose -f docker-compose.test.yml up -d` flow.
