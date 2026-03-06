import type {
  ApiRecipe,
  InventoryListResponse,
  ShoppingItem,
  ShoppingListResponse,
  SyncStatusResponse,
} from '../api.types';
import { offlineCache } from '../offline-cache';
import type { HttpClient } from '../http-client';

function mergeById<T extends { id: string }>(base: T[], delta: T[]): T[] {
  const merged = new Map<string, T>();
  for (const item of base) {
    if (item?.id) merged.set(item.id, item);
  }
  for (const item of delta) {
    if (item?.id) merged.set(item.id, item);
  }
  return Array.from(merged.values());
}

function mergeRecipesById(base: ApiRecipe[], delta: ApiRecipe[]): ApiRecipe[] {
  const merged = new Map<string, ApiRecipe>();
  for (const recipe of base) {
    if (recipe?.id) merged.set(recipe.id, recipe);
  }
  for (const recipe of delta) {
    if (recipe?.id) merged.set(recipe.id, recipe);
  }
  return Array.from(merged.values());
}

function toShoppingList(items: ShoppingItem[]): ShoppingListResponse {
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

export async function syncOfflineDeltaApi(transport: HttpClient): Promise<{
  synced: boolean;
  inventory_delta: number;
  favorites_delta: number;
  shopping_delta: number;
}> {
  const lastSync = await offlineCache.getDatasetSyncCursor();
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
    transport.request<InventoryListResponse>(`/inventory?sort_by=updated_at&limit=200&offset=0&updated_since=${updatedSince}`, {
      cacheTtlMs: 0,
      disableOfflineFallback: true,
      skipOfflineQueue: true,
      skipRequestDedup: true,
    }),
    transport.request<{ recipes: ApiRecipe[]; total_count: number }>(
      `/recipes/favorites?limit=200&offset=0&updated_since=${updatedSince}`,
      {
        cacheTtlMs: 0,
        disableOfflineFallback: true,
        skipOfflineQueue: true,
        skipRequestDedup: true,
      }
    ),
    transport.request<ShoppingListResponse>(`/shopping?limit=200&offset=0&updated_since=${updatedSince}`, {
      cacheTtlMs: 0,
      disableOfflineFallback: true,
      skipOfflineQueue: true,
      skipRequestDedup: true,
    }),
  ]);

  let successCount = 0;
  let inventoryDelta = 0;
  let favoritesDelta = 0;
  let shoppingDelta = 0;

  if (inventoryResult.data) {
    successCount += 1;
    const existing = await offlineCache.getInventoryEnvelope();
    const merged = mergeById(existing?.items || [], inventoryResult.data.items || []);
    inventoryDelta = inventoryResult.data.items?.length || 0;
    await offlineCache.saveInventory(merged);
  }

  if (favoritesResult.data) {
    successCount += 1;
    const existing = await offlineCache.getFavoritesEnvelope();
    const merged = mergeRecipesById(existing?.recipes || [], favoritesResult.data.recipes || []);
    favoritesDelta = favoritesResult.data.recipes?.length || 0;
    await offlineCache.saveFavorites(merged);
  }

  if (shoppingResult.data) {
    successCount += 1;
    const existing = await offlineCache.getShoppingEnvelope();
    const mergedItems = mergeById(existing?.payload.items || [], shoppingResult.data.items || []);
    shoppingDelta = shoppingResult.data.items?.length || 0;
    await offlineCache.saveShopping(toShoppingList(mergedItems));
  }

  if (successCount > 0) {
    await offlineCache.setDatasetSyncCursor();
  }

  return {
    synced: successCount > 0,
    inventory_delta: inventoryDelta,
    favorites_delta: favoritesDelta,
    shopping_delta: shoppingDelta,
  };
}

export async function getSyncStatusApi(transport: HttpClient): Promise<SyncStatusResponse> {
  return transport.getOfflineSyncStatus();
}

export async function retryPendingSyncApi(transport: HttpClient) {
  const retryResult = await transport.retryPendingMutations();
  if (retryResult.success_count > 0 || retryResult.remaining_count === 0) {
    await syncOfflineDeltaApi(transport).catch(() => undefined);
  }
  return retryResult;
}
