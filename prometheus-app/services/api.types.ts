export type ScanSourceType = 'camera' | 'gallery' | 'receipt';
export type ScanStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type SortOption = 'expiry_date' | 'name' | 'created_at';

export type FoodItem = {
  name: string;
  quantity: number;
  unit: string;
  expiry_date?: string;
  category?: '냉장' | '냉동' | '상온' | string;
  confidence?: number;
  unit_price?: number;
  total_price?: number;
  currency?: string;
};

export type ScanResultPayload = {
  scan_id: string;
  status: ScanStatus;
  items: FoodItem[];
  raw_text?: string;
  error_message?: string;
  receipt_store?: string;
  receipt_purchased_at?: string;
};

export type InventoryItem = {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  expiry_date?: string;
  category?: string;
  created_at?: string;
  updated_at?: string;
};

export type InventoryListResponse = {
  items: InventoryItem[];
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
  offline?: boolean;
  cache_timestamp?: number | null;
};

export type ApiRecipe = {
  id: string;
  title: string;
  description: string;
  recommendation_reason?: string;
  image_url?: string;
  cooking_time_minutes: number;
  difficulty: string;
  servings: number;
  ingredients: Array<{
    name: string;
    quantity: number;
    unit: string;
    available: boolean;
    expiry_days?: number;
  }>;
  instructions: string[];
  priority_score: number;
  is_favorite: boolean;
};

export type CookingHistoryItem = {
  id: string;
  recipe_id?: string | null;
  recipe_title: string;
  servings: number;
  deducted_items: Array<{
    name: string;
    deducted: number;
    remaining: number;
    deleted: boolean;
  }>;
  cooked_at: string;
};

export type CookingHistoryResponse = {
  items: CookingHistoryItem[];
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export type NotificationItem = {
  id: string;
  type: 'inventory' | 'cooking' | 'expiry' | 'system';
  title: string;
  message: string;
  is_read: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  read_at?: string;
};

export type NotificationListResponse = {
  items: NotificationItem[];
  total_count: number;
  unread_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export type ShoppingItemStatus = 'pending' | 'purchased' | 'canceled';
export type ShoppingItemSource = 'manual' | 'recipe' | 'low_stock';

export type ShoppingItem = {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  status: ShoppingItemStatus;
  source: ShoppingItemSource;
  recipe_id?: string;
  recipe_title?: string;
  added_to_inventory: boolean;
  purchased_at?: string;
  created_at?: string;
  updated_at?: string;
};

export type ShoppingListResponse = {
  items: ShoppingItem[];
  total_count: number;
  pending_count: number;
  purchased_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

export type ShoppingCheckoutResponse = {
  success: boolean;
  checked_out_count: number;
  added_count: number;
  updated_count: number;
  inventory_items: InventoryItem[];
};

export type LowStockSuggestionItem = {
  name: string;
  current_quantity: number;
  unit: string;
  predicted_days_left: number;
  recommended_quantity: number;
};

export type LowStockSuggestionResponse = {
  items: LowStockSuggestionItem[];
  total_count: number;
};

// --- Statistics ---

export type CookingStats = {
  total_cooked: number;
  most_cooked_recipe?: string;
  average_per_week: number;
};

export type InventoryStats = {
  total_added: number;
  total_consumed: number;
  total_expired: number;
  waste_rate: number;
  most_used_ingredient?: string;
  category_breakdown: Array<{ category: string; count: number }>;
};

export type ShoppingStats = {
  total_purchased: number;
  total_items: number;
};

export type StatsSummaryResponse = {
  period: string;
  cooking: CookingStats;
  inventory: InventoryStats;
  shopping: ShoppingStats;
};

export type PriceHistoryItem = {
  id: string;
  item_name: string;
  unit_price: number;
  currency: string;
  store_name?: string;
  purchased_on?: string;
  source_type?: string;
  created_at?: string;
};

export type PriceHistoryResponse = {
  items: PriceHistoryItem[];
  total_count: number;
};

// --- Barcode ---

export type BarcodeProductInfo = {
  name: string;
  category?: string;
  suggested_expiry_days?: number;
  image_url?: string;
};

export type BarcodeResponse = {
  found: boolean;
  barcode: string;
  product?: BarcodeProductInfo;
};

export type BackupExportResponse = {
  success: boolean;
  exported_at: string;
  payload: Record<string, unknown>;
};

export type BackupRestoreResponse = {
  success: boolean;
  message: string;
  restored_counts: Record<string, number>;
};

export type SyncStatusResponse = {
  online: boolean;
  pending_count: number;
  last_sync_at?: number | null;
  queue_health?: 'healthy' | 'warning' | 'critical';
  oldest_pending_age_ms?: number;
  stale_cache_age_ms?: number;
};

export type BootstrapResponse = {
  api_ok: boolean;
  token_required: boolean;
  device_registered: boolean;
  sync_pending_count: number;
  last_sync_at?: string | null;
};
