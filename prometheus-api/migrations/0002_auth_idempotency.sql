-- Migration 0002: auth hardening, durable idempotency, normalized inventory uniqueness
-- Apply after 0001_initial.sql.

ALTER TABLE devices ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS token_revoked_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;

ALTER TABLE inventory ADD COLUMN IF NOT EXISTS name_normalized TEXT;
UPDATE inventory SET name_normalized = lower(trim(name)) WHERE name_normalized IS NULL;
ALTER TABLE inventory ALTER COLUMN name_normalized SET NOT NULL;

DROP INDEX IF EXISTS idx_inventory_device_name_unique;
CREATE INDEX IF NOT EXISTS idx_inventory_name_normalized ON inventory(name_normalized);
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_device_name_normalized_unique
    ON inventory(device_id, name_normalized);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    method VARCHAR(12) NOT NULL,
    path TEXT NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    response_status INTEGER NOT NULL,
    response_body JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_device_created
    ON idempotency_keys(device_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_idempotency_keys_unique
    ON idempotency_keys(device_id, method, path, idempotency_key);

ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access" ON idempotency_keys;
CREATE POLICY "Service role full access" ON idempotency_keys
    FOR ALL TO service_role USING (true) WITH CHECK (true);

REVOKE ALL ON idempotency_keys FROM anon, authenticated;
