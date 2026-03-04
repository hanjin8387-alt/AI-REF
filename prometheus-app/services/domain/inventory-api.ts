import type { InventoryItem, InventoryListResponse, SortOption } from '../api.types';
import { offlineCache } from '../offline-cache';

import type { ApiTransport } from './types';

export async function getInventoryDomain(
  transport: ApiTransport,
  category?: string,
  sortBy: SortOption = 'expiry_date',
  limit = 30,
  offset = 0
) {
  const params = new URLSearchParams({
    sort_by: sortBy,
    limit: String(limit),
    offset: String(offset),
  });
  if (category) params.append('category', category);

  const result = await transport.request<InventoryListResponse>(`/inventory?${params.toString()}`, {
    cacheTtlMs: 3000,
  });

  if (result.data?.items) {
    offlineCache.saveInventory(result.data.items).catch(() => undefined);
  }

  if (result.data) {
    result.data.offline = Boolean(result.offline || result.data.offline);
    result.data.cache_timestamp = result.data.cache_timestamp ?? result.cache_timestamp ?? null;
  }
  return result;
}

export async function bulkAddInventoryDomain(
  transport: ApiTransport,
  items: Array<{ name: string; quantity: number; unit: string; expiry_date?: string; category?: string }>
) {
  const result = await transport.request<{
    success: boolean;
    added_count: number;
    updated_count: number;
    items: InventoryItem[];
  }>('/inventory/bulk', {
    method: 'POST',
    body: JSON.stringify({ items }),
  });

  if (result.data) {
    transport.invalidateCache(['/inventory', '/recipes/recommendations', '/notifications']);
  }
  return result;
}

export async function updateInventoryItemDomain(
  transport: ApiTransport,
  itemId: string,
  payload: Partial<Pick<InventoryItem, 'name' | 'quantity' | 'unit' | 'expiry_date' | 'category'>>
) {
  const result = await transport.request<InventoryItem>(`/inventory/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  if (result.data) {
    transport.invalidateCache(['/inventory']);
  }
  return result;
}

export async function deleteInventoryItemDomain(transport: ApiTransport, itemId: string) {
  const result = await transport.request<{
    success: boolean;
    message: string;
    deleted_item?: InventoryItem;
  }>(`/inventory/${itemId}`, {
    method: 'DELETE',
  });
  if (result.data?.success) {
    transport.invalidateCache(['/inventory', '/recipes/recommendations', '/notifications']);
  }
  return result;
}

export async function restoreInventoryItemDomain(
  transport: ApiTransport,
  payload: {
    name: string;
    quantity: number;
    unit: string;
    expiry_date?: string;
    category?: string;
  }
) {
  const result = await transport.request<InventoryItem>('/inventory/restore', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (result.data) {
    transport.invalidateCache(['/inventory', '/recipes/recommendations', '/notifications']);
  }
  return result;
}
