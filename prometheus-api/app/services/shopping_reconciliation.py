from __future__ import annotations

from dataclasses import dataclass, field

from ..core.normalization import NAME_NORMALIZATION_VERSION, normalize_item_name
from ..core.units import normalize_default_unit


@dataclass
class ShoppingReconciliationAction:
    row_id: str
    device_id: str
    update_payload: dict[str, object] = field(default_factory=dict)


@dataclass
class ShoppingReconciliationPlan:
    actions: list[ShoppingReconciliationAction] = field(default_factory=list)
    rows_seen: int = 0
    rows_to_update: int = 0


def plan_shopping_name_reconciliation(rows: list[dict]) -> ShoppingReconciliationPlan:
    plan = ShoppingReconciliationPlan(rows_seen=len(rows))
    for row in rows:
        row_id = str(row.get("id") or "").strip()
        device_id = str(row.get("device_id") or "").strip()
        name = str(row.get("name") or "").strip()
        normalized_name = normalize_item_name(name)
        if not row_id or not device_id or not name or not normalized_name:
            continue

        update_payload = {
            "name": name,
            "name_normalized": normalized_name,
            "name_normalization_version": NAME_NORMALIZATION_VERSION,
            "unit": normalize_default_unit(row.get("unit")),
        }
        needs_update = (
            str(row.get("name_normalized") or "").strip() != normalized_name
            or int(row.get("name_normalization_version") or 0) != NAME_NORMALIZATION_VERSION
            or normalize_default_unit(row.get("unit")) != update_payload["unit"]
        )
        if not needs_update:
            continue

        plan.actions.append(
            ShoppingReconciliationAction(
                row_id=row_id,
                device_id=device_id,
                update_payload=update_payload,
            )
        )

    plan.rows_to_update = len(plan.actions)
    return plan
