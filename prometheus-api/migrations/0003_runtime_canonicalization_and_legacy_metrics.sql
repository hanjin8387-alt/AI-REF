-- Migration 0003: runtime canonicalization tracking, durable legacy auth metrics, and canonical unit defaults
-- Apply after 0002_auth_idempotency.sql.

ALTER TABLE inventory
    ADD COLUMN IF NOT EXISTS name_normalization_version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE inventory
    ALTER COLUMN unit SET DEFAULT U&'\AC1C';

UPDATE inventory
SET
    unit = U&'\AC1C'
WHERE unit IS NULL OR btrim(unit) = '' OR lower(unit) = 'unit';

ALTER TABLE shopping_items
    ALTER COLUMN unit SET DEFAULT U&'\AC1C';

UPDATE shopping_items
SET
    unit = U&'\AC1C'
WHERE unit IS NULL OR btrim(unit) = '' OR lower(unit) = 'unit';

CREATE TABLE IF NOT EXISTS legacy_auth_event_counters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auth_mode VARCHAR(64) NOT NULL DEFAULT 'legacy_app_token',
    outcome VARCHAR(32) NOT NULL,
    reason VARCHAR(64) NOT NULL,
    event_count BIGINT NOT NULL DEFAULT 0,
    first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(auth_mode, outcome, reason)
);

CREATE INDEX IF NOT EXISTS idx_legacy_auth_event_counters_last_seen
    ON legacy_auth_event_counters(last_observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_legacy_auth_event_counters_outcome_reason
    ON legacy_auth_event_counters(auth_mode, outcome, reason);

CREATE OR REPLACE FUNCTION increment_legacy_auth_event_counter(
    p_auth_mode VARCHAR,
    p_outcome VARCHAR,
    p_reason VARCHAR
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO legacy_auth_event_counters (
        auth_mode,
        outcome,
        reason,
        event_count,
        first_observed_at,
        last_observed_at
    )
    VALUES (
        COALESCE(NULLIF(p_auth_mode, ''), 'legacy_app_token'),
        p_outcome,
        p_reason,
        1,
        NOW(),
        NOW()
    )
    ON CONFLICT (auth_mode, outcome, reason)
    DO UPDATE SET
        event_count = legacy_auth_event_counters.event_count + 1,
        last_observed_at = NOW();
END;
$$;

GRANT EXECUTE ON FUNCTION increment_legacy_auth_event_counter(VARCHAR, VARCHAR, VARCHAR)
TO service_role;

ALTER TABLE legacy_auth_event_counters ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access" ON legacy_auth_event_counters;
CREATE POLICY "Service role full access" ON legacy_auth_event_counters
    FOR ALL TO service_role USING (true) WITH CHECK (true);

REVOKE ALL ON legacy_auth_event_counters FROM anon, authenticated;
