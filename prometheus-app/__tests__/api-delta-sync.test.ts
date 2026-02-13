import type { ApiRecipe, ShoppingListResponse } from '../services/api.types';
import { api } from '../services/api';
import { offlineCache } from '../services/offline-cache';

describe('api delta sync', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.restoreAllMocks();
  });

  it('returns unsynced when last sync timestamp is missing', async () => {
    jest.spyOn(offlineCache, 'getLastSync').mockResolvedValue(null);
    const requestSpy = jest.spyOn(api as unknown as { request: () => Promise<unknown> }, 'request');

    const result = await api.syncOfflineDelta();

    expect(result).toEqual({
      synced: false,
      inventory_delta: 0,
      favorites_delta: 0,
      shopping_delta: 0,
    });
    expect(requestSpy).not.toHaveBeenCalled();
  });

  it('fetches delta payloads and merges them into offline cache', async () => {
    const syncAt = Date.UTC(2026, 1, 13, 0, 0, 0);
    jest.spyOn(offlineCache, 'getLastSync').mockResolvedValue(syncAt);

    const requestSpy = jest.spyOn(api as unknown as { request: (...args: unknown[]) => Promise<unknown> }, 'request');
    requestSpy
      .mockResolvedValueOnce({
        data: {
          items: [
            { id: 'inv-1', name: 'potato', quantity: 3, unit: 'ea' },
            { id: 'inv-2', name: 'onion', quantity: 1, unit: 'ea' },
          ],
          total_count: 2,
          limit: 200,
          offset: 0,
          has_more: false,
        },
      })
      .mockResolvedValueOnce({
        data: {
          recipes: [
            {
              id: 'recipe-1',
              title: 'potato stir-fry',
              description: 'potato stir-fry description',
              cooking_time_minutes: 10,
              difficulty: 'easy',
              servings: 1,
              ingredients: [{ name: 'potato', quantity: 1, unit: 'ea', available: true }],
              instructions: ['stir-fry'],
              priority_score: 0.9,
              is_favorite: true,
            },
          ] as ApiRecipe[],
          total_count: 1,
        },
      })
      .mockResolvedValueOnce({
        data: {
          items: [
            {
              id: 'shop-1',
              name: 'milk',
              quantity: 2,
              unit: 'pack',
              status: 'pending',
              source: 'manual',
              added_to_inventory: false,
            },
          ],
          total_count: 1,
          pending_count: 1,
          purchased_count: 0,
          limit: 200,
          offset: 0,
          has_more: false,
        } as ShoppingListResponse,
      });

    jest.spyOn(offlineCache, 'getInventoryEnvelope').mockResolvedValue({
      items: [{ id: 'inv-1', name: 'potato', quantity: 1, unit: 'ea' }],
      cache_timestamp: syncAt - 1000,
    });
    jest.spyOn(offlineCache, 'getFavoritesEnvelope').mockResolvedValue({
      recipes: [
        {
          id: 'recipe-1',
          title: 'old potato stir-fry',
          description: 'old payload',
          cooking_time_minutes: 8,
          difficulty: 'easy',
          servings: 1,
          ingredients: [{ name: 'potato', quantity: 1, unit: 'ea', available: true }],
          instructions: ['old'],
          priority_score: 0.4,
          is_favorite: true,
        },
      ],
      cache_timestamp: syncAt - 1000,
    });
    jest.spyOn(offlineCache, 'getShoppingEnvelope').mockResolvedValue({
      payload: {
        items: [
          {
            id: 'shop-1',
            name: 'milk',
            quantity: 1,
            unit: 'pack',
            status: 'pending',
            source: 'manual',
            added_to_inventory: false,
          },
          {
            id: 'shop-2',
            name: 'tofu',
            quantity: 1,
            unit: 'block',
            status: 'purchased',
            source: 'manual',
            added_to_inventory: false,
          },
        ],
        total_count: 2,
        pending_count: 1,
        purchased_count: 1,
        limit: 30,
        offset: 0,
        has_more: false,
      },
      cache_timestamp: syncAt - 1000,
    });

    const saveInventorySpy = jest.spyOn(offlineCache, 'saveInventory').mockResolvedValue();
    const saveFavoritesSpy = jest.spyOn(offlineCache, 'saveFavorites').mockResolvedValue();
    const saveShoppingSpy = jest.spyOn(offlineCache, 'saveShopping').mockResolvedValue();
    const setLastSyncSpy = jest.spyOn(offlineCache, 'setLastSync').mockResolvedValue();

    const result = await api.syncOfflineDelta();

    expect(result).toEqual({
      synced: true,
      inventory_delta: 2,
      favorites_delta: 1,
      shopping_delta: 1,
    });

    const endpoints = requestSpy.mock.calls.map(call => String(call[0]));
    expect(endpoints).toHaveLength(3);
    expect(endpoints[0]).toContain('/inventory?');
    expect(endpoints[1]).toContain('/recipes/favorites?');
    expect(endpoints[2]).toContain('/shopping?');
    endpoints.forEach(endpoint => {
      expect(endpoint).toContain('updated_since=');
    });

    expect(saveInventorySpy).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ id: 'inv-1', quantity: 3 }),
        expect.objectContaining({ id: 'inv-2' }),
      ])
    );
    expect(saveFavoritesSpy).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ id: 'recipe-1', title: 'potato stir-fry' })])
    );
    expect(saveShoppingSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        total_count: 2,
        pending_count: 1,
        purchased_count: 1,
      })
    );
    expect(setLastSyncSpy).toHaveBeenCalledTimes(1);
  });

  it('runs delta sync after retry when queue makes progress', async () => {
    jest
      .spyOn(api as unknown as { retryPendingMutations: () => Promise<unknown> }, 'retryPendingMutations')
      .mockResolvedValue({
        success_count: 1,
        failed_count: 0,
        remaining_count: 0,
      });
    const syncSpy = jest.spyOn(api, 'syncOfflineDelta').mockResolvedValue({
      synced: true,
      inventory_delta: 1,
      favorites_delta: 0,
      shopping_delta: 0,
    });

    const result = await api.retryPendingSync();

    expect(result.success_count).toBe(1);
    expect(syncSpy).toHaveBeenCalledTimes(1);
  });

  it('skips delta sync when retry leaves blocked queue', async () => {
    jest
      .spyOn(api as unknown as { retryPendingMutations: () => Promise<unknown> }, 'retryPendingMutations')
      .mockResolvedValue({
        success_count: 0,
        failed_count: 1,
        remaining_count: 1,
      });
    const syncSpy = jest.spyOn(api, 'syncOfflineDelta').mockResolvedValue({
      synced: false,
      inventory_delta: 0,
      favorites_delta: 0,
      shopping_delta: 0,
    });

    const result = await api.retryPendingSync();

    expect(result.failed_count).toBe(1);
    expect(syncSpy).not.toHaveBeenCalled();
  });
});
