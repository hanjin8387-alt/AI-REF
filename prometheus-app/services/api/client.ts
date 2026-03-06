import type {
  ApiRecipe,
  BarcodeResponse,
  InventoryItem,
  NotificationListResponse,
  PriceHistoryResponse,
  ScanResultPayload,
  ScanSourceType,
  ShoppingItem,
  ShoppingItemSource,
  ShoppingItemStatus,
  StatsSummaryResponse,
  SyncStatusResponse,
} from '../api.types';
import { getApiBaseUrl } from '../config/runtime';
import { HttpClient } from '../http-client';
import { exportBackupDomain, restoreBackupDomain } from './backup';
import { bootstrapDomain } from './bootstrap';
import {
  bulkAddInventoryDomain,
  deleteInventoryItemDomain,
  getInventoryDomain,
  restoreInventoryItemDomain,
  updateInventoryItemDomain,
} from './inventory';
import { getNotificationsApi, markNotificationsReadApi } from './notifications';
import {
  addFavoriteRecipeDomain,
  completeCookingDomain,
  getCookingHistoryDetailDomain,
  getCookingHistoryDomain,
  getFavoriteRecipesDomain,
  getRecipeDomain,
  getRecommendationsDomain,
  removeFavoriteRecipeDomain,
} from './recipes';
import { getScanResultApi, lookupBarcodeApi, uploadScanApi } from './scans';
import {
  addLowStockSuggestionsDomain,
  addShoppingFromRecipeDomain,
  addShoppingItemsDomain,
  checkoutShoppingItemsDomain,
  deleteShoppingItemDomain,
  getLowStockSuggestionsDomain,
  getShoppingItemsDomain,
  updateShoppingItemDomain,
} from './shopping';
import { getPriceHistoryApi, getStatsSummaryApi } from './stats';
import { getSyncStatusApi, retryPendingSyncApi, syncOfflineDeltaApi } from './sync';

const API_URL = getApiBaseUrl();

export class ApiClient extends HttpClient {
  constructor(baseUrl: string) {
    super(baseUrl);
  }

  async uploadScan(imageUri: string, sourceType: ScanSourceType = 'camera') {
    return uploadScanApi(this, imageUri, sourceType);
  }

  async getScanResult(scanId: string) {
    return getScanResultApi(this, scanId);
  }

  async getInventory(category?: string, sortBy: 'expiry_date' | 'name' | 'created_at' = 'expiry_date', limit = 30, offset = 0) {
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
    return getNotificationsApi(this, limit, offset, onlyUnread);
  }

  async markNotificationsRead(ids: string[] = []) {
    return markNotificationsReadApi(this, ids);
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
    return getStatsSummaryApi(this, period) as Promise<{ data?: StatsSummaryResponse; error?: string }>;
  }

  async getPriceHistory(name?: string, days = 90, limit = 100, offset = 0) {
    return getPriceHistoryApi(this, name, days, limit, offset) as Promise<{ data?: PriceHistoryResponse; error?: string }>;
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

  async syncOfflineDelta() {
    return syncOfflineDeltaApi(this);
  }

  async getSyncStatus(): Promise<SyncStatusResponse> {
    return getSyncStatusApi(this);
  }

  async retryPendingSync() {
    return retryPendingSyncApi(this);
  }

  async lookupBarcode(code: string) {
    return lookupBarcodeApi(this, code) as Promise<{ data?: BarcodeResponse; error?: string }>;
  }
}

export const api = new ApiClient(API_URL);
export default api;
