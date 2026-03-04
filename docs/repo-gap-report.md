# Repository Gap Report

Date: 2026-03-04
Scope: current tracked files in this checkout. `.codex` is excluded from solution scope.

## Current tree reality

- `prometheus-api/` contains FastAPI app source, `.env.example`, `.env.test`, `requirements.txt`, and `schema.sql`.
- Backend reproducibility scaffolding had been removed from current checkout (`pytest.ini`, `requirements-dev.txt`, tests, Docker artifacts), then partially rebuilt in this refactor.
- `prometheus-app/` contains Expo app source and package manifests, but test/lint scaffolding had been removed from current checkout and needed reconstruction.
- `scripts/perf-smoke.sh` was missing and required replacement.

## Git-history-derived missing foundations affecting reproducibility

- Backend test scaffolding historically existed (`pytest.ini`, tests, dev requirements) but was absent in current tree.
- Frontend Jest scaffolding (`jest.config.js`, `__tests__/setup.ts`, API/offline tests) existed historically but was absent.
- Versioned migrations were absent; only monolithic `schema.sql` remained.

## README vs actual files mismatch

- README content was encoding-corrupted and did not match real files/scripts.
- README referenced old stack assumptions and lacked migration/auth/idempotency instructions.

## Stale/orphan leftovers

- Deployment path files were intentionally removed from current checkout; docs must no longer claim Docker/Cloud Run as active unless restored.
- Legacy `APP_TOKEN` model was still treated as core auth in backend/frontend.

## Ranked issues and resolution type

### P0

1. Shared client token as primary auth boundary (`APP_TOKEN`).
- Action: REPLACE

2. No durable DB-backed idempotency for mutation replay.
- Action: REPLACE

3. No versioned migration strategy.
- Action: RESTORE

4. AI/backup silent-success behavior.
- Action: REPLACE

5. Broken README/repro instructions.
- Action: REPLACE

### P1

1. Hardcoded production API URL default in frontend.
- Action: REPLACE

2. Missing frontend test/lint/typecheck entrypoints.
- Action: RESTORE

3. Data correctness gap for inventory uniqueness on normalized names.
- Action: REPLACE

### P2

1. Removed deployment assets create ambiguity.
- Action: REPLACE with explicit local-first supported workflow docs.

## Issue matrix (REMOVE / REPLACE / RESTORE)

- Legacy app-token auth: REPLACE
- Durable idempotency storage: REPLACE
- Versioned migrations: RESTORE
- Backend test scaffolding: RESTORE
- Frontend test/lint scaffolding: RESTORE
- Hardcoded production API default: REPLACE
- Missing perf-smoke script: RESTORE
- README drift: REPLACE
- Stale deployment claims: REMOVE from docs (unless files are restored)
