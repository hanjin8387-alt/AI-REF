import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { offlineCache } from './offline-cache';
import { logHttpPerf } from './perf-logger';
import { parseJsonWithWorker } from '../utils/json-worker';
import { loadOrCreateDeviceId } from './device-id-storage';
import { loadDeviceToken, saveDeviceToken } from './device-token-storage';

const APP_TOKEN =
  process.env.EXPO_PUBLIC_APP_TOKEN ||
  (Constants.expoConfig?.extra?.appToken as string | undefined) ||
  '';
const REQUEST_TIMEOUT_MS = 20000;
const MAX_CLIENT_CACHE_ENTRIES = 200;
const OFFLINE_CACHE_TTL_MS = 24 * 60 * 60 * 1000;

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  offline?: boolean;
  cache_timestamp?: number | null;
}

type RequestOptions = RequestInit & {
  cacheTtlMs?: number;
  skipInit?: boolean;
  timeoutMs?: number;
  disableOfflineFallback?: boolean;
  skipOfflineQueue?: boolean;
  idempotencyKey?: string;
  skipRequestDedup?: boolean;
};

type CacheEntry = {
  expiresAt: number;
  data: unknown;
};

export type PendingSyncAction = {
  id: string;
  endpoint: string;
  method: string;
  body?: string;
  created_at: number;
  attempt_count: number;
  next_retry_at: number;
  idempotency_key: string;
};

export class HttpClient {
  private readonly baseUrl: string;
  private deviceId: string | null = null;
  private deviceToken: string | null = null;
  private initialized = false;
  private initializingPromise: Promise<void> | null = null;
  private readonly cache = new Map<string, CacheEntry>();
  private readonly inflightRequests = new Map<string, Promise<ApiResponse<unknown>>>();

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async initialize() {
    if (this.initialized) return;
    if (this.initializingPromise) {
      await this.initializingPromise;
      return;
    }

    this.initializingPromise = (async () => {
      const [deviceId, existingDeviceToken] = await Promise.all([
        loadOrCreateDeviceId(),
        loadDeviceToken(),
      ]);
      this.deviceId = deviceId;
      this.deviceToken = existingDeviceToken;

      if (!this.deviceToken) {
        const registerResult = await this.registerDevice(deviceId, undefined, Platform.OS);
        if (!registerResult.data?.device_token) {
          throw new Error(registerResult.error || 'Device token registration failed');
        }
      }

      this.initialized = true;
    })();

    try {
      await this.initializingPromise;
    } finally {
      this.initializingPromise = null;
    }
  }

  getDeviceId() {
    return this.deviceId;
  }

  async clearCache() {
    this.invalidateCache();
  }

  async registerDevice(deviceId: string, pushToken?: string, platform?: string) {
    const result = await this.request<{ success: boolean; device_id: string; message: string; device_token: string }>('/auth/device-register', {
      skipInit: true,
      method: 'POST',
      timeoutMs: 5000,
      body: JSON.stringify({
        device_id: deviceId,
        push_token: pushToken,
        platform: platform || 'unknown',
      }),
      skipOfflineQueue: true,
    });
    if (result.data?.device_token) {
      this.deviceToken = result.data.device_token;
      await saveDeviceToken(result.data.device_token);
    }
    return result;
  }

  protected invalidateCache(prefixes: string[] = []) {
    if (!prefixes.length) {
      this.cache.clear();
      this.inflightRequests.clear();
      return;
    }

    for (const key of Array.from(this.cache.keys())) {
      if (prefixes.some(prefix => key.includes(prefix))) {
        this.cache.delete(key);
      }
    }
  }

  async getOfflineSyncStatus(): Promise<{
    online: boolean;
    pending_count: number;
    last_sync_at: number | null;
    queue_health: 'healthy' | 'warning' | 'critical';
    oldest_pending_age_ms: number;
    stale_cache_age_ms: number;
  }> {
    const online = typeof navigator !== 'undefined' && typeof navigator.onLine === 'boolean' ? navigator.onLine : true;
    try {
      const [queue, lastSync, latestCacheTimestamp] = await Promise.all([
        offlineCache.getPendingMutations(),
        offlineCache.getLastSync(),
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
      const queueHealth = this.computeQueueHealth(queue.length, oldestPendingAge);
      return {
        online,
        pending_count: queue.length,
        last_sync_at: lastSync,
        queue_health: queueHealth,
        oldest_pending_age_ms: oldestPendingAge,
        stale_cache_age_ms: staleCacheAge,
      };
    } catch {
      return {
        online,
        pending_count: 0,
        last_sync_at: null,
        queue_health: 'healthy',
        oldest_pending_age_ms: 0,
        stale_cache_age_ms: 0,
      };
    }
  }

  async retryPendingMutations(limit = 20): Promise<{ success_count: number; failed_count: number; remaining_count: number }> {
    await this.ensureInitialized();

    let successCount = 0;
    let failedCount = 0;

    try {
      const queue = await offlineCache.getPendingMutations();
      const now = Date.now();
      const targets = queue.filter(action => action.next_retry_at <= now).slice(0, limit);

      for (const action of targets) {
        try {
          const response = await fetch(`${this.baseUrl}${action.endpoint}`, {
            method: action.method,
            headers: {
              ...this.buildHeaders({ body: action.body, method: action.method }, action.idempotency_key),
              'Content-Type': 'application/json',
            },
            body: action.body,
          });

          if (response.ok) {
            await offlineCache.removePendingMutation(action.id);
            successCount += 1;
            continue;
          }

          failedCount += 1;
          const nextAttempt = action.attempt_count + 1;
          await offlineCache.updatePendingMutation(action.id, {
            attempt_count: nextAttempt,
            next_retry_at: now + this.computeBackoffMs(nextAttempt),
          });
        } catch {
          failedCount += 1;
          const nextAttempt = action.attempt_count + 1;
          await offlineCache.updatePendingMutation(action.id, {
            attempt_count: nextAttempt,
            next_retry_at: now + this.computeBackoffMs(nextAttempt),
          });
        }
      }

      if (successCount > 0) {
        await offlineCache.setLastSync();
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

  protected async request<T>(endpoint: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
    if (!options.skipInit) {
      await this.ensureInitialized();
    }

    const method = (options.method || 'GET').toUpperCase();
    const idempotencyKey = this.resolveIdempotencyKey(endpoint, method, options);
    const cacheTtlMs = options.cacheTtlMs || 0;
    const cacheKey = this.buildCacheKey(endpoint, method);

    if (method === 'GET' && cacheTtlMs > 0) {
      const cached = this.cache.get(cacheKey);
      if (cached && cached.expiresAt > Date.now()) {
        logHttpPerf({
          method,
          endpoint,
          duration_ms: 0,
          status: 'ok',
          cache: 'hit',
        });
        return { data: cached.data as T };
      }
    }

    const performRequest = async (): Promise<ApiResponse<T>> => {
      const controller = new AbortController();
      const timeoutMs = options.timeoutMs ?? REQUEST_TIMEOUT_MS;
      const timeout = setTimeout(() => controller.abort(), timeoutMs);
      const startedAt = Date.now();

      try {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
          ...options,
          headers: this.buildHeaders(options, idempotencyKey),
          signal: controller.signal,
        });

        if (!response.ok) {
          const contentType = response.headers.get('content-type') || '';
          let detail = `HTTP ${response.status}`;

          if (contentType.includes('application/json')) {
            const errorData = await this.parseJsonBody<Record<string, unknown>>(response).catch(() => ({}));
            detail = String(errorData.detail || errorData.message || detail);
          } else {
            const errorText = await response.text().catch(() => '');
            if (errorText) detail = errorText;
          }
          logHttpPerf({
            method,
            endpoint,
            duration_ms: Date.now() - startedAt,
            status: 'error',
            cache: method === 'GET' ? 'miss' : 'none',
          });
          return { error: this.localizeServerError(detail) };
        }

        const data = await this.parseJsonBody<T>(response);
        if (method === 'GET' && cacheTtlMs > 0) {
          this.cache.set(cacheKey, {
            expiresAt: Date.now() + cacheTtlMs,
            data,
          });
          this.pruneClientCache();
        }

        this.recordSyncSuccess();
        logHttpPerf({
          method,
          endpoint,
          duration_ms: Date.now() - startedAt,
          status: 'ok',
          cache: method === 'GET' ? 'miss' : 'none',
        });
        return { data };
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          logHttpPerf({
            method,
            endpoint,
            duration_ms: Date.now() - startedAt,
            status: 'timeout',
            cache: method === 'GET' ? 'miss' : 'none',
          });
          return { error: '요청 시간이 초과되었어요. 잠시 후 다시 시도해 주세요.' };
        }

        // Queue mutation requests so user can retry from Sync Center.
        if (method !== 'GET' && !options.skipOfflineQueue && !(options.body instanceof FormData)) {
          await this.enqueueMutation(endpoint, method, typeof options.body === 'string' ? options.body : undefined, idempotencyKey);
        }

        // Offline fallback for GET
        if (method === 'GET' && !options.disableOfflineFallback) {
          try {
            let offlineData: unknown = null;
            let cacheTimestamp: number | null = null;
            if (endpoint.startsWith('/inventory')) {
              const inventoryEnvelope = await offlineCache.getInventoryEnvelope();
              if (inventoryEnvelope && this.isOfflineCacheFresh(inventoryEnvelope.cache_timestamp)) {
                cacheTimestamp = inventoryEnvelope.cache_timestamp;
                offlineData = {
                  items: inventoryEnvelope.items,
                  total_count: inventoryEnvelope.items.length,
                  limit: inventoryEnvelope.items.length || 30,
                  offset: 0,
                  has_more: false,
                  offline: true,
                  cache_timestamp: cacheTimestamp,
                };
              }
            } else if (endpoint.startsWith('/recipes/favorites')) {
              const favoritesEnvelope = await offlineCache.getFavoritesEnvelope();
              if (favoritesEnvelope && this.isOfflineCacheFresh(favoritesEnvelope.cache_timestamp)) {
                cacheTimestamp = favoritesEnvelope.cache_timestamp;
                offlineData = favoritesEnvelope.recipes;
              }
            } else if (endpoint.startsWith('/shopping')) {
              const shoppingEnvelope = await offlineCache.getShoppingEnvelope();
              if (shoppingEnvelope && this.isOfflineCacheFresh(shoppingEnvelope.cache_timestamp)) {
                cacheTimestamp = shoppingEnvelope.cache_timestamp;
                offlineData = this.normalizeShoppingFallback(shoppingEnvelope.payload);
              }
            }
            if (offlineData !== null && offlineData !== undefined) {
              return {
                data: offlineData as T,
                offline: true,
                cache_timestamp: cacheTimestamp,
              } as ApiResponse<T>;
            }
          } catch {
            // ignore
          }
        }

        if (error instanceof Error) {
          const rawMessage = error.message || '';
          logHttpPerf({
            method,
            endpoint,
            duration_ms: Date.now() - startedAt,
            status: 'error',
            cache: method === 'GET' ? 'miss' : 'none',
          });
          if (rawMessage === 'Failed to fetch' || rawMessage === 'Network request failed' || rawMessage === 'Load failed') {
            if (method !== 'GET') {
              return { error: '네트워크가 불안정해 요청을 임시 보관했어요. 동기화 센터에서 재시도할 수 있어요.' };
            }
            return { error: '서버에 연결하지 못했어요. 네트워크나 서버 상태를 확인해 주세요.' };
          }
          return { error: this.localizeServerError(rawMessage) };
        }

        return { error: '네트워크 오류가 발생했어요.' };
      } finally {
        clearTimeout(timeout);
      }
    };

    if (method === 'GET' && !options.skipRequestDedup) {
      const inflightKey = this.buildCacheKey(endpoint, method);
      const pending = this.inflightRequests.get(inflightKey) as Promise<ApiResponse<T>> | undefined;
      if (pending) {
        logHttpPerf({
          method,
          endpoint,
          duration_ms: 0,
          status: 'ok',
          cache: 'dedup',
        });
        return pending;
      }

      const dedupedPromise = performRequest().finally(() => {
        this.inflightRequests.delete(inflightKey);
      });
      this.inflightRequests.set(inflightKey, dedupedPromise as Promise<ApiResponse<unknown>>);
      return dedupedPromise;
    }

    return performRequest();
  }

  private async enqueueMutation(endpoint: string, method: string, body?: string, idempotencyKey?: string) {
    try {
      await offlineCache.enqueueMutation({
        endpoint,
        method,
        body,
        idempotency_key: idempotencyKey || this.generateIdempotencyKey(endpoint, method, body),
      });
    } catch {
      // ignore
    }
  }

  private async recordSyncSuccess() {
    try {
      await offlineCache.setLastSync();
    } catch {
      // ignore
    }
  }


  private async ensureInitialized() {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  private buildHeaders(options: RequestInit, idempotencyKey?: string): Record<string, string> {
    const headers: Record<string, string> = {
      ...(APP_TOKEN && { 'X-App-Token': APP_TOKEN }),
      ...(this.deviceId && { 'X-Device-ID': this.deviceId }),
      ...(this.deviceToken && { 'X-Device-Token': this.deviceToken }),
      ...(idempotencyKey && { 'X-Idempotency-Key': idempotencyKey }),
    };

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const customHeaders = options.headers as Record<string, string> | undefined;
    return { ...headers, ...customHeaders };
  }

  private resolveIdempotencyKey(endpoint: string, method: string, options: RequestOptions): string | undefined {
    if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) return undefined;
    if (options.body instanceof FormData) return undefined;
    if (options.idempotencyKey) return options.idempotencyKey;
    return this.generateIdempotencyKey(endpoint, method, typeof options.body === 'string' ? options.body : undefined);
  }

  private generateIdempotencyKey(endpoint: string, method: string, body?: string): string {
    const payload = `${method}:${endpoint}:${body || ''}:${Date.now()}:${Math.random().toString(36).slice(2, 10)}`;
    const globalBuffer = (globalThis as { Buffer?: { from: (input: string, encoding?: string) => { toString: (encoding: string) => string } } }).Buffer;
    try {
      if (globalBuffer) {
        return globalBuffer
          .from(payload, 'utf8')
          .toString('base64')
          .replace(/\+/g, '-')
          .replace(/\//g, '_')
          .replace(/=+$/g, '')
          .slice(0, 64);
      }
    } catch {
      // ignore
    }

    try {
      if (typeof btoa === 'function') {
        return btoa(unescape(encodeURIComponent(payload))).replace(/=+$/g, '').slice(0, 64);
      }
    } catch {
      // ignore
    }

    return `ikey-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
  }

  private computeBackoffMs(attempt: number): number {
    const boundedAttempt = Math.max(1, attempt);
    return Math.min(300000, 5000 * 2 ** (boundedAttempt - 1));
  }

  private computeQueueHealth(count: number, oldestAgeMs: number): 'healthy' | 'warning' | 'critical' {
    if (count === 0) return 'healthy';
    if (count >= 100 || oldestAgeMs > 60 * 60 * 1000) return 'critical';
    if (count >= 20 || oldestAgeMs > 10 * 60 * 1000) return 'warning';
    return 'healthy';
  }

  private buildCacheKey(endpoint: string, method: string) {
    return `${method}:${endpoint}`;
  }

  private pruneClientCache() {
    while (this.cache.size > MAX_CLIENT_CACHE_ENTRIES) {
      const oldestKey = this.cache.keys().next().value as string | undefined;
      if (!oldestKey) break;
      this.cache.delete(oldestKey);
    }
  }

  private isOfflineCacheFresh(cacheTimestamp: number | null | undefined): boolean {
    if (!Number.isFinite(cacheTimestamp)) return false;
    return Date.now() - Number(cacheTimestamp) <= OFFLINE_CACHE_TTL_MS;
  }

  private normalizeShoppingFallback(data: unknown): unknown {
    if (!data) return null;
    if (Array.isArray(data)) {
      const pendingCount = data.filter(item => (item as { status?: string })?.status === 'pending').length;
      const purchasedCount = data.filter(item => (item as { status?: string })?.status === 'purchased').length;
      return {
        items: data,
        total_count: data.length,
        pending_count: pendingCount,
        purchased_count: purchasedCount,
        limit: data.length || 30,
        offset: 0,
        has_more: false,
      };
    }

    if (typeof data === 'object' && Array.isArray((data as { items?: unknown[] }).items)) {
      return data;
    }
    return null;
  }

  private localizeServerError(message: string): string {
    const normalized = (message || '').trim();
    if (!normalized) return '요청을 처리하지 못했어요.';

    const lower = normalized.toLowerCase();
    const directMappings: Array<[string, string]> = [
      ['inventory item not found', '인벤토리 항목을 찾을 수 없어요.'],
      ['shopping item not found', '장보기 항목을 찾을 수 없어요.'],
      ['recipe not found', '레시피를 찾을 수 없어요.'],
      ['cooking history entry not found', '요리 이력을 찾을 수 없어요.'],
      ['scan result not found', '스캔 결과를 찾을 수 없어요.'],
      ['only image files are supported', '이미지 파일만 업로드할 수 있어요.'],
      ['image file is too large', '이미지 파일이 너무 커요. 업로드 용량 제한을 확인해 주세요.'],
      ['name cannot be empty', '이름은 비워둘 수 없어요.'],
      ['quantity must be greater than or equal to 0', '수량은 0 이상이어야 해요.'],
      ['no fields to update', '수정할 항목이 없어요.'],
      ['at least one item is required', '최소 1개 이상의 항목이 필요해요.'],
      ['at least one ingredient is required', '최소 1개 이상의 재료가 필요해요.'],
      ['no valid item payload provided', '유효한 항목 정보가 없어요.'],
      ['no valid ingredient payload provided', '유효한 재료 정보가 없어요.'],
      ['sort_by must be one of', '정렬 기준이 올바르지 않아요.'],
      ['mode must be either merge or replace', '복원 모드는 merge 또는 replace만 사용할 수 있어요.'],
      ['recipe id does not match the request body', '레시피 ID가 요청 본문과 일치하지 않아요.'],
      ['recipe payload is required to save generated recommendations', '생성 레시피를 저장하려면 레시피 데이터가 필요해요.'],
      ['servings must be at least 1', '인분은 1 이상이어야 해요.'],
      ['failed to load shopping list', '장보기 목록을 불러오지 못했어요.'],
      ['failed to calculate low-stock suggestions', '저재고 추천 계산에 실패했어요.'],
      ['failed to add low-stock suggestions', '저재고 추천 항목 추가에 실패했어요.'],
      ['failed to add shopping items', '장보기 항목 추가에 실패했어요.'],
      ['failed to add recipe ingredients to shopping list', '레시피 재료를 장보기 목록에 추가하지 못했어요.'],
      ['failed to process shopping checkout', '장보기 처리에 실패했어요.'],
      ['failed to update shopping item', '장보기 항목 수정에 실패했어요.'],
      ['failed to delete shopping item', '장보기 항목 삭제에 실패했어요.'],
      ['failed to update inventory item', '인벤토리 항목 수정에 실패했어요.'],
      ['failed to delete inventory item', '인벤토리 항목 삭제에 실패했어요.'],
      ['failed to restore inventory item', '인벤토리 항목 복구에 실패했어요.'],
      ['failed to complete cooking transaction', '요리 완료 처리에 실패했어요.'],
      ['failed to analyze scan image', '스캔 분석에 실패했어요.'],
      ['failed to export backup', '백업 내보내기에 실패했어요.'],
      ['failed to restore backup', '백업 복원에 실패했어요.'],
      ['shopping feature is not initialized', '장보기 기능이 초기화되지 않았어요. 서버 스키마를 확인해 주세요.'],
    ];
    for (const [needle, localized] of directMappings) {
      if (lower.includes(needle)) return localized;
    }

    if (lower.includes('method not allowed')) return '지원하지 않는 요청 방식입니다.';
    if (lower.includes('internal server error')) return '서버 내부 오류가 발생했어요.';
    if (lower.includes('timeout') || lower.includes('timed out')) return '요청 시간이 초과되었어요. 잠시 후 다시 시도해 주세요.';
    if (lower.includes('failed to fetch') || lower.includes('network request failed') || lower.includes('load failed')) {
      return '서버에 연결하지 못했어요. 네트워크나 서버 상태를 확인해 주세요.';
    }

    return normalized;
  }
  private async parseJsonBody<T>(response: Response): Promise<T> {
    if (Platform.OS === 'web' && typeof response.text === 'function') {
      const raw = await response.text();
      return parseJsonWithWorker<T>(raw);
    }
    return (await response.json()) as T;
  }
}




