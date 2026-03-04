import AsyncStorage from '@react-native-async-storage/async-storage';

import { offlineCache } from '../services/offline-cache';

describe('offline cache queue behavior', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    jest.restoreAllMocks();
    await AsyncStorage.clear();
  });

  it('deduplicates pending mutations by idempotency key', async () => {
    await offlineCache.enqueueMutation({
      endpoint: '/shopping/items',
      method: 'POST',
      body: '{"name":"milk"}',
      idempotency_key: 'dup-key',
    });
    await offlineCache.enqueueMutation({
      endpoint: '/shopping/items',
      method: 'POST',
      body: '{"name":"milk2"}',
      idempotency_key: 'dup-key',
    });

    const queue = await offlineCache.getPendingMutations();
    expect(queue).toHaveLength(1);
    expect(queue[0].body).toContain('milk2');
  });
});
