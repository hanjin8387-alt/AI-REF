from typing import Any, List, Optional

from pydantic import BaseModel, Field


class CookingStats(BaseModel):
    total_cooked: int = 0
    most_cooked_recipe: Optional[str] = None
    average_per_week: float = 0.0


class InventoryStats(BaseModel):
    total_added: int = 0
    total_consumed: int = 0
    total_expired: int = 0
    waste_rate: float = 0.0
    most_used_ingredient: Optional[str] = None
    category_breakdown: List[dict[str, Any]] = Field(default_factory=list)


class ShoppingStats(BaseModel):
    total_purchased: int = 0
    total_items: int = 0


class StatsSummaryResponse(BaseModel):
    period: str
    cooking: CookingStats
    inventory: InventoryStats
    shopping: ShoppingStats


class ExpiryCheckResponse(BaseModel):
    devices_checked: int = 0
    notifications_sent: int = 0
    errors: int = 0
