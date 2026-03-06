-- Migration 0004: claim-first idempotency, atomic backup restore RPC, and normalization version alignment
-- Forward-only. 0001/0002/0003 remain unchanged.

ALTER TABLE inventory
    ALTER COLUMN name_normalization_version SET DEFAULT 2;

UPDATE inventory
SET
    name_normalized = lower(regexp_replace(BTRIM(name), '\s+', ' ', 'g')),
    name_normalization_version = 1
WHERE name_normalized IS NULL
  AND NULLIF(BTRIM(name), '') IS NOT NULL;

ALTER TABLE shopping_items
    ADD COLUMN IF NOT EXISTS name_normalized TEXT,
    ADD COLUMN IF NOT EXISTS name_normalization_version INTEGER NOT NULL DEFAULT 2;

ALTER TABLE shopping_items
    ALTER COLUMN name_normalization_version SET DEFAULT 2;

UPDATE shopping_items
SET
    name_normalized = lower(regexp_replace(BTRIM(name), '\s+', ' ', 'g')),
    name_normalization_version = 1
WHERE name_normalized IS NULL
  AND NULLIF(BTRIM(name), '') IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_shopping_items_device_name_normalized
    ON shopping_items(device_id, name_normalized);

ALTER TABLE idempotency_keys
    ADD COLUMN IF NOT EXISTS request_fingerprint TEXT,
    ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'committed',
    ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS failure_code VARCHAR(64),
    ADD COLUMN IF NOT EXISTS failure_message TEXT;

ALTER TABLE idempotency_keys
    ALTER COLUMN response_status DROP NOT NULL;

UPDATE idempotency_keys
SET
    status = 'committed',
    locked_until = NULL,
    updated_at = COALESCE(updated_at, created_at, NOW())
WHERE status IS NULL OR status NOT IN ('in_progress', 'committed', 'failed');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'idempotency_keys_status_check'
    ) THEN
        ALTER TABLE idempotency_keys
            ADD CONSTRAINT idempotency_keys_status_check
            CHECK (status IN ('in_progress', 'committed', 'failed'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_status_locked_until
    ON idempotency_keys(status, locked_until);
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_updated_at
    ON idempotency_keys(updated_at DESC);

CREATE OR REPLACE FUNCTION claim_idempotency_key(
    p_device_id VARCHAR,
    p_method VARCHAR,
    p_path TEXT,
    p_idempotency_key VARCHAR,
    p_request_fingerprint TEXT,
    p_lock_ttl_seconds INTEGER DEFAULT 120,
    p_replay_ttl_seconds INTEGER DEFAULT 86400
)
RETURNS TABLE (
    action TEXT,
    status TEXT,
    response_status INTEGER,
    response_headers JSONB,
    response_body JSONB,
    retry_after_seconds INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_now TIMESTAMPTZ := NOW();
    v_locked_until TIMESTAMPTZ := NOW() + make_interval(secs => GREATEST(COALESCE(p_lock_ttl_seconds, 0), 1));
    v_expires_at TIMESTAMPTZ := NOW() + make_interval(secs => GREATEST(COALESCE(p_replay_ttl_seconds, 0), 1));
    v_existing idempotency_keys%ROWTYPE;
    v_retry_after INTEGER := 0;
BEGIN
    SELECT *
    INTO v_existing
    FROM idempotency_keys
    WHERE device_id = p_device_id
      AND method = UPPER(p_method)
      AND path = p_path
      AND idempotency_key = p_idempotency_key
    FOR UPDATE;

    IF NOT FOUND THEN
        INSERT INTO idempotency_keys (
            device_id,
            method,
            path,
            idempotency_key,
            request_fingerprint,
            status,
            locked_until,
            response_status,
            response_headers,
            response_body,
            failure_code,
            failure_message,
            created_at,
            updated_at,
            expires_at
        )
        VALUES (
            p_device_id,
            UPPER(p_method),
            p_path,
            p_idempotency_key,
            p_request_fingerprint,
            'in_progress',
            v_locked_until,
            NULL,
            '{}'::jsonb,
            '{}'::jsonb,
            NULL,
            NULL,
            v_now,
            v_now,
            v_expires_at
        );

        RETURN QUERY
        SELECT
            'started'::TEXT,
            'in_progress'::TEXT,
            NULL::INTEGER,
            '{}'::jsonb,
            '{}'::jsonb,
            0::INTEGER;
        RETURN;
    END IF;

    IF v_existing.expires_at <= v_now THEN
        UPDATE idempotency_keys
        SET
            request_fingerprint = p_request_fingerprint,
            status = 'in_progress',
            locked_until = v_locked_until,
            response_status = NULL,
            response_headers = '{}'::jsonb,
            response_body = '{}'::jsonb,
            failure_code = NULL,
            failure_message = NULL,
            created_at = v_now,
            updated_at = v_now,
            expires_at = v_expires_at
        WHERE id = v_existing.id;

        RETURN QUERY
        SELECT
            'started'::TEXT,
            'in_progress'::TEXT,
            NULL::INTEGER,
            '{}'::jsonb,
            '{}'::jsonb,
            0::INTEGER;
        RETURN;
    END IF;

    IF COALESCE(v_existing.request_fingerprint, '') <> COALESCE(p_request_fingerprint, '') THEN
        RETURN QUERY
        SELECT
            'conflict'::TEXT,
            v_existing.status::TEXT,
            v_existing.response_status,
            COALESCE(v_existing.response_headers, '{}'::jsonb),
            COALESCE(v_existing.response_body, '{}'::jsonb),
            0::INTEGER;
        RETURN;
    END IF;

    IF v_existing.status = 'committed' THEN
        RETURN QUERY
        SELECT
            'replay'::TEXT,
            v_existing.status::TEXT,
            v_existing.response_status,
            COALESCE(v_existing.response_headers, '{}'::jsonb),
            COALESCE(v_existing.response_body, '{}'::jsonb),
            0::INTEGER;
        RETURN;
    END IF;

    IF v_existing.status = 'in_progress'
       AND v_existing.locked_until IS NOT NULL
       AND v_existing.locked_until > v_now THEN
        v_retry_after := GREATEST(1, CEIL(EXTRACT(EPOCH FROM (v_existing.locked_until - v_now)))::INTEGER);
        RETURN QUERY
        SELECT
            'in_progress'::TEXT,
            v_existing.status::TEXT,
            v_existing.response_status,
            COALESCE(v_existing.response_headers, '{}'::jsonb),
            COALESCE(v_existing.response_body, '{}'::jsonb),
            v_retry_after;
        RETURN;
    END IF;

    UPDATE idempotency_keys
    SET
        request_fingerprint = p_request_fingerprint,
        status = 'in_progress',
        locked_until = v_locked_until,
        response_status = NULL,
        response_headers = '{}'::jsonb,
        response_body = '{}'::jsonb,
        failure_code = NULL,
        failure_message = NULL,
        updated_at = v_now,
        expires_at = v_expires_at
    WHERE id = v_existing.id;

    RETURN QUERY
    SELECT
        'started'::TEXT,
        'in_progress'::TEXT,
        NULL::INTEGER,
        '{}'::jsonb,
        '{}'::jsonb,
        0::INTEGER;
END;
$$;

CREATE OR REPLACE FUNCTION commit_idempotency_key(
    p_device_id VARCHAR,
    p_method VARCHAR,
    p_path TEXT,
    p_idempotency_key VARCHAR,
    p_request_fingerprint TEXT,
    p_response_status INTEGER,
    p_response_headers JSONB,
    p_response_body JSONB,
    p_replay_ttl_seconds INTEGER DEFAULT 86400
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_now TIMESTAMPTZ := NOW();
    v_expires_at TIMESTAMPTZ := NOW() + make_interval(secs => GREATEST(COALESCE(p_replay_ttl_seconds, 0), 1));
BEGIN
    UPDATE idempotency_keys
    SET
        status = 'committed',
        locked_until = NULL,
        response_status = p_response_status,
        response_headers = COALESCE(p_response_headers, '{}'::jsonb),
        response_body = COALESCE(p_response_body, '{}'::jsonb),
        failure_code = NULL,
        failure_message = NULL,
        updated_at = v_now,
        expires_at = v_expires_at
    WHERE device_id = p_device_id
      AND method = UPPER(p_method)
      AND path = p_path
      AND idempotency_key = p_idempotency_key
      AND COALESCE(request_fingerprint, '') = COALESCE(p_request_fingerprint, '');

    RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION fail_idempotency_key(
    p_device_id VARCHAR,
    p_method VARCHAR,
    p_path TEXT,
    p_idempotency_key VARCHAR,
    p_request_fingerprint TEXT,
    p_failure_code VARCHAR DEFAULT NULL,
    p_failure_message TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE idempotency_keys
    SET
        status = 'failed',
        locked_until = NULL,
        response_status = NULL,
        response_headers = '{}'::jsonb,
        response_body = '{}'::jsonb,
        failure_code = p_failure_code,
        failure_message = p_failure_message,
        updated_at = NOW()
    WHERE device_id = p_device_id
      AND method = UPPER(p_method)
      AND path = p_path
      AND idempotency_key = p_idempotency_key
      AND COALESCE(request_fingerprint, '') = COALESCE(p_request_fingerprint, '');

    RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION restore_device_backup_payload(
    p_device_id VARCHAR,
    p_mode VARCHAR,
    p_payload JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_mode TEXT := LOWER(COALESCE(p_mode, 'merge'));
    v_payload JSONB := COALESCE(p_payload, '{}'::jsonb);
    v_inventory_count INTEGER := 0;
    v_shopping_count INTEGER := 0;
    v_favorite_count INTEGER := 0;
    v_history_count INTEGER := 0;
    v_notification_count INTEGER := 0;
    v_inventory_log_count INTEGER := 0;
    v_price_history_count INTEGER := 0;
BEGIN
    IF v_mode NOT IN ('merge', 'replace') THEN
        RAISE EXCEPTION 'restore mode must be merge or replace'
            USING ERRCODE = '22023';
    END IF;

    IF v_mode = 'replace' THEN
        DELETE FROM price_history WHERE device_id = p_device_id;
        DELETE FROM inventory_logs WHERE device_id = p_device_id;
        DELETE FROM notifications WHERE device_id = p_device_id;
        DELETE FROM cooking_history WHERE device_id = p_device_id;
        DELETE FROM shopping_items WHERE device_id = p_device_id;
        DELETE FROM favorite_recipes WHERE device_id = p_device_id;
        DELETE FROM inventory WHERE device_id = p_device_id;
    END IF;

    INSERT INTO inventory (
        device_id,
        name,
        name_normalized,
        name_normalization_version,
        quantity,
        unit,
        expiry_date,
        category,
        image_url
    )
    SELECT
        p_device_id,
        x.name,
        x.name_normalized,
        COALESCE(x.name_normalization_version, 2),
        COALESCE(x.quantity, 0),
        COALESCE(NULLIF(BTRIM(x.unit), ''), U&'\AC1C'),
        x.expiry_date,
        NULLIF(BTRIM(x.category), ''),
        NULLIF(BTRIM(x.image_url), '')
    FROM jsonb_to_recordset(COALESCE(v_payload -> 'inventory', '[]'::jsonb)) AS x(
        name TEXT,
        name_normalized TEXT,
        name_normalization_version INTEGER,
        quantity NUMERIC,
        unit TEXT,
        expiry_date DATE,
        category TEXT,
        image_url TEXT
    )
    WHERE NULLIF(BTRIM(x.name), '') IS NOT NULL
      AND NULLIF(BTRIM(x.name_normalized), '') IS NOT NULL
    ON CONFLICT (device_id, name_normalized)
    DO UPDATE SET
        name = EXCLUDED.name,
        name_normalization_version = EXCLUDED.name_normalization_version,
        quantity = EXCLUDED.quantity,
        unit = EXCLUDED.unit,
        expiry_date = EXCLUDED.expiry_date,
        category = EXCLUDED.category,
        image_url = EXCLUDED.image_url;
    GET DIAGNOSTICS v_inventory_count = ROW_COUNT;

    INSERT INTO favorite_recipes (
        device_id,
        recipe_id,
        title,
        recipe_data
    )
    SELECT
        p_device_id,
        x.recipe_id,
        NULLIF(BTRIM(x.title), ''),
        COALESCE(x.recipe_data, '{}'::jsonb)
    FROM jsonb_to_recordset(COALESCE(v_payload -> 'favorite_recipes', '[]'::jsonb)) AS x(
        recipe_id TEXT,
        title TEXT,
        recipe_data JSONB
    )
    WHERE NULLIF(BTRIM(x.recipe_id), '') IS NOT NULL
    ON CONFLICT (device_id, recipe_id)
    DO UPDATE SET
        title = EXCLUDED.title,
        recipe_data = EXCLUDED.recipe_data;
    GET DIAGNOSTICS v_favorite_count = ROW_COUNT;

    INSERT INTO shopping_items (
        device_id,
        name,
        quantity,
        unit,
        status,
        source,
        recipe_id,
        recipe_title,
        added_to_inventory,
        purchased_at,
        created_at,
        updated_at
    )
    SELECT
        p_device_id,
        x.name,
        COALESCE(x.quantity, 0),
        COALESCE(NULLIF(BTRIM(x.unit), ''), U&'\AC1C'),
        COALESCE(NULLIF(BTRIM(x.status), ''), 'pending'),
        COALESCE(NULLIF(BTRIM(x.source), ''), 'manual'),
        NULLIF(BTRIM(x.recipe_id), ''),
        NULLIF(BTRIM(x.recipe_title), ''),
        COALESCE(x.added_to_inventory, FALSE),
        x.purchased_at,
        COALESCE(x.created_at, NOW()),
        COALESCE(x.updated_at, NOW())
    FROM jsonb_to_recordset(COALESCE(v_payload -> 'shopping_items', '[]'::jsonb)) AS x(
        name TEXT,
        quantity NUMERIC,
        unit TEXT,
        status TEXT,
        source TEXT,
        recipe_id TEXT,
        recipe_title TEXT,
        added_to_inventory BOOLEAN,
        purchased_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ
    )
    WHERE NULLIF(BTRIM(x.name), '') IS NOT NULL;
    GET DIAGNOSTICS v_shopping_count = ROW_COUNT;

    INSERT INTO cooking_history (
        device_id,
        recipe_id,
        recipe_title,
        servings,
        deducted_items,
        cooked_at
    )
    SELECT
        p_device_id,
        x.recipe_id,
        NULLIF(BTRIM(x.recipe_title), ''),
        COALESCE(x.servings, 1),
        COALESCE(x.deducted_items, '[]'::jsonb),
        COALESCE(x.cooked_at, NOW())
    FROM jsonb_to_recordset(COALESCE(v_payload -> 'cooking_history', '[]'::jsonb)) AS x(
        recipe_id UUID,
        recipe_title TEXT,
        servings INTEGER,
        deducted_items JSONB,
        cooked_at TIMESTAMPTZ
    );
    GET DIAGNOSTICS v_history_count = ROW_COUNT;

    INSERT INTO notifications (
        device_id,
        type,
        title,
        message,
        metadata,
        is_read,
        read_at,
        created_at
    )
    SELECT
        p_device_id,
        COALESCE(NULLIF(BTRIM(x.type), ''), 'system'),
        x.title,
        x.message,
        COALESCE(x.metadata, '{}'::jsonb),
        COALESCE(x.is_read, FALSE),
        x.read_at,
        COALESCE(x.created_at, NOW())
    FROM jsonb_to_recordset(COALESCE(v_payload -> 'notifications', '[]'::jsonb)) AS x(
        type TEXT,
        title TEXT,
        message TEXT,
        metadata JSONB,
        is_read BOOLEAN,
        read_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ
    )
    WHERE NULLIF(BTRIM(x.title), '') IS NOT NULL
      AND NULLIF(BTRIM(x.message), '') IS NOT NULL;
    GET DIAGNOSTICS v_notification_count = ROW_COUNT;

    INSERT INTO inventory_logs (
        device_id,
        item_name,
        action,
        quantity_change,
        metadata,
        created_at
    )
    SELECT
        p_device_id,
        x.item_name,
        x.action,
        COALESCE(x.quantity_change, 0),
        COALESCE(x.metadata, '{}'::jsonb),
        COALESCE(x.created_at, NOW())
    FROM jsonb_to_recordset(COALESCE(v_payload -> 'inventory_logs', '[]'::jsonb)) AS x(
        item_name TEXT,
        action TEXT,
        quantity_change NUMERIC,
        metadata JSONB,
        created_at TIMESTAMPTZ
    )
    WHERE NULLIF(BTRIM(x.item_name), '') IS NOT NULL
      AND NULLIF(BTRIM(x.action), '') IS NOT NULL;
    GET DIAGNOSTICS v_inventory_log_count = ROW_COUNT;

    INSERT INTO price_history (
        device_id,
        scan_id,
        item_name,
        unit_price,
        currency,
        store_name,
        purchased_on,
        source_type,
        created_at
    )
    SELECT
        p_device_id,
        x.scan_id,
        x.item_name,
        x.unit_price,
        COALESCE(NULLIF(BTRIM(x.currency), ''), 'KRW'),
        NULLIF(BTRIM(x.store_name), ''),
        x.purchased_on,
        COALESCE(NULLIF(BTRIM(x.source_type), ''), 'receipt'),
        COALESCE(x.created_at, NOW())
    FROM jsonb_to_recordset(COALESCE(v_payload -> 'price_history', '[]'::jsonb)) AS x(
        scan_id UUID,
        item_name TEXT,
        unit_price NUMERIC,
        currency TEXT,
        store_name TEXT,
        purchased_on DATE,
        source_type TEXT,
        created_at TIMESTAMPTZ
    )
    WHERE NULLIF(BTRIM(x.item_name), '') IS NOT NULL
      AND x.unit_price IS NOT NULL;
    GET DIAGNOSTICS v_price_history_count = ROW_COUNT;

    RETURN jsonb_build_object(
        'inventory', v_inventory_count,
        'shopping_items', v_shopping_count,
        'favorite_recipes', v_favorite_count,
        'cooking_history', v_history_count,
        'notifications', v_notification_count,
        'inventory_logs', v_inventory_log_count,
        'price_history', v_price_history_count
    );
END;
$$;

GRANT EXECUTE ON FUNCTION claim_idempotency_key(VARCHAR, VARCHAR, TEXT, VARCHAR, TEXT, INTEGER, INTEGER)
TO service_role;
GRANT EXECUTE ON FUNCTION commit_idempotency_key(VARCHAR, VARCHAR, TEXT, VARCHAR, TEXT, INTEGER, JSONB, JSONB, INTEGER)
TO service_role;
GRANT EXECUTE ON FUNCTION fail_idempotency_key(VARCHAR, VARCHAR, TEXT, VARCHAR, TEXT, VARCHAR, TEXT)
TO service_role;
GRANT EXECUTE ON FUNCTION restore_device_backup_payload(VARCHAR, VARCHAR, JSONB)
TO service_role;
