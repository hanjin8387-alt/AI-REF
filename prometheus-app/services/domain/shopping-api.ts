import type {
  LowStockSuggestionResponse,
  ShoppingCheckoutResponse,
  ShoppingItem,
  ShoppingItemSource,
  ShoppingItemStatus,
  ShoppingListResponse,
} from '../api.types';
import { offlineCache } from '../offline-cache';

import type { ApiTransport } from './types';

export async function getShoppingItemsDomain(
  transport: ApiTransport,
  status?: ShoppingItemStatus,
  limit = 30,
  offset = 0
) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (status) params.append('status', status);
  const result = await transport.request<ShoppingListResponse>(`/shopping?${params.toString()}`, { cacheTtlMs: 3000 });
  if (result.data) {
    offlineCache.saveShopping(result.data).catch(() => undefined);
  }
  return result;
}

export async function addShoppingItemsDomain(
  transport: ApiTransport,
  items: Array<{ name: string; quantity: number; unit: string }>,
  options: {
    source?: ShoppingItemSource;
    recipe_id?: string;
    recipe_title?: string;
  } = {}
) {
  const result = await transport.request<{
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
    transport.invalidateCache(['/shopping', '/notifications']);
  }
  return result;
}

export async function addShoppingFromRecipeDomain(
  transport: ApiTransport,
  recipeId: string,
  recipeTitle: string,
  servings: number,
  ingredients: Array<{ name: string; quantity: number; unit: string }>
) {
  const result = await transport.request<{
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
    transport.invalidateCache(['/shopping', '/notifications']);
  }
  return result;
}

export async function checkoutShoppingItemsDomain(
  transport: ApiTransport,
  ids: string[] = [],
  addToInventory = true
) {
  const result = await transport.request<ShoppingCheckoutResponse>('/shopping/checkout', {
    method: 'POST',
    body: JSON.stringify({
      ids,
      add_to_inventory: addToInventory,
    }),
  });

  if (result.data?.success) {
    transport.invalidateCache(['/shopping', '/notifications']);
    if (addToInventory) {
      transport.invalidateCache(['/inventory', '/recipes/recommendations']);
    }
  }
  return result;
}

export async function updateShoppingItemDomain(
  transport: ApiTransport,
  itemId: string,
  payload: Partial<Pick<ShoppingItem, 'name' | 'quantity' | 'unit' | 'status'>>
) {
  const result = await transport.request<ShoppingItem>(`/shopping/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  if (result.data) {
    transport.invalidateCache(['/shopping']);
  }
  return result;
}

export async function deleteShoppingItemDomain(transport: ApiTransport, itemId: string) {
  const result = await transport.request<{
    success: boolean;
    message: string;
    deleted_item?: ShoppingItem;
  }>(`/shopping/${itemId}`, {
    method: 'DELETE',
  });
  if (result.data?.success) {
    transport.invalidateCache(['/shopping']);
  }
  return result;
}

export async function getLowStockSuggestionsDomain(transport: ApiTransport, lookbackDays = 14, thresholdDays = 7) {
  return transport.request<LowStockSuggestionResponse>(
    `/shopping/suggestions/low-stock?lookback_days=${lookbackDays}&threshold_days=${thresholdDays}`,
    { cacheTtlMs: 3000 }
  );
}

export async function addLowStockSuggestionsDomain(transport: ApiTransport, lookbackDays = 14, thresholdDays = 7) {
  const result = await transport.request<{
    success: boolean;
    added_count: number;
    updated_count: number;
    items: ShoppingItem[];
  }>(`/shopping/suggestions/low-stock/add?lookback_days=${lookbackDays}&threshold_days=${thresholdDays}`, {
    method: 'POST',
  });
  if (result.data?.success) {
    transport.invalidateCache(['/shopping', '/notifications']);
  }
  return result;
}
