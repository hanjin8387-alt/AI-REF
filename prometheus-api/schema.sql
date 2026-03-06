-- PROMETHEUS Database Schema (Supabase)
-- Safe to run multiple times.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Devices
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) UNIQUE NOT NULL,
    device_secret_hash TEXT,
    token_version INTEGER NOT NULL DEFAULT 1,
    token_expires_at TIMESTAMPTZ,
    token_revoked_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    push_token TEXT,
    platform VARCHAR(20) DEFAULT 'unknown',
    app_version VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scan enums
DO $$
BEGIN
    CREATE TYPE scan_source_type AS ENUM ('camera', 'gallery', 'receipt');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE scan_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Scans
CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255),
    source_type scan_source_type DEFAULT 'camera',
    status scan_status DEFAULT 'pending',
    original_filename VARCHAR(255),
    items JSONB DEFAULT '[]'::jsonb,
    raw_text TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inventory
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    name_normalized TEXT,
    name_normalization_version INTEGER NOT NULL DEFAULT 1,
    quantity DECIMAL(10, 2) DEFAULT 1,
    unit VARCHAR(50) DEFAULT U&'\AC1C',
    category VARCHAR(100),
    expiry_date DATE,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Recipes (optional persistent catalog)
CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    image_url TEXT,
    cooking_time_minutes INTEGER DEFAULT 30,
    difficulty VARCHAR(20) DEFAULT 'medium',
    servings INTEGER DEFAULT 2,
    ingredients JSONB DEFAULT '[]'::jsonb,
    instructions JSONB DEFAULT '[]'::jsonb,
    priority_score DECIMAL(3, 2) DEFAULT 0.50,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE recipes ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN DEFAULT FALSE;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS device_secret_hash TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS token_revoked_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS name_normalized TEXT;
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS name_normalization_version INTEGER NOT NULL DEFAULT 1;
UPDATE inventory SET name_normalized = lower(trim(name)) WHERE name_normalized IS NULL;
ALTER TABLE inventory ALTER COLUMN name_normalized SET NOT NULL;
ALTER TABLE inventory ALTER COLUMN unit SET DEFAULT U&'\AC1C';
UPDATE inventory SET unit = U&'\AC1C' WHERE unit IS NULL OR btrim(unit) = '' OR lower(unit) = 'unit';

-- Favorites (supports generated non-UUID recipe IDs)
CREATE TABLE IF NOT EXISTS favorite_recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    recipe_id VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    recipe_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(device_id, recipe_id)
);

-- Cooking history
CREATE TABLE IF NOT EXISTS cooking_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255),
    recipe_id UUID REFERENCES recipes(id),
    recipe_title VARCHAR(255),
    servings INTEGER DEFAULT 1,
    deducted_items JSONB DEFAULT '[]'::jsonb,
    cooked_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    type VARCHAR(30) NOT NULL DEFAULT 'system',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Shopping list
CREATE TABLE IF NOT EXISTS shopping_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10, 2) DEFAULT 1,
    unit VARCHAR(50) DEFAULT U&'\AC1C',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    source VARCHAR(20) NOT NULL DEFAULT 'manual',
    recipe_id VARCHAR(255),
    recipe_title VARCHAR(255),
    added_to_inventory BOOLEAN DEFAULT FALSE,
    purchased_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT shopping_items_status_check CHECK (status IN ('pending', 'purchased', 'canceled')),
    CONSTRAINT shopping_items_source_check CHECK (source IN ('manual', 'recipe', 'low_stock'))
);

ALTER TABLE shopping_items ALTER COLUMN unit SET DEFAULT U&'\AC1C';
UPDATE shopping_items SET unit = U&'\AC1C' WHERE unit IS NULL OR btrim(unit) = '' OR lower(unit) = 'unit';

-- Inventory change logs (for statistics)
CREATE TABLE IF NOT EXISTS inventory_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    action VARCHAR(20) NOT NULL,
    quantity_change DECIMAL(10, 2) DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT inventory_logs_action_check CHECK (action IN ('add', 'update', 'delete', 'cook', 'expire', 'restore'))
);

-- Receipt price history
CREATE TABLE IF NOT EXISTS price_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    item_name VARCHAR(255) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(12) NOT NULL DEFAULT 'KRW',
    store_name VARCHAR(255),
    purchased_on DATE,
    source_type VARCHAR(20) NOT NULL DEFAULT 'receipt',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Async recommendation jobs
CREATE TABLE IF NOT EXISTS recipe_recommendation_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    recipes JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT recipe_recommendation_jobs_status_check
        CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Durable idempotency keys for mutation replay safety.
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_inventory_logs_device_created ON inventory_logs(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_logs_device_action ON inventory_logs(device_id, action);
CREATE INDEX IF NOT EXISTS idx_inventory_name ON inventory(name);
CREATE INDEX IF NOT EXISTS idx_inventory_name_normalized ON inventory(name_normalized);
CREATE INDEX IF NOT EXISTS idx_inventory_expiry ON inventory(expiry_date);
CREATE INDEX IF NOT EXISTS idx_inventory_device ON inventory(device_id);
CREATE INDEX IF NOT EXISTS idx_inventory_device_expiry ON inventory(device_id, expiry_date);
CREATE INDEX IF NOT EXISTS idx_inventory_device_updated ON inventory(device_id, updated_at DESC);
DROP INDEX IF EXISTS idx_inventory_device_name_unique;
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_device_name_normalized_unique ON inventory(device_id, name_normalized);

CREATE INDEX IF NOT EXISTS idx_scans_device ON scans(device_id);
CREATE INDEX IF NOT EXISTS idx_cooking_history_device ON cooking_history(device_id);
CREATE INDEX IF NOT EXISTS idx_cooking_history_device_cooked ON cooking_history(device_id, cooked_at DESC);
CREATE INDEX IF NOT EXISTS idx_favorite_recipes_device_created ON favorite_recipes(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_device_created ON notifications(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_device_unread ON notifications(device_id, is_read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shopping_items_device_created ON shopping_items(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shopping_items_device_status ON shopping_items(device_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shopping_items_device_updated ON shopping_items(device_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_device_created ON price_history(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_price_history_device_item ON price_history(device_id, item_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recipe_recommendation_jobs_device_updated
    ON recipe_recommendation_jobs(device_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_device_created ON idempotency_keys(device_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_idempotency_keys_unique
    ON idempotency_keys(device_id, method, path, idempotency_key);
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

-- Trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_devices_updated_at ON devices;
CREATE TRIGGER update_devices_updated_at
BEFORE UPDATE ON devices
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_scans_updated_at ON scans;
CREATE TRIGGER update_scans_updated_at
BEFORE UPDATE ON scans
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_inventory_updated_at ON inventory;
CREATE TRIGGER update_inventory_updated_at
BEFORE UPDATE ON inventory
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_recipes_updated_at ON recipes;
CREATE TRIGGER update_recipes_updated_at
BEFORE UPDATE ON recipes
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_shopping_items_updated_at ON shopping_items;
CREATE TRIGGER update_shopping_items_updated_at
BEFORE UPDATE ON shopping_items
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_recipe_recommendation_jobs_updated_at ON recipe_recommendation_jobs;
CREATE TRIGGER update_recipe_recommendation_jobs_updated_at
BEFORE UPDATE ON recipe_recommendation_jobs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE favorite_recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE cooking_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE shopping_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipe_recommendation_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE legacy_auth_event_counters ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access" ON devices;
DROP POLICY IF EXISTS "Service role full access" ON scans;
DROP POLICY IF EXISTS "Service role full access" ON inventory;
DROP POLICY IF EXISTS "Service role full access" ON recipes;
DROP POLICY IF EXISTS "Service role full access" ON favorite_recipes;
DROP POLICY IF EXISTS "Service role full access" ON cooking_history;
DROP POLICY IF EXISTS "Service role full access" ON notifications;
DROP POLICY IF EXISTS "Service role full access" ON shopping_items;
DROP POLICY IF EXISTS "Service role full access" ON inventory_logs;
DROP POLICY IF EXISTS "Service role full access" ON price_history;
DROP POLICY IF EXISTS "Service role full access" ON recipe_recommendation_jobs;
DROP POLICY IF EXISTS "Service role full access" ON idempotency_keys;
DROP POLICY IF EXISTS "Service role full access" ON legacy_auth_event_counters;

CREATE POLICY "Service role full access" ON devices
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON scans
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON inventory
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON recipes
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON favorite_recipes
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON cooking_history
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON notifications
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON shopping_items
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON inventory_logs
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON price_history
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON recipe_recommendation_jobs
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON idempotency_keys
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON legacy_auth_event_counters
    FOR ALL TO service_role USING (true) WITH CHECK (true);

REVOKE ALL ON devices, scans, inventory, recipes, favorite_recipes, cooking_history, notifications, shopping_items, inventory_logs, price_history, recipe_recommendation_jobs, idempotency_keys, legacy_auth_event_counters
FROM anon, authenticated;

-- Transactional cook completion: inventory updates/deletes + history insert
CREATE OR REPLACE FUNCTION complete_cooking_transaction(
    p_device_id VARCHAR,
    p_recipe_id UUID,
    p_recipe_title VARCHAR,
    p_servings INTEGER,
    p_deducted_items JSONB,
    p_updates JSONB,
    p_delete_ids UUID[]
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_history_id UUID;
    v_item JSONB;
    v_updated_count INTEGER;
BEGIN
    IF p_updates IS NOT NULL THEN
        FOR v_item IN SELECT value FROM jsonb_array_elements(p_updates) AS value
        LOOP
            UPDATE inventory
            SET quantity = COALESCE((v_item ->> 'quantity')::numeric, quantity)
            WHERE id = (v_item ->> 'id')::uuid
              AND device_id = p_device_id;

            GET DIAGNOSTICS v_updated_count = ROW_COUNT;
            IF v_updated_count = 0 THEN
                RAISE EXCEPTION 'Inventory item not found for device. item_id=%', v_item ->> 'id';
            END IF;
        END LOOP;
    END IF;

    IF p_delete_ids IS NOT NULL AND array_length(p_delete_ids, 1) > 0 THEN
        DELETE FROM inventory
        WHERE device_id = p_device_id
          AND id = ANY(p_delete_ids);
    END IF;

    INSERT INTO cooking_history (
        device_id,
        recipe_id,
        recipe_title,
        servings,
        deducted_items
    )
    VALUES (
        p_device_id,
        p_recipe_id,
        p_recipe_title,
        p_servings,
        COALESCE(p_deducted_items, '[]'::jsonb)
    )
    RETURNING id INTO v_history_id;

    RETURN v_history_id;
END;
$$;

GRANT EXECUTE ON FUNCTION complete_cooking_transaction(VARCHAR, UUID, VARCHAR, INTEGER, JSONB, JSONB, UUID[])
TO service_role;
