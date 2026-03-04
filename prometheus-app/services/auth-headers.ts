export function buildAppAuthHeaders(appId: string, legacyAppToken: string): Record<string, string> {
  const headers: Record<string, string> = {};

  const normalizedAppId = (appId || '').trim();
  if (normalizedAppId) {
    headers['X-App-ID'] = normalizedAppId;
  }

  const normalizedLegacyToken = (legacyAppToken || '').trim();
  if (normalizedLegacyToken) {
    headers['X-App-Token'] = normalizedLegacyToken;
  }

  return headers;
}
