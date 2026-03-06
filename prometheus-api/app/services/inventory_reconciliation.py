from __future__ import annotations

from dataclasses import dataclass, field

from ..core.normalization import NAME_NORMALIZATION_VERSION, normalize_item_name
from ..core.units import normalize_default_unit
from .storage_utils import normalize_storage_category


@dataclass
class InventoryReconciliationAction:
    keep_id: str
    merge_ids: list[str] = field(default_factory=list)
    update_payload: dict[str, object] = field(default_factory=dict)


@dataclass
class InventoryReconciliationPlan:
    actions: list[InventoryReconciliationAction] = field(default_factory=list)
    rows_seen: int = 0
    rows_to_update: int = 0
    rows_to_delete: int = 0


def _sort_key(row: dict) -> tuple[str, str]:
    created_at = str(row.get("created_at") or "")
    row_id = str(row.get("id") or "")
    return (created_at, row_id)


def plan_inventory_name_reconciliation(rows: list[dict]) -> InventoryReconciliationPlan:
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        device_id = str(row.get("device_id") or "").strip()
        row_id = str(row.get("id") or "").strip()
        name = str(row.get("name") or "").strip()
        normalized = normalize_item_name(name)
        if not device_id or not row_id or not name or not normalized:
            continue
        grouped.setdefault((device_id, normalized), []).append(row)

    plan = InventoryReconciliationPlan(rows_seen=len(rows))
    for (_, normalized_name), members in grouped.items():
        ordered = sorted(members, key=_sort_key)
        keep = ordered[0]
        duplicates = ordered[1:]

        merged_quantity = round(sum(max(float(member.get("quantity") or 0), 0.0) for member in ordered), 2)
        expiry_values = [str(member.get("expiry_date") or "").strip() for member in ordered if str(member.get("expiry_date") or "").strip()]
        canonical_expiry = min(expiry_values) if expiry_values else None
        canonical_category = None
        for member in ordered:
            category = normalize_storage_category(member.get("category"))
            if category:
                canonical_category = category
                break

        update_payload = {
            "name": str(keep.get("name") or "").strip(),
            "name_normalized": normalized_name,
            "name_normalization_version": NAME_NORMALIZATION_VERSION,
            "quantity": merged_quantity,
            "unit": normalize_default_unit(keep.get("unit")),
            "expiry_date": canonical_expiry,
            "category": canonical_category,
        }

        needs_update = (
            str(keep.get("name_normalized") or "").strip() != normalized_name
            or int(keep.get("name_normalization_version") or 0) != NAME_NORMALIZATION_VERSION
            or round(float(keep.get("quantity") or 0), 2) != merged_quantity
            or normalize_default_unit(keep.get("unit")) != update_payload["unit"]
            or str(keep.get("expiry_date") or "") != str(canonical_expiry or "")
            or normalize_storage_category(keep.get("category")) != canonical_category
            or bool(duplicates)
        )
        if not needs_update:
            continue

        plan.actions.append(
            InventoryReconciliationAction(
                keep_id=str(keep["id"]),
                merge_ids=[str(member["id"]) for member in duplicates if member.get("id")],
                update_payload=update_payload,
            )
        )

    plan.rows_to_update = len(plan.actions)
    plan.rows_to_delete = sum(len(action.merge_ids) for action in plan.actions)
    return plan
