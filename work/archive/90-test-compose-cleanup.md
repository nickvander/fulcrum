# 90: docker-compose.test.yml — usable for both pytest AND interactive serving

> **STATUS: ✅ COMPLETE as of 2026-05-17.** Two-line patch to
> `docker-compose.test.yml`: dropped `TESTING=1` from the backend
> service env, added `MARKETPLACE_ENCRYPTION_KEY`. Plus the bonus
> redis-port-parameterization. Verified: container boots cleanly,
> seeded superuser logs in successfully, full pytest suite still
> passes (331/0/6).

## What landed

`docker-compose.test.yml`:

- **Removed `TESTING=1`** from the `backend` service `environment:`
  block. `conftest.py` sets `os.environ["TESTING"] = "True"` at
  import time, so pytest still gets the flag for its own scope (the
  `main.py` check is `!= "1"`, so `"True"` doesn't bypass superuser
  creation — but the pytest path doesn't need that bypass anyway).
  Removing it from compose means uvicorn at container boot DOES seed
  the default superuser and DOES enable slowapi rate limiting.
- **Added `MARKETPLACE_ENCRYPTION_KEY`** to the backend env. Pydantic
  Settings rejects this field as missing at import time, so without
  it the container would crash before uvicorn could bind.
- **Parameterized the redis host port** as
  `${FULCRUM_TEST_REDIS_PORT:-6379}:6379`, matching the existing
  `FULCRUM_TEST_DB_PORT` and `FULCRUM_TEST_BACKEND_PORT` patterns.
  Lets multiple worktrees coexist without 6379 collisions.
- **Cleaned up two duplicate-line typos** in the env block
  (`FIRST_SUPERUSER_PASSWORD` and `SECRET_KEY` were each listed twice).
- **Dropped the obsolete `version: '3.8'`** top-level key. Docker
  Compose v2 ignores it and warns about it on every command.
- **Inline comment** on the missing TESTING env explains why it's
  intentionally absent, so the next person doesn't put it back.

## How to verify

```bash
# Bring up the standard test compose (use overrides if any port collides)
FULCRUM_TEST_DB_PORT=5435 FULCRUM_TEST_REDIS_PORT=6381 FULCRUM_TEST_BACKEND_PORT=8201 \
  docker compose -f docker-compose.test.yml up -d

# Backend serves
curl http://localhost:8201/   # {"message":"Welcome to the Fulcrum API"}

# Seeded admin logs in
curl -X POST http://localhost:8201/api/v1/users/login/access-token \
  -d "username=test@example.com&password=SecurePass123!" \
  -H "Content-Type: application/x-www-form-urlencoded"
# {"access_token":"...","token_type":"bearer"}

# Pytest still works
docker compose -f docker-compose.test.yml exec backend python -m pytest tests/ -q
# 331 passed, 6 skipped, 2 warnings
```

No more `docker compose exec -e MARKETPLACE_ENCRYPTION_KEY=... bash -c
"pkill uvicorn; uvicorn..."` dance during interactive sessions.

## Why this matters

Before this fix, every dev who wanted to click through the app against
a real backend had to either bring up the heavier dev
`docker-compose.yml` (which has its own port conflicts when multiple
worktrees are active), OR patch the test compose at runtime. Both are
friction at the worst possible time (when you're trying to verify a
fix in the browser).

Live UI walkthrough on 2026-05-17 had to use a `/tmp/docker-compose.override.yml`
patch to get past these papercuts — that workaround is now obsolete.
