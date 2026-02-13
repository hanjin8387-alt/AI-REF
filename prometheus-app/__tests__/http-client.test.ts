import AsyncStorage from '@react-native-async-storage/async-storage';

import type { InventoryListResponse } from '../services/api.types';
import { HttpClient } from '../services/http-client';
import { offlineCache } from '../services/offline-cache';

class TestHttpClient extends HttpClient {
  public requestPublic<T>(endpoint: string, options: Record<string, unknown>) {
    return this.request<T>(endpoint, options as never);
  }
}

function markInitialized(client: TestHttpClient) {
  (client as unknown as { initialized: boolean; deviceId: string }).initialized = true;
  (client as unknown as { initialized: boolean; deviceId: string }).deviceId = 'device-1234';
}

describe('http-client', () => {
  const originalNavigator = global.navigator;
  const setNavigator = (value: unknown) => {
    Object.defineProperty(global, 'navigator', {
      value,
      writable: true,
      configurable: true,
    });
  };

  beforeEach(async () => {
    await AsyncStorage.clear();
    jest.clearAllMocks();
    jest.restoreAllMocks();
  });

  afterAll(() => {
    setNavigator(originalNavigator);
  });

  it('returns timeout message on AbortError', async () => {
    const client = new TestHttpClient('https://example.com');
    global.fetch = jest.fn().mockRejectedValue(Object.assign(new Error('aborted'), { name: 'AbortError' })) as never;

    const result = await client.requestPublic('/inventory', {
      method: 'GET',
      skipInit: true,
      disableOfflineFallback: true,
      timeoutMs: 1,
    });

    expect(result.error).toContain('요청 시간이 초과되었어요');
  });

  it('queues mutation when network fails', async () => {
    const client = new TestHttpClient('https://example.com');
    const enqueueSpy = jest.spyOn(offlineCache, 'enqueueMutation').mockResolvedValue();
    global.fetch = jest.fn().mockRejectedValue(new Error('Failed to fetch')) as never;

    const result = await client.requestPublic('/shopping/items', {
      method: 'POST',
      body: JSON.stringify({ items: [{ name: '우유', quantity: 1, unit: '개' }] }),
      skipInit: true,
    });

    expect(result.error).toContain('임시 보관');
    expect(enqueueSpy).toHaveBeenCalledTimes(1);
    expect(enqueueSpy.mock.calls[0][0].endpoint).toBe('/shopping/items');
    expect(enqueueSpy.mock.calls[0][0].idempotency_key).toBeTruthy();
  });

  it('retries pending queue and applies backoff on failure', async () => {
    const client = new TestHttpClient('https://example.com');
    markInitialized(client);
    const oldRetryAt = Date.now() - 1;
    jest.spyOn(offlineCache, 'getPendingMutations').mockResolvedValue([
      {
        id: 'pm-retry-1',
        endpoint: '/inventory/bulk',
        method: 'POST',
        body: JSON.stringify({ items: [] }),
        created_at: oldRetryAt,
        attempt_count: 0,
        next_retry_at: oldRetryAt,
        idempotency_key: 'retry-1',
      },
    ]);
    const updateSpy = jest.spyOn(offlineCache, 'updatePendingMutation').mockResolvedValue();

    global.fetch = jest.fn().mockRejectedValue(new Error('Network request failed')) as never;

    const result = await client.retryPendingMutations(10);

    expect(result.failed_count).toBe(1);
    expect(updateSpy).toHaveBeenCalledTimes(1);
    expect(updateSpy.mock.calls[0][0]).toBe('pm-retry-1');
    expect(updateSpy.mock.calls[0][1].attempt_count).toBe(1);
  });

  it('sends idempotency header when retrying pending queue', async () => {
    const client = new TestHttpClient('https://example.com');
    markInitialized(client);
    jest
      .spyOn(offlineCache, 'getPendingMutations')
      .mockResolvedValueOnce([
        {
          id: 'pm-retry-header',
          endpoint: '/inventory/bulk',
          method: 'POST',
          body: JSON.stringify({ items: [] }),
          created_at: Date.now() - 1,
          attempt_count: 0,
          next_retry_at: Date.now() - 1,
          idempotency_key: 'retry-key-header',
        },
      ])
      .mockResolvedValueOnce([]);
    jest.spyOn(offlineCache, 'removePendingMutation').mockResolvedValue();

    global.fetch = jest.fn().mockResolvedValue({ ok: true }) as never;

    await client.retryPendingMutations(10);

    const fetchArgs = (global.fetch as jest.Mock).mock.calls[0][1] as { headers?: Record<string, string> };
    expect(fetchArgs.headers?.['X-Idempotency-Key']).toBe('retry-key-header');
  });

  it('returns offline inventory fallback with cache timestamp', async () => {
    const client = new TestHttpClient('https://example.com');
    jest.spyOn(offlineCache, 'getInventoryEnvelope').mockResolvedValue({
      items: [{ id: 'inv-1', name: '감자', quantity: 3, unit: '개' }],
      cache_timestamp: Date.now(),
    });
    global.fetch = jest.fn().mockRejectedValue(new Error('Failed to fetch')) as never;

    const result = await client.requestPublic<InventoryListResponse>('/inventory?sort_by=expiry_date', {
      method: 'GET',
      skipInit: true,
    });

    expect(result.offline).toBe(true);
    expect(result.cache_timestamp).toBeGreaterThan(0);
    expect(result.data?.items).toHaveLength(1);
    expect(result.data?.offline).toBe(true);
  });

  it('includes idempotency key header on mutation request', async () => {
    const client = new TestHttpClient('https://example.com');
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ success: true }),
    }) as never;

    await client.requestPublic('/shopping/items', {
      method: 'POST',
      body: JSON.stringify({ name: '우유' }),
      skipInit: true,
    });

    const fetchArgs = (global.fetch as jest.Mock).mock.calls[0][1] as { headers?: Record<string, string> };
    expect(fetchArgs.headers?.['X-Idempotency-Key']).toBeDefined();
  });

  it('deduplicates concurrent GET requests with the same endpoint', async () => {
    const client = new TestHttpClient('https://example.com');

    let resolveFetch: ((value: unknown) => void) | null = null;
    global.fetch = jest.fn().mockImplementation(
      () =>
        new Promise(resolve => {
          resolveFetch = resolve;
        })
    ) as never;

    const first = client.requestPublic('/inventory?limit=30', {
      method: 'GET',
      skipInit: true,
      disableOfflineFallback: true,
    });
    const second = client.requestPublic('/inventory?limit=30', {
      method: 'GET',
      skipInit: true,
      disableOfflineFallback: true,
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);

    resolveFetch?.({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ items: [], total_count: 0, limit: 30, offset: 0, has_more: false }),
    });

    const [firstResult, secondResult] = await Promise.all([first, second]);
    expect(firstResult.data).toBeDefined();
    expect(secondResult.data).toBeDefined();
  });

  it('can bypass inflight deduplication when requested', async () => {
    const client = new TestHttpClient('https://example.com');
    global.fetch = jest
      .fn()
      .mockResolvedValue({
        ok: true,
        headers: { get: () => 'application/json' },
        json: async () => ({ items: [], total_count: 0, limit: 30, offset: 0, has_more: false }),
      }) as never;

    await Promise.all([
      client.requestPublic('/inventory?limit=30', {
        method: 'GET',
        skipInit: true,
        disableOfflineFallback: true,
        skipRequestDedup: true,
      }),
      client.requestPublic('/inventory?limit=30', {
        method: 'GET',
        skipInit: true,
        disableOfflineFallback: true,
        skipRequestDedup: true,
      }),
    ]);

    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it('computes healthy sync status when queue is empty', async () => {
    const client = new TestHttpClient('https://example.com');
    setNavigator({ onLine: true });

    const status = await client.getOfflineSyncStatus();

    expect(status.pending_count).toBe(0);
    expect(status.queue_health).toBe('healthy');
    expect(status.oldest_pending_age_ms).toBe(0);
  });

  it('computes warning sync status for stale pending queue', async () => {
    const oldTimestamp = Date.now() - 20 * 60 * 1000;
    jest.spyOn(offlineCache, 'getPendingMutations').mockResolvedValue([
      {
        id: 'pm-1',
        endpoint: '/shopping/items',
        method: 'POST',
        body: '{}',
        created_at: oldTimestamp,
        attempt_count: 1,
        next_retry_at: oldTimestamp,
        idempotency_key: 'old-key',
      },
    ]);

    const client = new TestHttpClient('https://example.com');
    setNavigator({ onLine: true });

    const status = await client.getOfflineSyncStatus();

    expect(status.pending_count).toBe(1);
    expect(status.queue_health).toBe('warning');
    expect(status.oldest_pending_age_ms).toBeGreaterThan(0);
  });
});
