import { Platform } from 'react-native';

import { offlineCache, type PendingMutation } from '../offline-cache';
import { logHttpPerf } from '../perf-logger';
import { parseJsonWithWorker } from '../../utils/json-worker';
import { AuthContext } from './auth-context';
import { localizeServerError } from './error-map';
import { createMutationIdentity } from './idempotency';
import { loadOfflineFallback } from './offline-fallback';
import { getOfflineSyncStatus, retryPendingMutations } from './offline-queue';

const REQUEST_TIMEOUT_MS = 20000;
const MAX_CLIENT_CACHE_ENTRIES = 200;
const OFFLINE_CACHE_TTL_MS = 24 * 60 * 60 * 1000;

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  offline?: boolean;
  cache_timestamp?: number | null;
}

export type RequestOptions = RequestInit & {
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

export class HttpClient {
  private readonly cache = new Map<string, CacheEntry>();
  private readonly inflightRequests = new Map<string, Promise<ApiResponse<unknown>>>();
  private readonly authContext: AuthContext;

  constructor(private readonly baseUrl: string) {
    this.authContext = new AuthContext((deviceId, pushToken, platform) =>
      this.performRequest<{ success: boolean; device_id: string; message: string; device_token: string }>(
        '/auth/device-register',
        {
          skipInit: true,
          method: 'POST',
          timeoutMs: 5000,
          body: JSON.stringify({
            device_id: deviceId,
            push_token: pushToken,
            platform: platform || 'unknown',
          }),
          skipOfflineQueue: true,
        }
      )
    );
  }

  async initialize() {
    await this.authContext.ensureInitialized();
  }

  getDeviceId() {
    return this.authContext.getDeviceId();
  }

  async clearCache() {
    this.invalidateCache();
  }

  async registerDevice(deviceId: string, pushToken?: string, platform?: string) {
    return this.authContext.registerDevice(deviceId, pushToken, platform);
  }

  invalidateCache(prefixes: string[] = []) {
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

  async getOfflineSyncStatus() {
    return getOfflineSyncStatus();
  }

  async retryPendingMutations(limit = 20) {
    await this.ensureInitialized();
    return retryPendingMutations(action => this.dispatchQueuedMutation(action), limit);
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
    if (!options.skipInit) {
      await this.ensureInitialized();
    }

    const method = (options.method || 'GET').toUpperCase();
    const mutationIdentity =
      options.body instanceof FormData
        ? { fingerprint: `${method}:${endpoint}` }
        : createMutationIdentity(
            endpoint,
            method,
            typeof options.body === 'string' ? options.body : undefined,
            options.idempotencyKey
          );
    const cacheTtlMs = options.cacheTtlMs || 0;
    const cacheKey = this.buildCacheKey(endpoint, method);

    if (method === 'GET' && cacheTtlMs > 0) {
      const cached = this.cache.get(cacheKey);
      if (cached && cached.expiresAt > Date.now()) {
        logHttpPerf({ method, endpoint, duration_ms: 0, status: 'ok', cache: 'hit' });
        return { data: cached.data as T };
      }
    }

    const perform = (): Promise<ApiResponse<T>> =>
      this.performRequest<T>(endpoint, options, mutationIdentity.idempotencyKey, mutationIdentity.fingerprint);

    if (method === 'GET' && !options.skipRequestDedup) {
      const pending = this.inflightRequests.get(cacheKey) as Promise<ApiResponse<T>> | undefined;
      if (pending) {
        logHttpPerf({ method, endpoint, duration_ms: 0, status: 'ok', cache: 'dedup' });
        return pending;
      }

      const dedupedPromise = perform().finally(() => {
        this.inflightRequests.delete(cacheKey);
      });
      this.inflightRequests.set(cacheKey, dedupedPromise as Promise<ApiResponse<unknown>>);
      return dedupedPromise;
    }

    return perform();
  }

  private async performRequest<T>(
    endpoint: string,
    options: RequestOptions,
    idempotencyKey?: string,
    fingerprint?: string
  ): Promise<ApiResponse<T>> {
    const method = (options.method || 'GET').toUpperCase();
    const cacheTtlMs = options.cacheTtlMs || 0;
    const cacheKey = this.buildCacheKey(endpoint, method);
    const controller = new AbortController();
    const timeoutMs = options.timeoutMs ?? REQUEST_TIMEOUT_MS;
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    const startedAt = Date.now();

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers: this.authContext.buildHeaders(options, idempotencyKey),
        signal: controller.signal,
      });

      if (!response.ok) {
        const detail = await this.readErrorDetail(response);
        logHttpPerf({
          method,
          endpoint,
          duration_ms: Date.now() - startedAt,
          status: 'error',
          cache: method === 'GET' ? 'miss' : 'none',
        });
        return { error: localizeServerError(detail) };
      }

      const data = await this.parseJsonBody<T>(response);
      if (method === 'GET' && cacheTtlMs > 0) {
        this.cache.set(cacheKey, {
          expiresAt: Date.now() + cacheTtlMs,
          data,
        });
        this.pruneClientCache();
      }

      await offlineCache.setLastContact();
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

      if (method !== 'GET' && !options.skipOfflineQueue && !(options.body instanceof FormData)) {
        await this.enqueueMutation(
          endpoint,
          method,
          typeof options.body === 'string' ? options.body : undefined,
          idempotencyKey,
          fingerprint
        );
      }

      if (method === 'GET' && !options.disableOfflineFallback) {
        const offlineFallback = await loadOfflineFallback<T>(endpoint, timestamp => this.isOfflineCacheFresh(timestamp));
        if (offlineFallback) {
          return {
            data: offlineFallback.data,
            offline: true,
            cache_timestamp: offlineFallback.cacheTimestamp,
          };
        }
      }

      logHttpPerf({
        method,
        endpoint,
        duration_ms: Date.now() - startedAt,
        status: 'error',
        cache: method === 'GET' ? 'miss' : 'none',
      });

      if (error instanceof Error) {
        const rawMessage = error.message || '';
        if (rawMessage === 'Failed to fetch' || rawMessage === 'Network request failed' || rawMessage === 'Load failed') {
          if (method !== 'GET') {
            return { error: '네트워크가 불안정해 요청을 임시 보관했어요. 동기화 센터에서 다시 시도할 수 있어요.' };
          }
          return { error: '서버에 연결하지 못했어요. 네트워크와 서버 상태를 확인해 주세요.' };
        }
        return { error: localizeServerError(rawMessage) };
      }

      return { error: '네트워크 오류가 발생했어요.' };
    } finally {
      clearTimeout(timeout);
    }
  }

  private async dispatchQueuedMutation(action: PendingMutation): Promise<boolean> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(`${this.baseUrl}${action.endpoint}`, {
        method: action.method,
        headers: this.authContext.buildHeaders(
          {
            method: action.method,
            body: action.body,
            headers: { 'Content-Type': 'application/json' },
          },
          action.idempotency_key
        ),
        body: action.body,
        signal: controller.signal,
      });
      return response.ok;
    } catch {
      return false;
    } finally {
      clearTimeout(timeout);
    }
  }

  private async enqueueMutation(
    endpoint: string,
    method: string,
    body?: string,
    idempotencyKey?: string,
    fingerprint?: string
  ) {
    try {
      await offlineCache.enqueueMutation({
        endpoint,
        method,
        body,
        idempotency_key: idempotencyKey || createMutationIdentity(endpoint, method, body).idempotencyKey || '',
        fingerprint,
      });
    } catch {
      // ignore
    }
  }

  private async ensureInitialized() {
    await this.authContext.ensureInitialized();
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

  private async parseJsonBody<T>(response: Response): Promise<T> {
    if (Platform.OS === 'web' && typeof response.text === 'function') {
      const raw = await response.text();
      return parseJsonWithWorker<T>(raw);
    }
    return (await response.json()) as T;
  }

  private async readErrorDetail(response: Response): Promise<string> {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const errorData = await this.parseJsonBody<Record<string, unknown>>(response).catch(() => ({}));
      const detailMessage =
        (errorData && typeof errorData === 'object' && (errorData as Record<string, unknown>).detail) ||
        (errorData && typeof errorData === 'object' && (errorData as Record<string, unknown>).message) ||
        `HTTP ${response.status}`;
      return String(detailMessage);
    }

    const errorText = await response.text().catch(() => '');
    return errorText || `HTTP ${response.status}`;
  }
}
