import AsyncStorage from '@react-native-async-storage/async-storage';

import { HttpClient } from '../services/http-client';
import { offlineCache } from '../services/offline-cache';

class TestHttpClient extends HttpClient {
  requestPublic<T>(endpoint: string, options: Record<string, unknown>) {
    return this.request<T>(endpoint, options as never);
  }
}

function markInitialized(client: TestHttpClient) {
  (client as unknown as { initialized: boolean; deviceId: string; deviceToken: string }).initialized = true;
  (client as unknown as { initialized: boolean; deviceId: string; deviceToken: string }).deviceId = 'device-1234';
  (client as unknown as { initialized: boolean; deviceId: string; deviceToken: string }).deviceToken = 'device-token-1';
}

describe('http client idempotency and replay', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    jest.restoreAllMocks();
    await AsyncStorage.clear();
  });

  it('adds X-App-ID and idempotency header on mutation request', async () => {
    const client = new TestHttpClient('http://localhost:8000');
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ success: true }),
    }) as never;

    const result = await client.requestPublic('/shopping/items', {
      method: 'POST',
      body: JSON.stringify({ items: [{ name: '우유', quantity: 1, unit: '개' }] }),
      skipInit: true,
    });

    expect(result.error).toBeUndefined();
    const options = (global.fetch as jest.Mock).mock.calls[0][1] as { headers: Record<string, string> };
    expect(options.headers['X-App-ID']).toBe('prometheus-app');
    expect(options.headers['X-Idempotency-Key']).toBeTruthy();
  });

  it('replays pending mutation queue using stored idempotency key', async () => {
    const client = new TestHttpClient('http://localhost:8000');
    markInitialized(client);
    const now = Date.now() - 10;

    jest.spyOn(offlineCache, 'getPendingMutations').mockResolvedValueOnce([
      {
        id: 'pending-1',
        endpoint: '/inventory/bulk',
        method: 'POST',
        body: JSON.stringify({ items: [{ name: '사과', quantity: 2, unit: '개' }] }),
        created_at: now,
        attempt_count: 0,
        next_retry_at: now,
        idempotency_key: 'idem-123',
      },
    ]).mockResolvedValueOnce([]);

    const removeSpy = jest.spyOn(offlineCache, 'removePendingMutation').mockResolvedValue();
    global.fetch = jest.fn().mockResolvedValue({ ok: true }) as never;

    const replay = await client.retryPendingMutations();

    expect(replay.success_count).toBe(1);
    expect(replay.failed_count).toBe(0);
    expect(removeSpy).toHaveBeenCalledWith('pending-1');
    const options = (global.fetch as jest.Mock).mock.calls[0][1] as { headers: Record<string, string> };
    expect(options.headers['X-Idempotency-Key']).toBe('idem-123');
  });
});
