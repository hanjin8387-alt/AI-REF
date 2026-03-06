import type { BackupExportResponse, BackupRestoreResponse } from '../api.types';

import type { ApiTransport } from '../domain/types';

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
