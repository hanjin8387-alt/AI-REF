from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.units import DEFAULT_UNIT
from .inventory import InventoryItem


class ShoppingItemStatus(str, Enum):
    PENDING = "pending"
    PURCHASED = "purchased"
    CANCELED = "canceled"


class ShoppingItemSource(str, Enum):
    MANUAL = "manual"
    RECIPE = "recipe"
    LOW_STOCK = "low_stock"


class ShoppingItemInput(BaseModel):
    name: str
    quantity: float = Field(default=1, ge=0)
    unit: str = DEFAULT_UNIT


class ShoppingItem(BaseModel):
    id: Optional[str] = None
    name: str
    quantity: float
    unit: str
    status: ShoppingItemStatus = ShoppingItemStatus.PENDING
    source: ShoppingItemSource = ShoppingItemSource.MANUAL
    recipe_id: Optional[str] = None
    recipe_title: Optional[str] = None
    added_to_inventory: bool = False
    purchased_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ShoppingListResponse(BaseModel):
    items: List[ShoppingItem]
    total_count: int
    pending_count: int
    purchased_count: int
    limit: int
    offset: int
    has_more: bool


class AddShoppingItemsRequest(BaseModel):
    items: List[ShoppingItemInput]
    source: ShoppingItemSource = ShoppingItemSource.MANUAL
    recipe_id: Optional[str] = None
    recipe_title: Optional[str] = None


class AddShoppingFromRecipeRequest(BaseModel):
    recipe_id: str
    recipe_title: str
    servings: float = Field(default=1, gt=0)
    ingredients: List[ShoppingItemInput]


class AddShoppingItemsResponse(BaseModel):
    success: bool
    added_count: int
    updated_count: int
    items: List[ShoppingItem]


class ShoppingCheckoutRequest(BaseModel):
    ids: List[str] = Field(default_factory=list)
    add_to_inventory: bool = True


class ShoppingCheckoutResponse(BaseModel):
    success: bool
    checked_out_count: int
    added_count: int
    updated_count: int
    inventory_items: List[InventoryItem]


class ShoppingItemUpdateRequest(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    status: Optional[ShoppingItemStatus] = None


class ShoppingDeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_item: Optional[ShoppingItem] = None
