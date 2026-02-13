from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ScanSourceType(str, Enum):
    CAMERA = "camera"
    GALLERY = "gallery"
    RECEIPT = "receipt"


class ScanStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationType(str, Enum):
    INVENTORY = "inventory"
    COOKING = "cooking"
    EXPIRY = "expiry"
    SYSTEM = "system"


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    push_token: Optional[str] = Field(None, description="FCM push token")
    platform: str = Field(default="unknown", description="ios/android/web")
    app_version: Optional[str] = None


class DeviceRegisterResponse(BaseModel):
    success: bool
    device_id: str
    message: str


class BootstrapResponse(BaseModel):
    api_ok: bool
    token_required: bool
    device_registered: bool
    sync_pending_count: int = 0
    last_sync_at: Optional[datetime] = None


class ScanUploadResponse(BaseModel):
    scan_id: str
    status: ScanStatus
    message: str


class FoodItem(BaseModel):
    name: str = Field(..., description="Ingredient name")
    quantity: float = Field(default=1, description="Quantity")
    unit: str = Field(default="개", description="Quantity unit")
    expiry_date: Optional[datetime] = Field(None, description="Expiry date")
    category: Optional[str] = Field(None, description="Storage category: 냉장|냉동|상온")
    confidence: float = Field(default=0.0, description="Recognition confidence, 0-1")
    unit_price: Optional[float] = Field(None, description="Detected unit price from receipt")
    total_price: Optional[float] = Field(None, description="Detected line total price from receipt")
    currency: Optional[str] = Field(default="KRW", description="Detected currency code")


class ScanResultResponse(BaseModel):
    scan_id: str
    status: ScanStatus
    items: List[FoodItem] = Field(default_factory=list)
    raw_text: Optional[str] = None
    error_message: Optional[str] = None
    receipt_store: Optional[str] = None
    receipt_purchased_at: Optional[str] = None


class InventoryItem(BaseModel):
    id: Optional[str] = None
    name: str
    quantity: float
    unit: str
    expiry_date: Optional[datetime] = None
    category: Optional[str] = None
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
    unit: str = "개"
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


class RecipeIngredient(BaseModel):
    name: str
    quantity: float
    unit: str
    available: bool = False
    expiry_days: Optional[int] = None


class Recipe(BaseModel):
    id: str
    title: str
    description: str
    image_url: Optional[str] = None
    cooking_time_minutes: int
    difficulty: str
    servings: int
    ingredients: List[RecipeIngredient]
    instructions: List[str]
    priority_score: float = Field(default=0.0, description="Recommendation priority")
    recommendation_reason: Optional[str] = Field(default=None, description="Why this recipe was recommended")
    is_favorite: bool = False


class RecipeListResponse(BaseModel):
    recipes: List[Recipe]
    total_count: int


class RecommendationJobCreateResponse(BaseModel):
    job_id: str
    status: str


class RecommendationJobStatusResponse(BaseModel):
    job_id: str
    status: str
    recipes: List[Recipe] = Field(default_factory=list)
    total_count: int = 0
    error: Optional[str] = None


class FavoriteRecipeRequest(BaseModel):
    recipe: Optional[Recipe] = None


class FavoriteToggleResponse(BaseModel):
    success: bool
    is_favorite: bool
    message: str


class CookCompleteRequest(BaseModel):
    servings: int = Field(default=1, description="Number of servings cooked")


class CookCompleteResponse(BaseModel):
    success: bool
    message: str
    deducted_items: List[dict[str, Any]]


class CookingHistoryItem(BaseModel):
    id: str
    recipe_id: Optional[str] = None
    recipe_title: str
    servings: int
    deducted_items: List[dict[str, Any]] = Field(default_factory=list)
    cooked_at: datetime


class CookingHistoryResponse(BaseModel):
    items: List[CookingHistoryItem]
    total_count: int
    limit: int
    offset: int
    has_more: bool


class NotificationItem(BaseModel):
    id: str
    type: NotificationType
    title: str
    message: str
    is_read: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    read_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    items: List[NotificationItem]
    total_count: int
    unread_count: int
    limit: int
    offset: int
    has_more: bool


class MarkNotificationsReadRequest(BaseModel):
    ids: List[str] = Field(default_factory=list)


class MarkNotificationsReadResponse(BaseModel):
    success: bool
    updated_count: int


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
    unit: str = "개"


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


class LowStockSuggestionItem(BaseModel):
    name: str
    current_quantity: float
    unit: str
    predicted_days_left: float
    recommended_quantity: float


class LowStockSuggestionResponse(BaseModel):
    items: List[LowStockSuggestionItem]
    total_count: int


# --- Statistics ---

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


class PriceHistoryItem(BaseModel):
    id: str
    item_name: str
    unit_price: float
    currency: str = "KRW"
    store_name: Optional[str] = None
    purchased_on: Optional[str] = None
    source_type: Optional[str] = None
    scan_id: Optional[str] = None
    created_at: Optional[datetime] = None


class PriceHistoryResponse(BaseModel):
    items: List[PriceHistoryItem]
    total_count: int


# --- Barcode ---

class BarcodeProductInfo(BaseModel):
    name: str
    category: Optional[str] = None
    suggested_expiry_days: Optional[int] = None
    image_url: Optional[str] = None


class BarcodeResponse(BaseModel):
    found: bool
    barcode: str
    product: Optional[BarcodeProductInfo] = None


# --- Backup / Restore ---

class BackupRestoreRequest(BaseModel):
    payload: dict[str, Any]
    mode: str = Field(default="merge", description="merge | replace")


class BackupRestoreResponse(BaseModel):
    success: bool
    message: str
    restored_counts: dict[str, int] = Field(default_factory=dict)


class BackupExportResponse(BaseModel):
    success: bool
    exported_at: datetime
    payload: dict[str, Any]


# --- Expiry Check ---

class ExpiryCheckResponse(BaseModel):
    devices_checked: int = 0
    notifications_sent: int = 0
    errors: int = 0
