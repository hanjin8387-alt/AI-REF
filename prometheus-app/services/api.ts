import { Platform } from 'react-native';

import type {
  ApiRecipe,
  BarcodeResponse,
  InventoryItem,
  InventoryListResponse,
  NotificationListResponse,
  PriceHistoryResponse,
  ScanResultPayload,
  ScanSourceType,
  ShoppingItem,
  ShoppingItemSource,
  ShoppingItemStatus,
  ShoppingListResponse,
  SortOption,
  StatsSummaryResponse,
  SyncStatusResponse,
} from './api.types';
import { getApiBaseUrl } from './config/runtime';
import {
  bootstrapDomain,
  exportBackupDomain,
  restoreBackupDomain,
} from './domain/auth-api';
import {
  bulkAddInventoryDomain,
  deleteInventoryItemDomain,
  getInventoryDomain,
  restoreInventoryItemDomain,
  updateInventoryItemDomain,
} from './domain/inventory-api';
import {
  addFavoriteRecipeDomain,
  completeCookingDomain,
  getCookingHistoryDetailDomain,
  getCookingHistoryDomain,
  getFavoriteRecipesDomain,
  getRecipeDomain,
  getRecommendationsDomain,
  removeFavoriteRecipeDomain,
} from './domain/recipes-api';
import {
  addLowStockSuggestionsDomain,
  addShoppingFromRecipeDomain,
  addShoppingItemsDomain,
  checkoutShoppingItemsDomain,
  deleteShoppingItemDomain,
  getLowStockSuggestionsDomain,
  getShoppingItemsDomain,
  updateShoppingItemDomain,
} from './domain/shopping-api';
import { HttpClient } from './http-client';
import { offlineCache } from './offline-cache';

export type {
  ApiRecipe,
  BackupExportResponse,
  BackupRestoreResponse,
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

const API_URL = getApiBaseUrl();
const DEFAULT_SCAN_EXTENSION = 'jpg';
const SCAN_UPLOAD_TIMEOUT_MS = 120000;
const SCAN_RESULT_TIMEOUT_MS = 30000;

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
    return getInventoryDomain(this, category, sortBy, limit, offset);
  }

  async bulkAddInventory(items: Array<{ name: string; quantity: number; unit: string; expiry_date?: string; category?: string }>) {
    return bulkAddInventoryDomain(this, items);
  }

  async updateInventoryItem(
    itemId: string,
    payload: Partial<Pick<InventoryItem, 'name' | 'quantity' | 'unit' | 'expiry_date' | 'category'>>
  ) {
    return updateInventoryItemDomain(this, itemId, payload);
  }

  async deleteInventoryItem(itemId: string) {
    return deleteInventoryItemDomain(this, itemId);
  }

  async restoreInventoryItem(payload: {
    name: string;
    quantity: number;
    unit: string;
    expiry_date?: string;
    category?: string;
  }) {
    return restoreInventoryItemDomain(this, payload);
  }

  async getRecommendations(limit = 5, forceRefresh = false) {
    return getRecommendationsDomain(this, limit, forceRefresh);
  }

  async getRecipe(recipeId: string) {
    return getRecipeDomain(this, recipeId);
  }

  async getFavoriteRecipes(limit = 30, offset = 0) {
    return getFavoriteRecipesDomain(this, limit, offset);
  }

  async addFavoriteRecipe(recipe: ApiRecipe) {
    return addFavoriteRecipeDomain(this, recipe);
  }

  async removeFavoriteRecipe(recipeId: string) {
    return removeFavoriteRecipeDomain(this, recipeId);
  }

  async completeCooking(recipeId: string, servings = 1) {
    return completeCookingDomain(this, recipeId, servings);
  }

  async getCookingHistory(limit = 20, offset = 0) {
    return getCookingHistoryDomain(this, limit, offset);
  }

  async getCookingHistoryDetail(historyId: string) {
    return getCookingHistoryDetailDomain(this, historyId);
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
    return getShoppingItemsDomain(this, status, limit, offset);
  }

  async addShoppingItems(
    items: Array<{ name: string; quantity: number; unit: string }>,
    options: {
      source?: ShoppingItemSource;
      recipe_id?: string;
      recipe_title?: string;
    } = {}
  ) {
    return addShoppingItemsDomain(this, items, options);
  }

  async addShoppingFromRecipe(
    recipeId: string,
    recipeTitle: string,
    servings: number,
    ingredients: Array<{ name: string; quantity: number; unit: string }>
  ) {
    return addShoppingFromRecipeDomain(this, recipeId, recipeTitle, servings, ingredients);
  }

  async checkoutShoppingItems(ids: string[] = [], addToInventory = true) {
    return checkoutShoppingItemsDomain(this, ids, addToInventory);
  }

  async updateShoppingItem(
    itemId: string,
    payload: Partial<Pick<ShoppingItem, 'name' | 'quantity' | 'unit' | 'status'>>
  ) {
    return updateShoppingItemDomain(this, itemId, payload);
  }

  async deleteShoppingItem(itemId: string) {
    return deleteShoppingItemDomain(this, itemId);
  }

  async getLowStockSuggestions(lookbackDays = 14, thresholdDays = 7) {
    return getLowStockSuggestionsDomain(this, lookbackDays, thresholdDays);
  }

  async addLowStockSuggestions(lookbackDays = 14, thresholdDays = 7) {
    return addLowStockSuggestionsDomain(this, lookbackDays, thresholdDays);
  }

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
    return exportBackupDomain(this);
  }

  async restoreBackup(payload: Record<string, unknown>, mode: 'merge' | 'replace' = 'merge') {
    return restoreBackupDomain(this, payload, mode);
  }

  async bootstrap(options: { timeoutMs?: number } = {}) {
    return bootstrapDomain(this, options);
  }

  private mergeById<T extends { id: string }>(base: T[], delta: T[]): T[] {
    const merged = new Map<string, T>();
    for (const item of base) {
      if (item?.id) merged.set(item.id, item);
    }
    for (const item of delta) {
      if (item?.id) merged.set(item.id, item);
    }
    return Array.from(merged.values());
  }

  private mergeRecipesById(base: ApiRecipe[], delta: ApiRecipe[]): ApiRecipe[] {
    const merged = new Map<string, ApiRecipe>();
    for (const recipe of base) {
      if (recipe?.id) merged.set(recipe.id, recipe);
    }
    for (const recipe of delta) {
      if (recipe?.id) merged.set(recipe.id, recipe);
    }
    return Array.from(merged.values());
  }

  private toShoppingList(items: ShoppingItem[]): ShoppingListResponse {
    const pendingCount = items.filter(item => item.status === 'pending').length;
    const purchasedCount = items.filter(item => item.status === 'purchased').length;
    return {
      items,
      total_count: items.length,
      pending_count: pendingCount,
      purchased_count: purchasedCount,
      limit: items.length || 30,
      offset: 0,
      has_more: false,
    };
  }

  async syncOfflineDelta(): Promise<{
    synced: boolean;
    inventory_delta: number;
    favorites_delta: number;
    shopping_delta: number;
  }> {
    const lastSync = await offlineCache.getLastSync();
    if (!lastSync) {
      return {
        synced: false,
        inventory_delta: 0,
        favorites_delta: 0,
        shopping_delta: 0,
      };
    }

    const updatedSince = encodeURIComponent(new Date(lastSync).toISOString());
    const [inventoryResult, favoritesResult, shoppingResult] = await Promise.all([
      this.request<InventoryListResponse>(
        `/inventory?sort_by=updated_at&limit=200&offset=0&updated_since=${updatedSince}`,
        {
          cacheTtlMs: 0,
          disableOfflineFallback: true,
          skipOfflineQueue: true,
          skipRequestDedup: true,
        }
      ),
      this.request<{ recipes: ApiRecipe[]; total_count: number }>(
        `/recipes/favorites?limit=200&offset=0&updated_since=${updatedSince}`,
        {
          cacheTtlMs: 0,
          disableOfflineFallback: true,
          skipOfflineQueue: true,
          skipRequestDedup: true,
        }
      ),
      this.request<ShoppingListResponse>(
        `/shopping?limit=200&offset=0&updated_since=${updatedSince}`,
        {
          cacheTtlMs: 0,
          disableOfflineFallback: true,
          skipOfflineQueue: true,
          skipRequestDedup: true,
        }
      ),
    ]);

    let successCount = 0;
    let inventoryDelta = 0;
    let favoritesDelta = 0;
    let shoppingDelta = 0;

    if (inventoryResult.data) {
      successCount += 1;
      const existing = await offlineCache.getInventoryEnvelope();
      const merged = this.mergeById(existing?.items || [], inventoryResult.data.items || []);
      inventoryDelta = inventoryResult.data.items?.length || 0;
      await offlineCache.saveInventory(merged);
    }

    if (favoritesResult.data) {
      successCount += 1;
      const existing = await offlineCache.getFavoritesEnvelope();
      const merged = this.mergeRecipesById(existing?.recipes || [], favoritesResult.data.recipes || []);
      favoritesDelta = favoritesResult.data.recipes?.length || 0;
      await offlineCache.saveFavorites(merged);
    }

    if (shoppingResult.data) {
      successCount += 1;
      const existing = await offlineCache.getShoppingEnvelope();
      const mergedItems = this.mergeById(existing?.payload.items || [], shoppingResult.data.items || []);
      shoppingDelta = shoppingResult.data.items?.length || 0;
      await offlineCache.saveShopping(this.toShoppingList(mergedItems));
    }

    if (successCount > 0) {
      await offlineCache.setLastSync();
    }

    return {
      synced: successCount > 0,
      inventory_delta: inventoryDelta,
      favorites_delta: favoritesDelta,
      shopping_delta: shoppingDelta,
    };
  }

  async getSyncStatus(): Promise<SyncStatusResponse> {
    return this.getOfflineSyncStatus();
  }

  async retryPendingSync() {
    const retryResult = await this.retryPendingMutations();
    if (retryResult.success_count > 0 || retryResult.remaining_count === 0) {
      await this.syncOfflineDelta().catch(() => undefined);
    }
    return retryResult;
  }

  async lookupBarcode(code: string) {
    return this.request<BarcodeResponse>(`/scans/barcode?code=${encodeURIComponent(code)}`, { cacheTtlMs: 30000 });
  }
}

export const api = new ApiClient(API_URL);
export default api;
