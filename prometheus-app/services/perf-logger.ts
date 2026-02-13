type HttpPerfStatus = 'ok' | 'error' | 'timeout';
type HttpPerfCache = 'hit' | 'miss' | 'dedup' | 'none';

type HttpPerfEvent = {
  method: string;
  endpoint: string;
  duration_ms: number;
  status: HttpPerfStatus;
  cache: HttpPerfCache;
};

const PERF_ENV_FLAG = process.env.EXPO_PUBLIC_ENABLE_PERF_LOGS === 'true';

export function logHttpPerf(event: HttpPerfEvent) {
  if (!__DEV__ && !PERF_ENV_FLAG) return;
  const durationMs = Number.isFinite(event.duration_ms) ? event.duration_ms.toFixed(1) : '0.0';
  console.info(
    `[perf.http] method=${event.method} endpoint=${event.endpoint} status=${event.status} cache=${event.cache} duration_ms=${durationMs}`
  );
}
