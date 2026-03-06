import { Platform } from 'react-native';

import type { BarcodeResponse, ScanResultPayload, ScanSourceType } from '../api.types';

import type { ApiTransport } from '../domain/types';

const DEFAULT_SCAN_EXTENSION = 'jpg';
const SCAN_UPLOAD_TIMEOUT_MS = 120000;
const SCAN_RESULT_TIMEOUT_MS = 30000;

function normalizeImageExtension(raw?: string): string {
  const normalized = (raw || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  if (normalized === 'jpeg') return 'jpg';
  if (normalized === 'heif') return 'heic';
  if (!normalized) return DEFAULT_SCAN_EXTENSION;
  return normalized.slice(0, 5);
}

function extensionFromMimeType(mimeType?: string | null): string {
  if (!mimeType) return DEFAULT_SCAN_EXTENSION;
  const match = mimeType.match(/^image\/([a-zA-Z0-9.+-]+)/i);
  return normalizeImageExtension(match?.[1]);
}

function extensionFromImageUri(imageUri: string): string {
  const dataUriMatch = imageUri.match(/^data:image\/([a-zA-Z0-9.+-]+);base64,/i);
  if (dataUriMatch?.[1]) {
    return normalizeImageExtension(dataUriMatch[1]);
  }

  try {
    const pathname = new URL(imageUri, 'https://local.invalid').pathname;
    const filename = pathname.split('/').pop() || '';
    const extensionMatch = filename.match(/\.([a-zA-Z0-9]{1,8})$/);
    if (extensionMatch?.[1]) {
      return normalizeImageExtension(extensionMatch[1]);
    }
  } catch {
    // Non-standard URIs fall back to default.
  }

  return DEFAULT_SCAN_EXTENSION;
}

export async function uploadScanApi(
  transport: ApiTransport,
  imageUri: string,
  sourceType: ScanSourceType = 'camera'
) {
  const formData = new FormData();
  const fileExtension = extensionFromImageUri(imageUri);
  const normalizedType = fileExtension === 'jpg' ? 'jpeg' : fileExtension;
  const mimeType = `image/${normalizedType}`;

  if (Platform.OS === 'web') {
    const blobResponse = await fetch(imageUri);
    const blob = await blobResponse.blob();
    const blobExtension = extensionFromMimeType(blob.type) || fileExtension;
    formData.append('file', blob, `scan.${blobExtension}`);
  } else {
    formData.append(
      'file',
      {
        uri: imageUri,
        name: `scan.${fileExtension}`,
        type: mimeType,
      } as never
    );
  }

  return transport.request<{ scan_id: string; status: string; message: string }>(
    `/scans/upload?source_type=${sourceType}`,
    {
      method: 'POST',
      body: formData,
      timeoutMs: SCAN_UPLOAD_TIMEOUT_MS,
    }
  );
}

export async function getScanResultApi(transport: ApiTransport, scanId: string) {
  return transport.request<ScanResultPayload>(`/scans/${scanId}/result`, { timeoutMs: SCAN_RESULT_TIMEOUT_MS });
}

export async function lookupBarcodeApi(transport: ApiTransport, code: string) {
  return transport.request<BarcodeResponse>(`/scans/barcode?code=${encodeURIComponent(code)}`, {
    cacheTtlMs: 30000,
  });
}
