#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.database import get_supabase_client
from app.services.inventory_reconciliation import plan_inventory_name_reconciliation


def _load_rows(device_id: str | None = None) -> list[dict]:
    db = get_supabase_client()
    query = db.table("inventory").select(
        "id,device_id,name,name_normalized,name_normalization_version,quantity,unit,expiry_date,category,created_at"
    )
    if device_id:
        query = query.eq("device_id", device_id)
    return query.execute().data or []


def _apply_plan(actions: list[dict]) -> None:
    db = get_supabase_client()
    for action in actions:
        keep_id = str(action["keep_id"])
        merge_ids = [str(item) for item in action.get("merge_ids") or []]
        update_payload = dict(action.get("update_payload") or {})

        db.table("inventory").update(update_payload).eq("id", keep_id).execute()
        if merge_ids:
            db.table("inventory").delete().in_("id", merge_ids).execute()


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile inventory.name_normalized with the runtime canonicalizer.")
    parser.add_argument("--device-id", help="Optional single-device scope")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Default is dry-run.")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    rows = _load_rows(args.device_id)
    plan = plan_inventory_name_reconciliation(rows)
    payload = {
        "mode": "apply" if args.apply else "dry-run",
        "rows_seen": plan.rows_seen,
        "rows_to_update": plan.rows_to_update,
        "rows_to_delete": plan.rows_to_delete,
        "actions": [
            {
                "keep_id": action.keep_id,
                "merge_ids": action.merge_ids,
                "update_payload": action.update_payload,
            }
            for action in plan.actions
        ],
    }

    if args.apply and plan.actions:
        _apply_plan(payload["actions"])

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
