import type { BootstrapResponse } from '../api.types';

import type { ApiTransport } from '../domain/types';

export async function bootstrapDomain(transport: ApiTransport, options: { timeoutMs?: number } = {}) {
  return transport.request<BootstrapResponse>('/auth/bootstrap', {
    cacheTtlMs: 0,
    skipOfflineQueue: true,
    timeoutMs: options.timeoutMs,
  });
}
