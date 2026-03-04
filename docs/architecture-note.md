# Architecture Note

Date: 2026-03-04

## Backend (`prometheus-api`)

- Framework: FastAPI + Supabase client.
- Entry point: `app/main.py`.
- API routers: `app/api/*`.
- Core modules:
  - `app/core/config.py`: environment-driven runtime settings.
  - `app/core/security.py`: app identity validation + device token auth lifecycle checks.
  - `app/core/idempotency.py`: durable idempotency read/write helpers backed by DB table.
  - `app/core/normalization.py`: canonical item name normalization.
- Services:
  - `app/services/gemini_service.py`: Gemini integration with strict contract validation.
  - `app/services/inventory_service.py`: normalized inventory upsert logic.

## Frontend (`prometheus-app`)

- Framework: Expo Router + React Native + TypeScript.
- Runtime config:
  - `services/config/runtime.ts` reads `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_APP_ID`, optional legacy token.
- Networking:
  - `services/http-client.ts` sends `X-App-ID`, device headers, and mutation idempotency keys.
  - `services/api.ts` exposes domain API facade for screens.
- Offline behavior:
  - `services/offline-cache.ts` stores offline snapshots + mutation queue.

## Auth model summary

- Public app identifier is `X-App-ID`.
- Legacy `X-App-Token` is compatibility-only when server flag allows it.
- Device token is server-issued, hash-stored, versioned, expirable, revocable, and tracks `last_used_at`.

## Reliability summary

- Mutation endpoints support server-side idempotency replay via `idempotency_keys` table.
- AI calls use `google.genai` with `response_schema` enforcement, then perform server-side schema validation.
- Backup export/restore returns per-table result records and marks degraded/failed outcomes explicitly.
