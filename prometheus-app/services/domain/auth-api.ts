import type { BackupExportResponse, BackupRestoreResponse, BootstrapResponse } from '../api.types';

import type { ApiTransport } from './types';

export async function exportBackupDomain(transport: ApiTransport) {
  return transport.request<BackupExportResponse>('/auth/backup/export', { cacheTtlMs: 0 });
}

export async function restoreBackupDomain(
  transport: ApiTransport,
  payload: Record<string, unknown>,
  mode: 'merge' | 'replace' = 'merge'
) {
  return transport.request<BackupRestoreResponse>('/auth/backup/restore', {
    method: 'POST',
    body: JSON.stringify({ payload, mode }),
  });
}

export async function bootstrapDomain(transport: ApiTransport, options: { timeoutMs?: number } = {}) {
  return transport.request<BootstrapResponse>('/auth/bootstrap', {
    cacheTtlMs: 0,
    skipOfflineQueue: true,
    timeoutMs: options.timeoutMs,
  });
}
