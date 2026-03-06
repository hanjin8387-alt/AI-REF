import { beforeEach, describe, expect, it, vi } from 'vitest';

const queue = [
  {
    id: 'pm-1',
    endpoint: '/shopping/items',
    method: 'POST',
    body: '{"items":[]}',
    created_at: 1700000000001,
    attempt_count: 0,
    next_retry_at: 0,
    idempotency_key: 'ikey-1',
  },
];

const offlineCacheMock = {
  getPendingMutations: vi.fn(async () => [...queue]),
  removePendingMutation: vi.fn(async (id: string) => {
    const index = queue.findIndex(item => item.id === id);
    if (index >= 0) queue.splice(index, 1);
  }),
  updatePendingMutation: vi.fn(async () => undefined),
  setLastContact: vi.fn(async () => undefined),
  getDatasetSyncCursor: vi.fn(async () => 1700000000000),
  getLatestCacheTimestamp: vi.fn(async () => null),
};

vi.mock('../services/offline-cache', () => ({
  offlineCache: offlineCacheMock,
}));

describe('OfflineMutationQueue', () => {
  beforeEach(() => {
    queue.splice(0, queue.length, {
      id: 'pm-1',
      endpoint: '/shopping/items',
      method: 'POST',
      body: '{"items":[]}',
      created_at: 1700000000001,
      attempt_count: 0,
      next_retry_at: 0,
      idempotency_key: 'ikey-1',
    });
    vi.clearAllMocks();
  });

  it('replays pending mutations and clears them on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
      }))
    );

    const { retryPendingMutations } = await import('../services/transport/offline-queue');
    const result = await retryPendingMutations(async () => true);

    expect(result).toEqual({
      success_count: 1,
      failed_count: 0,
      remaining_count: 0,
    });
    expect(offlineCacheMock.removePendingMutation).toHaveBeenCalledWith('pm-1');
    expect(offlineCacheMock.setLastContact).toHaveBeenCalled();
  });

  it('reports sync status from the dataset cursor', async () => {
    vi.stubGlobal('navigator', { onLine: true });
    const dateNowSpy = vi.spyOn(Date, 'now').mockReturnValue(1700000600000);
    queue[0].created_at = 1699999999999;
    try {
      const { getOfflineSyncStatus } = await import('../services/transport/offline-queue');
      const result = await getOfflineSyncStatus();

      expect(result).toEqual({
        online: true,
        pending_count: 1,
        last_sync_at: 1700000000000,
        queue_health: 'warning',
        oldest_pending_age_ms: 600001,
        stale_cache_age_ms: 0,
      });
    } finally {
      dateNowSpy.mockRestore();
    }
  });
});
