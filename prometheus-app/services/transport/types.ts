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
