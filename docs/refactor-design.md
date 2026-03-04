# Refactor Design

Date: 2026-03-04

## Target architecture

Backend
- `app/api`: route handlers only.
- `app/core`: config/security/idempotency/normalization primitives.
- `app/services`: integrations and domain services.
- `migrations/`: ordered SQL migration source of truth.

Frontend
- `services/config`: runtime config resolution.
- `services/http-client.ts`: transport + retry/idempotency headers.
- `services/api.ts`: domain facade for screens.
- `services/offline-cache.ts`: queue + cache persistence.

## Auth/security redesign

- Primary app boundary: public `X-App-ID` allow-list validated server-side.
- Legacy compatibility: optional `X-App-Token` accepted only when enabled.
- Device token lifecycle:
  - issue token at register,
  - hash at rest,
  - rotate endpoint,
  - revoke endpoint,
  - expiry check,
  - `last_used_at` tracking,
  - `token_version` tracking.

## Migration/data model plan

- Add `migrations/0001_initial.sql` and `migrations/0002_auth_idempotency.sql`.
- Introduce `inventory.name_normalized` and unique `(device_id, name_normalized)`.
- Introduce `idempotency_keys` durable store for mutation replay.
- Extend `devices` token lifecycle columns.

## AI reliability contract

- Parse Gemini outputs with strict schema checks.
- Reject invalid JSON/shape with explicit error codes.
- No silent empty-success fallbacks for parse failures.

## Backup reliability contract

- Export/restore returns per-table result records.
- Response includes `status: ok|degraded|failed` and `warnings`.
- Critical table failures fail request.

## Frontend modularization plan

- Isolate runtime configuration in `services/config/runtime.ts`.
- Keep API facade stable while transport/auth header concerns stay in `http-client`.
- Ensure local/dev defaults do not point to production URL.

## Validation plan

Backend
- `python -m compileall app`
- `pytest` for auth, normalization, idempotency, backup, Gemini contract, integration auth flow

Frontend
- `npm ci`
- `npm run typecheck`
- `npm run lint`
- `npm test`

Docs
- ensure README commands map to existing files/scripts.

## Rollback / compatibility risks

- Legacy clients without `X-App-ID` require temporary legacy token support.
- Unique index on normalized names can surface previously hidden duplicates.
- Strict AI parsing will surface more explicit failures until prompts/models stabilize.
