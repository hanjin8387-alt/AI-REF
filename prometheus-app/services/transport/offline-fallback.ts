import { offlineCache } from '../offline-cache';
import type { ApiRecipe, InventoryListResponse, ShoppingListResponse } from '../api.types';

export async function loadOfflineFallback<T>(
  endpoint: string,
  isFresh: (timestamp: number | null | undefined) => boolean
): Promise<{ data: T; cacheTimestamp: number | null } | null> {
  if (endpoint.startsWith('/inventory')) {
    const inventoryEnvelope = await offlineCache.getInventoryEnvelope();
    if (!inventoryEnvelope || !isFresh(inventoryEnvelope.cache_timestamp)) return null;
    return {
      data: {
        items: inventoryEnvelope.items,
        total_count: inventoryEnvelope.items.length,
        limit: inventoryEnvelope.items.length || 30,
        offset: 0,
        has_more: false,
        offline: true,
        cache_timestamp: inventoryEnvelope.cache_timestamp,
      } as T,
      cacheTimestamp: inventoryEnvelope.cache_timestamp,
    };
  }

  if (endpoint.startsWith('/recipes/favorites')) {
    const favoritesEnvelope = await offlineCache.getFavoritesEnvelope();
    if (!favoritesEnvelope || !isFresh(favoritesEnvelope.cache_timestamp)) return null;
    return {
      data: {
        recipes: favoritesEnvelope.recipes as ApiRecipe[],
        total_count: favoritesEnvelope.recipes.length,
      } as T,
      cacheTimestamp: favoritesEnvelope.cache_timestamp,
    };
  }

  if (endpoint.startsWith('/shopping')) {
    const shoppingEnvelope = await offlineCache.getShoppingEnvelope();
    if (!shoppingEnvelope || !isFresh(shoppingEnvelope.cache_timestamp)) return null;
    const payload = shoppingEnvelope.payload as ShoppingListResponse;
    return {
      data: {
        ...payload,
        offline: true,
        cache_timestamp: shoppingEnvelope.cache_timestamp,
      } as T,
      cacheTimestamp: shoppingEnvelope.cache_timestamp,
    };
  }

  return null;
}
