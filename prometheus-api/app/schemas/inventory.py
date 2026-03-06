from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.units import DEFAULT_UNIT


class FoodItem(BaseModel):
    name: str = Field(..., description="Ingredient name")
    quantity: float = Field(default=1, description="Quantity")
    unit: str = Field(default=DEFAULT_UNIT, description="Quantity unit")
    expiry_date: Optional[datetime] = Field(None, description="Expiry date")
    category: Optional[str] = Field(None, description="Storage category: 냉장|냉동|상온")
    confidence: float = Field(default=0.0, description="Recognition confidence, 0-1")
    unit_price: Optional[float] = Field(None, description="Detected unit price from receipt")
    total_price: Optional[float] = Field(None, description="Detected line total price from receipt")
    currency: Optional[str] = Field(default="KRW", description="Detected currency code")


class InventoryItem(BaseModel):
    id: Optional[str] = None
    name: str
    name_normalized: Optional[str] = None
    quantity: float
    unit: str
    expiry_date: Optional[datetime] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class InventoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiry_date: Optional[datetime] = None
    category: Optional[str] = None


class InventoryRestoreRequest(BaseModel):
    name: str
    quantity: float = 1
    unit: str = DEFAULT_UNIT
    expiry_date: Optional[datetime] = None
    category: Optional[str] = None


class InventoryDeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_item: Optional[InventoryItem] = None


class InventoryListResponse(BaseModel):
    items: List[InventoryItem]
    total_count: int
    limit: int
    offset: int
    has_more: bool


class BulkInventoryRequest(BaseModel):
    items: List[FoodItem]


class BulkInventoryResponse(BaseModel):
    success: bool
    added_count: int
    updated_count: int
    items: List[InventoryItem]


class LowStockSuggestionItem(BaseModel):
    name: str
    current_quantity: float
    unit: str
    predicted_days_left: float
    recommended_quantity: float


class LowStockSuggestionResponse(BaseModel):
    items: List[LowStockSuggestionItem]
    total_count: int


class PriceHistoryItem(BaseModel):
    id: str
    item_name: str
    unit_price: float
    currency: str = "KRW"
    store_name: Optional[str] = None
    purchased_on: Optional[str] = None
    source_type: Optional[str] = None
    created_at: Optional[datetime] = None


class PriceHistoryResponse(BaseModel):
    items: List[PriceHistoryItem]
    total_count: int


class BarcodeProductInfo(BaseModel):
    name: str
    category: Optional[str] = None
    suggested_expiry_days: Optional[int] = None
    image_url: Optional[str] = None


class BarcodeResponse(BaseModel):
    found: bool
    barcode: str
    product: Optional[BarcodeProductInfo] = None
