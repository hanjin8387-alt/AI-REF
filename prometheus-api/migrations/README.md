# SQL Migrations

This project uses ordered SQL migrations under `prometheus-api/migrations`.

## Files

- `0001_initial.sql`: baseline schema snapshot
- `0002_auth_idempotency.sql`: auth hardening + durable idempotency + normalized inventory uniqueness

## How to apply

Apply files in lexical order to the same database:

1. `0001_initial.sql` (new environments)
2. `0002_auth_idempotency.sql`

For existing environments already on old `schema.sql`, apply only `0002_auth_idempotency.sql`.

You can run via your PostgreSQL client (for example `psql`) or Supabase SQL editor.

## Source of truth

- Upgrade path: `migrations/*.sql`
- Convenience full bootstrap: `schema.sql`
