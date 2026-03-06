import type { NotificationListResponse } from '../api.types';

import type { ApiTransport } from '../domain/types';

export async function getNotificationsApi(
  transport: ApiTransport,
  limit = 30,
  offset = 0,
  onlyUnread = false
) {
  return transport.request<NotificationListResponse>(
    `/notifications?limit=${limit}&offset=${offset}&only_unread=${onlyUnread ? 'true' : 'false'}`,
    { cacheTtlMs: 3000 }
  );
}

export async function markNotificationsReadApi(transport: ApiTransport, ids: string[] = []) {
  const result = await transport.request<{ success: boolean; updated_count: number }>('/notifications/read', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  });
  if (result.data?.success) {
    transport.invalidateCache(['/notifications']);
  }
  return result;
}
