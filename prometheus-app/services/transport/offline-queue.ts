import { offlineCache, type PendingMutation } from '../offline-cache';

type RetryDispatch = (action: PendingMutation) => Promise<boolean>;

function computeBackoffMs(attempt: number): number {
  const boundedAttempt = Math.max(1, attempt);
  return Math.min(300000, 5000 * 2 ** (boundedAttempt - 1));
}

export function computeQueueHealth(count: number, oldestAgeMs: number): 'healthy' | 'warning' | 'critical' {
  if (count === 0) return 'healthy';
  if (count >= 100 || oldestAgeMs > 60 * 60 * 1000) return 'critical';
  if (count >= 20 || oldestAgeMs > 10 * 60 * 1000) return 'warning';
  return 'healthy';
}

export async function getOfflineSyncStatus() {
  const online = typeof navigator !== 'undefined' && typeof navigator.onLine === 'boolean' ? navigator.onLine : true;
  try {
    const [queue, lastSync, latestCacheTimestamp] = await Promise.all([
      offlineCache.getPendingMutations(),
      offlineCache.getDatasetSyncCursor(),
      offlineCache.getLatestCacheTimestamp(),
    ]);
    const now = Date.now();
    const oldestPending = queue.reduce<number | null>((min, item) => {
      if (!Number.isFinite(item.created_at)) return min;
      if (min === null) return item.created_at;
      return Math.min(min, item.created_at);
    }, null);
    const oldestPendingAge = oldestPending ? Math.max(0, now - oldestPending) : 0;
    const staleCacheAge = latestCacheTimestamp ? Math.max(0, now - latestCacheTimestamp) : 0;
    return {
      online,
      pending_count: queue.length,
      last_sync_at: lastSync,
      queue_health: computeQueueHealth(queue.length, oldestPendingAge),
      oldest_pending_age_ms: oldestPendingAge,
      stale_cache_age_ms: staleCacheAge,
    };
  } catch {
    return {
      online,
      pending_count: 0,
      last_sync_at: null,
      queue_health: 'healthy' as const,
      oldest_pending_age_ms: 0,
      stale_cache_age_ms: 0,
    };
  }
}

export async function retryPendingMutations(
  dispatch: RetryDispatch,
  limit = 20
): Promise<{ success_count: number; failed_count: number; remaining_count: number }> {
  let successCount = 0;
  let failedCount = 0;

  try {
    const queue = await offlineCache.getPendingMutations();
    const now = Date.now();
    const targets = queue.filter(action => action.next_retry_at <= now).slice(0, limit);

    for (const action of targets) {
      const succeeded = await dispatch(action).catch(() => false);
      if (succeeded) {
        await offlineCache.removePendingMutation(action.id);
        successCount += 1;
        continue;
      }

      failedCount += 1;
      const nextAttempt = action.attempt_count + 1;
      await offlineCache.updatePendingMutation(action.id, {
        attempt_count: nextAttempt,
        next_retry_at: now + computeBackoffMs(nextAttempt),
      });
    }

    if (successCount > 0) {
      await offlineCache.setLastContact();
    }

    const remaining = await offlineCache.getPendingMutations();
    return {
      success_count: successCount,
      failed_count: failedCount,
      remaining_count: remaining.length,
    };
  } catch {
    return {
      success_count: 0,
      failed_count: 0,
      remaining_count: 0,
    };
  }
}
