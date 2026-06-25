# Phase 0 — Scaffold & gates — report

**Status:** Done (2026-06-25)

## What was built

- `apps/api` — a `uv` project on **Python 3.14**, laid out as the hexagon:
  `src/frontdesk/{domain,application,infrastructure,interface,core}`.
- `core/settings.py` — the typed `Settings` (pydantic-settings), read from
  `FRONTDESK_*` env with local-dev defaults.
- Tooling wired in `pyproject.toml`: ruff (lint + format), mypy `--strict` (with the
  pydantic plugin), pytest + coverage (≥ 90% gate), and **import-linter** with three
  hexagonal contracts (domain pure; application depends only on domain; driven and
  driving adapters don't import each other).
- `deploy/docker/docker-compose.yml` — PostgreSQL 18 + Redis 8, with healthchecks and
  an explicit project name (`frontdesk`).
- `Makefile` — the single entry point (`make help`, `install`, `fmt`, `lint`,
  `typecheck`, `test`, `check`, `up`, `down`, `logs`).

## Verification (real runs, logged to `logs/phase-0/`)

- **The gate** (`make check`) — green:
  - ruff format + lint: clean.
  - import-linter: **3 contracts kept, 0 broken**.
  - mypy `--strict`: success, 9 source files, 0 issues.
  - pytest: 2 passed, **100 % coverage** (branch) — above the 90 % gate.
- **Infrastructure** (`make up`) — both services reach `healthy` in ~4 s;
  `pg_isready` reports "accepting connections", `redis-cli ping` returns `PONG`;
  `make down` tears down cleanly.

## Problems found and fixed (by running it for real)

1. **Compose project-name collision.** The default project name is the compose
   file's parent directory (`docker`), which collided with another repo's
   `deploy/docker/` and grabbed its orphan containers. Fixed by setting an explicit
   `name: frontdesk` in the compose file.
2. **PostgreSQL 18 data-dir convention.** `postgres:18` exits on start if the volume
   is mounted at `/var/lib/postgresql/data`; 18+ expects the mount at
   `/var/lib/postgresql` (data lives in a version subdirectory). Fixed the mount.

## Definition of Done

- [x] `make check` runs ruff + mypy + import-linter + pytest and passes on the
      skeleton.
- [x] Docker Compose brings up PostgreSQL and Redis (healthy + connectivity proven).
