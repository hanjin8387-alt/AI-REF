# Migration Note

Date: 2026-03-04

## Migration source of truth

Use SQL files in `prometheus-api/migrations/`.

- `0001_initial.sql`: baseline schema snapshot.
- `0002_auth_idempotency.sql`: adds auth/token lifecycle columns, durable idempotency table, and inventory normalized uniqueness.

## What changed in 0002

- `devices` table:
  - `token_version`
  - `token_expires_at`
  - `token_revoked_at`
  - `last_used_at`
- `inventory` table:
  - `name_normalized`
  - uniqueness on `(device_id, name_normalized)`
- New table:
  - `idempotency_keys`

## Applying migrations

For existing DBs already initialized with old schema:

1. Apply `migrations/0002_auth_idempotency.sql`.

For new DBs:

1. Apply `migrations/0001_initial.sql`.
2. Apply `migrations/0002_auth_idempotency.sql`.

You can use `prometheus-api/scripts/apply-migrations.sh` with `DATABASE_URL`.

## Compatibility

- Legacy app token remains temporarily compatible when `ALLOW_LEGACY_APP_TOKEN=true`.
- Recommended client migration path is `X-App-ID` + device token only.
