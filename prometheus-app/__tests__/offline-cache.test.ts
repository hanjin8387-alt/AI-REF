import AsyncStorage from '@react-native-async-storage/async-storage';

import { offlineCache } from '../services/offline-cache';

describe('offline-cache', () => {
  beforeEach(async () => {
    await AsyncStorage.clear();
  });

  it('stores inventory with cache timestamp envelope', async () => {
    await offlineCache.saveInventory([{ id: 'inv-1', name: '우유', quantity: 1, unit: '개' }]);

    const inventory = await offlineCache.getInventoryEnvelope();

    expect(inventory?.items).toHaveLength(1);
    expect(inventory?.items[0].name).toBe('우유');
    expect(typeof inventory?.cache_timestamp).toBe('number');
  });

  it('reads legacy inventory array payload', async () => {
    await AsyncStorage.setItem(
      'prometheus_offline_inventory',
      JSON.stringify([{ id: 'legacy-1', name: '달걀', quantity: 6, unit: '개' }])
    );

    const inventory = await offlineCache.getInventoryEnvelope();

    expect(inventory?.items[0].id).toBe('legacy-1');
    expect(inventory?.cache_timestamp).toBeGreaterThan(0);
  });

  it('stores favorites and shopping envelopes', async () => {
    await offlineCache.saveFavorites([
      {
        id: 'r-1',
        title: '토스트',
        description: '아침',
        cooking_time_minutes: 10,
        difficulty: 'easy',
        servings: 1,
        ingredients: [],
        instructions: [],
        priority_score: 1,
        is_favorite: true,
      },
    ]);
    await offlineCache.saveShopping({
      items: [
        {
          id: 's-1',
          name: '식빵',
          quantity: 1,
          unit: '봉',
          status: 'pending',
          source: 'manual',
          added_to_inventory: false,
        },
      ],
      total_count: 1,
      pending_count: 1,
      purchased_count: 0,
      limit: 30,
      offset: 0,
      has_more: false,
    });

    const [favoritesEnvelope, shoppingEnvelope, latestTimestamp] = await Promise.all([
      offlineCache.getFavoritesEnvelope(),
      offlineCache.getShoppingEnvelope(),
      offlineCache.getLatestCacheTimestamp(),
    ]);

    expect(favoritesEnvelope?.recipes).toHaveLength(1);
    expect(shoppingEnvelope?.payload.items).toHaveLength(1);
    expect(latestTimestamp).toBeGreaterThan(0);
  });

  it('coalesces pending mutations by idempotency key', async () => {
    await offlineCache.enqueueMutation({
      endpoint: '/inventory/bulk',
      method: 'POST',
      body: '{"a":1}',
      idempotency_key: 'dup-key',
    });
    await offlineCache.enqueueMutation({
      endpoint: '/inventory/bulk',
      method: 'POST',
      body: '{"a":2}',
      idempotency_key: 'dup-key',
    });

    const queue = await offlineCache.getPendingMutations();

    expect(queue).toHaveLength(1);
    expect(queue[0].body).toBe('{"a":2}');
  });

  it('caps pending queue size to 200', async () => {
    for (let index = 0; index < 205; index += 1) {
      await offlineCache.enqueueMutation({
        endpoint: `/endpoint/${index}`,
        method: 'POST',
        body: JSON.stringify({ index }),
        idempotency_key: `key-${index}`,
      });
    }

    const queue = await offlineCache.getPendingMutations();

    expect(queue).toHaveLength(200);
    expect(queue[0].endpoint).toContain('/endpoint/');
  });

  it('updates pending mutation retry metadata', async () => {
    await offlineCache.enqueueMutation({
      endpoint: '/shopping/items',
      method: 'POST',
      body: '{"name":"우유"}',
      idempotency_key: 'retry-key',
    });
    const [entry] = await offlineCache.getPendingMutations();

    await offlineCache.updatePendingMutation(entry.id, {
      attempt_count: 3,
      next_retry_at: 999999,
    });

    const [updated] = await offlineCache.getPendingMutations();
    expect(updated.attempt_count).toBe(3);
    expect(updated.next_retry_at).toBe(999999);
  });

  it('filters out invalid pending mutation payload', async () => {
    await AsyncStorage.setItem(
      'prometheus_pending_mutations',
      JSON.stringify([
        { endpoint: '/a', method: 'POST', idempotency_key: 'k-1' },
        { endpoint: '/b', method: 'POST' },
      ])
    );

    const queue = await offlineCache.getPendingMutations();

    expect(queue).toHaveLength(1);
    expect(queue[0].endpoint).toBe('/a');
  });
});
