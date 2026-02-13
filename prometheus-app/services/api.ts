import Constants from 'expo-constants';
import { Platform } from 'react-native';

import type {
  ApiRecipe,
  BackupExportResponse,
  BackupRestoreResponse,
  BarcodeResponse,
  BootstrapResponse,
  CookingHistoryItem,
  CookingHistoryResponse,
  InventoryItem,
  InventoryListResponse,
  LowStockSuggestionResponse,
  NotificationListResponse,
  PriceHistoryResponse,
  ShoppingCheckoutResponse,
  ShoppingItem,
  ShoppingItemSource,
  ShoppingItemStatus,
  ShoppingListResponse,
  ScanResultPayload,
  ScanSourceType,
  SortOption,
  StatsSummaryResponse,
  SyncStatusResponse,
} from './api.types';
import { HttpClient } from './http-client';

export type {
  ApiRecipe,
  BackupExportResponse,
  BarcodeResponse,
  BootstrapResponse,
  CookingHistoryItem,
  CookingHistoryResponse,
  FoodItem,
  InventoryItem,
  InventoryListResponse,
  LowStockSuggestionResponse,
  NotificationItem,
  NotificationListResponse,
  PriceHistoryItem,
  PriceHistoryResponse,
  BackupRestoreResponse,
  ShoppingCheckoutResponse,
  ShoppingItem,
  ShoppingItemSource,
  ShoppingItemStatus,
  ShoppingListResponse,
  ScanResultPayload,
  ScanSourceType,
  ScanStatus,
  SortOption,
  StatsSummaryResponse,
  SyncStatusResponse,
} from './api.types';

const API_URL = Constants.expoConfig?.extra?.apiUrl || 'https://ai-ref-api-274026276907.asia-northeast3.run.app';
const DEFAULT_SCAN_EXTENSION = 'jpg';
const SCAN_UPLOAD_TIMEOUT_MS = 120000;
const SCAN_RESULT_TIMEOUT_MS = 30000;
const RECOMMENDATIONS_TIMEOUT_MS = 45000;

function normalizeImageExtension(raw?: string): string {
  const normalized = (raw || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  if (normalized === 'jpeg') return 'jpg';
  if (normalized === 'heif') return 'heic';
  if (!normalized) return DEFAULT_SCAN_EXTENSION;
  return normalized.slice(0, 5);
}

function extensionFromMimeType(mimeType?: string | null): string {
  if (!mimeType) return DEFAULT_SCAN_EXTENSION;
  const match = mimeType.match(/^image\/([a-zA-Z0-9.+-]+)/i);
  return normalizeImageExtension(match?.[1]);
}

function extensionFromImageUri(imageUri: string): string {
  const dataUriMatch = imageUri.match(/^data:image\/([a-zA-Z0-9.+-]+);base64,/i);
  if (dataUriMatch?.[1]) {
    return normalizeImageExtension(dataUriMatch[1]);
  }

  try {
    const pathname = new URL(imageUri, 'https://local.invalid').pathname;
    const filename = pathname.split('/').pop() || '';
    const extensionMatch = filename.match(/\.([a-zA-Z0-9]{1,8})$/);
    if (extensionMatch?.[1]) {
      return normalizeImageExtension(extensionMatch[1]);
    }
  } catch {
    // Non-standard URIs fall back to default.
  }

  return DEFAULT_SCAN_EXTENSION;
}

class ApiClient extends HttpClient {
  constructor(baseUrl: string) {
    super(baseUrl);
  }

  async uploadScan(imageUri: string, sourceType: ScanSourceType = 'camera') {
    const formData = new FormData();
    const fileExtension = extensionFromImageUri(imageUri);
    const normalizedType = fileExtension === 'jpg' ? 'jpeg' : fileExtension;
    const mimeType = `image/${normalizedType}`;

    if (Platform.OS === 'web') {
      const blobResponse = await fetch(imageUri);
      const blob = await blobResponse.blob();
      const blobExtension = extensionFromMimeType(blob.type) || fileExtension;
      formData.append('file', blob, `scan.${blobExtension}`);
    } else {
      formData.append('file', {
        uri: imageUri,
        name: `scan.${fileExtension}`,
        type: mimeType,
      } as never);
    }

    return this.request<{ scan_id: string; status: string; message: string }>(`/scans/upload?source_type=${sourceType}`, {
      method: 'POST',
      body: formData,
      timeoutMs: SCAN_UPLOAD_TIMEOUT_MS,
    });
  }

  async getScanResult(scanId: string) {
    return this.request<ScanResultPayload>(`/scans/${scanId}/result`, { timeoutMs: SCAN_RESULT_TIMEOUT_MS });
  }

  async getInventory(category?: string, sortBy: SortOption = 'expiry_date', limit = 30, offset = 0) {
    const params = new URLSearchParams({
      sort_by: sortBy,
      limit: String(limit),
      offset: String(offset),
    });
    if (category) params.append('category', category);

    const result = await this.request<InventoryListResponse>(`/inventory?${params.toString()}`, {
      cacheTtlMs: 3000,
    });

    // Auto-save to offline cache
    if (result.data?.items) {
      import('./offline-cache').then(m => m.offlineCache.saveInventory(result.data!.items)).catch(() => { });
    }

    if (result.data) {
      result.data.offline = Boolean(result.offline || result.data.offline);
      result.data.cache_timestamp = result.data.cache_timestamp ?? result.cache_timestamp ?? null;
    }
    return result;
  }

  async bulkAddInventory(items: Array<{ name: string; quantity: number; unit: string; expiry_date?: string; category?: string }>) {
    const result = await this.request<{
      success: boolean;
      added_count: number;
      updated_count: number;
      items: InventoryItem[];
    }>('/inventory/bulk', {
      method: 'POST',
      body: JSON.stringify({ items }),
    });

    if (result.data) {
      this.invalidateCache(['/inventory', '/recipes/recommendations', '/notifications']);
    }
    return result;
  }

  async updateInventoryItem(
    itemId: string,
    payload: Partial<Pick<InventoryItem, 'name' | 'quantity' | 'unit' | 'expiry_date' | 'category'>>
  ) {
    const result = await this.request<InventoryItem>(`/inventory/${itemId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    if (result.data) {
      this.invalidateCache(['/inventory']);
    }
    return result;
  }

  async deleteInventoryItem(itemId: string) {
    const result = await this.request<{
      success: boolean;
      message: string;
      deleted_item?: InventoryItem;
    }>(`/inventory/${itemId}`, {
      method: 'DELETE',
    });
    if (result.data?.success) {
      this.invalidateCache(['/inventory', '/recipes/recommendations', '/notifications']);
    }
    return result;
  }

  async restoreInventoryItem(payload: {
    name: string;
    quantity: number;
    unit: string;
    expiry_date?: string;
    category?: string;
  }) {
    const result = await this.request<InventoryItem>('/inventory/restore', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (result.data) {
      this.invalidateCache(['/inventory', '/recipes/recommendations', '/notifications']);
    }
    return result;
  }

  async getRecommendations(limit = 5, forceRefresh = false) {
    const fallback = () =>
      this.request<{ recipes: ApiRecipe[]; total_count: number }>(
        `/recipes/recommendations?limit=${limit}&force_refresh=${forceRefresh ? 'true' : 'false'}`,
        {
          cacheTtlMs: forceRefresh ? 0 : 10000,
          timeoutMs: RECOMMENDATIONS_TIMEOUT_MS,
        }
      );

    const createJob = await this.request<{ job_id: string; status: string }>(
      `/recipes/recommendations/jobs?limit=${limit}&force_refresh=${forceRefresh ? 'true' : 'false'}`,
      {
        method: 'POST',
        timeoutMs: 10000,
        skipOfflineQueue: true,
      }
    );

    if (!createJob.data?.job_id) {
      return fallback();
    }

    const jobId = createJob.data.job_id;
    const maxPolls = 20;
    for (let attempt = 0; attempt < maxPolls; attempt += 1) {
      const statusResult = await this.request<{
        job_id: string;
        status: 'pending' | 'processing' | 'completed' | 'failed';
        recipes?: ApiRecipe[];
        total_count?: number;
        error?: string;
      }>(`/recipes/recommendations/jobs/${jobId}`, {
        cacheTtlMs: 0,
        timeoutMs: 10000,
        skipOfflineQueue: true,
      });

      if (!statusResult.data) {
        return { error: statusResult.error || '레시피 추천 상태를 확인하지 못했어요.' };
      }

      if (statusResult.data.status === 'completed') {
        const recipes = statusResult.data.recipes || [];
        return {
          data: {
            recipes,
            total_count: statusResult.data.total_count ?? recipes.length,
          },
        };
      }

      if (statusResult.data.status === 'failed') {
        return { error: statusResult.data.error || '레시피 추천 생성에 실패했어요.' };
      }

      await new Promise(resolve => setTimeout(resolve, 500));
    }

    return { error: '레시피 추천 생성이 지연되고 있어요. 잠시 후 다시 시도해 주세요.' };
  }

  async getRecipe(recipeId: string) {
    return this.request<ApiRecipe>(`/recipes/${recipeId}`, { cacheTtlMs: 15000 });
  }

  async getFavoriteRecipes(limit = 30, offset = 0) {
    const result = await this.request<{ recipes: ApiRecipe[]; total_count: number }>(
      `/recipes/favorites?limit=${limit}&offset=${offset}`,
      { cacheTtlMs: 6000 }
    );

    // Auto-save to offline cache
    if (result.data?.recipes) {
      import('./offline-cache').then(m => m.offlineCache.saveFavorites(result.data!.recipes)).catch(() => { });
    }
    return result;
  }

  async addFavoriteRecipe(recipe: ApiRecipe) {
    const result = await this.request<{ success: boolean; is_favorite: boolean; message: string }>(
      `/recipes/${recipe.id}/favorite`,
      {
        method: 'POST',
        body: JSON.stringify({ recipe }),
      }
    );
    if (result.data?.success) {
      this.invalidateCache(['/recipes/recommendations', '/recipes/favorites', `/recipes/${recipe.id}`]);
    }
    return result;
  }

  async removeFavoriteRecipe(recipeId: string) {
    const result = await this.request<{ success: boolean; is_favorite: boolean; message: string }>(
      `/recipes/${recipeId}/favorite`,
      {
        method: 'DELETE',
      }
    );
    if (result.data?.success) {
      this.invalidateCache(['/recipes/recommendations', '/recipes/favorites', `/recipes/${recipeId}`]);
    }
    return result;
  }

  async completeCooking(recipeId: string, servings = 1) {
    const result = await this.request<{
      success: boolean;
      message: string;
      deducted_items: Array<{
        name: string;
        deducted: number;
        remaining: number;
        deleted: boolean;
      }>;
    }>(`/recipes/${recipeId}/cook`, {
      method: 'POST',
      body: JSON.stringify({ servings }),
    });

    if (result.data?.success) {
      this.invalidateCache([
        '/inventory',
        '/recipes/recommendations',
        `/recipes/${recipeId}`,
        '/recipes/history',
        '/notifications',
      ]);
    }
    return result;
  }

  async getCookingHistory(limit = 20, offset = 0) {
    return this.request<CookingHistoryResponse>(`/recipes/history?limit=${limit}&offset=${offset}`, { cacheTtlMs: 5000 });
  }

  async getCookingHistoryDetail(historyId: string) {
    return this.request<CookingHistoryItem>(`/recipes/history/${historyId}`, { cacheTtlMs: 5000 });
  }

  async getNotifications(limit = 30, offset = 0, onlyUnread = false) {
    return this.request<NotificationListResponse>(
      `/notifications?limit=${limit}&offset=${offset}&only_unread=${onlyUnread ? 'true' : 'false'}`,
      { cacheTtlMs: 3000 }
    );
  }

  async markNotificationsRead(ids: string[] = []) {
    const result = await this.request<{ success: boolean; updated_count: number }>('/notifications/read', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    });
    if (result.data?.success) {
      this.invalidateCache(['/notifications']);
    }
    return result;
  }

  async getShoppingItems(status?: ShoppingItemStatus, limit = 30, offset = 0) {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (status) params.append('status', status);
    const result = await this.request<ShoppingListResponse>(`/shopping?${params.toString()}`, { cacheTtlMs: 3000 });
    if (result.data) {
      import('./offline-cache').then(m => m.offlineCache.saveShopping(result.data!)).catch(() => { });
    }
    return result;
  }

  async addShoppingItems(
    items: Array<{ name: string; quantity: number; unit: string }>,
    options: {
      source?: ShoppingItemSource;
      recipe_id?: string;
      recipe_title?: string;
    } = {}
  ) {
    const result = await this.request<{
      success: boolean;
      added_count: number;
      updated_count: number;
      items: ShoppingItem[];
    }>('/shopping/items', {
      method: 'POST',
      body: JSON.stringify({
        items,
        source: options.source || 'manual',
        recipe_id: options.recipe_id,
        recipe_title: options.recipe_title,
      }),
    });

    if (result.data?.success) {
      this.invalidateCache(['/shopping', '/notifications']);
    }
    return result;
  }

  async addShoppingFromRecipe(
    recipeId: string,
    recipeTitle: string,
    servings: number,
    ingredients: Array<{ name: string; quantity: number; unit: string }>
  ) {
    const result = await this.request<{
      success: boolean;
      added_count: number;
      updated_count: number;
      items: ShoppingItem[];
    }>('/shopping/from-recipe', {
      method: 'POST',
      body: JSON.stringify({
        recipe_id: recipeId,
        recipe_title: recipeTitle,
        servings,
        ingredients,
      }),
    });

    if (result.data?.success) {
      this.invalidateCache(['/shopping', '/notifications']);
    }
    return result;
  }

  async checkoutShoppingItems(ids: string[] = [], addToInventory = true) {
    const result = await this.request<ShoppingCheckoutResponse>('/shopping/checkout', {
      method: 'POST',
      body: JSON.stringify({
        ids,
        add_to_inventory: addToInventory,
      }),
    });

    if (result.data?.success) {
      this.invalidateCache(['/shopping', '/notifications']);
      if (addToInventory) {
        this.invalidateCache(['/inventory', '/recipes/recommendations']);
      }
    }
    return result;
  }

  async updateShoppingItem(
    itemId: string,
    payload: Partial<Pick<ShoppingItem, 'name' | 'quantity' | 'unit' | 'status'>>
  ) {
    const result = await this.request<ShoppingItem>(`/shopping/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
    if (result.data) {
      this.invalidateCache(['/shopping']);
    }
    return result;
  }

  async deleteShoppingItem(itemId: string) {
    const result = await this.request<{
      success: boolean;
      message: string;
      deleted_item?: ShoppingItem;
    }>(`/shopping/${itemId}`, {
      method: 'DELETE',
    });
    if (result.data?.success) {
      this.invalidateCache(['/shopping']);
    }
    return result;
  }

  async getLowStockSuggestions(lookbackDays = 14, thresholdDays = 7) {
    return this.request<LowStockSuggestionResponse>(
      `/shopping/suggestions/low-stock?lookback_days=${lookbackDays}&threshold_days=${thresholdDays}`,
      { cacheTtlMs: 3000 }
    );
  }

  async addLowStockSuggestions(lookbackDays = 14, thresholdDays = 7) {
    const result = await this.request<{
      success: boolean;
      added_count: number;
      updated_count: number;
      items: ShoppingItem[];
    }>(`/shopping/suggestions/low-stock/add?lookback_days=${lookbackDays}&threshold_days=${thresholdDays}`, {
      method: 'POST',
    });
    if (result.data?.success) {
      this.invalidateCache(['/shopping', '/notifications']);
    }
    return result;
  }

  // --- Statistics ---

  async getStatsSummary(period: 'week' | 'month' | 'all' = 'month') {
    return this.request<StatsSummaryResponse>(`/stats/summary?period=${period}`, { cacheTtlMs: 10000 });
  }

  async getPriceHistory(name?: string, days = 90, limit = 100, offset = 0) {
    const params = new URLSearchParams({
      days: String(days),
      limit: String(limit),
      offset: String(offset),
    });
    if (name) params.append('name', name);
    return this.request<PriceHistoryResponse>(`/stats/price-history?${params.toString()}`, { cacheTtlMs: 5000 });
  }

  async exportBackup() {
    return this.request<BackupExportResponse>('/auth/backup/export', { cacheTtlMs: 0 });
  }

  async restoreBackup(payload: Record<string, unknown>, mode: 'merge' | 'replace' = 'merge') {
    return this.request<BackupRestoreResponse>('/auth/backup/restore', {
      method: 'POST',
      body: JSON.stringify({ payload, mode }),
    });
  }

  async bootstrap() {
    return this.request<BootstrapResponse>('/auth/bootstrap', { cacheTtlMs: 0, skipOfflineQueue: true });
  }

  async getSyncStatus(): Promise<SyncStatusResponse> {
    return this.getOfflineSyncStatus();
  }

  async retryPendingSync() {
    return this.retryPendingMutations();
  }

  // --- Barcode ---

  async lookupBarcode(code: string) {
    return this.request<BarcodeResponse>(`/scans/barcode?code=${encodeURIComponent(code)}`, { cacheTtlMs: 30000 });
  }
}

export const api = new ApiClient(API_URL);
export default api;
