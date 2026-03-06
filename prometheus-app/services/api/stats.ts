import type { PriceHistoryResponse, StatsSummaryResponse } from '../api.types';

import type { ApiTransport } from '../domain/types';

export async function getStatsSummaryApi(
  transport: ApiTransport,
  period: 'week' | 'month' | 'all' = 'month'
) {
  return transport.request<StatsSummaryResponse>(`/stats/summary?period=${period}`, { cacheTtlMs: 10000 });
}

export async function getPriceHistoryApi(
  transport: ApiTransport,
  name?: string,
  days = 90,
  limit = 100,
  offset = 0
) {
  const params = new URLSearchParams({
    days: String(days),
    limit: String(limit),
    offset: String(offset),
  });
  if (name) params.append('name', name);
  return transport.request<PriceHistoryResponse>(`/stats/price-history?${params.toString()}`, { cacheTtlMs: 5000 });
}
