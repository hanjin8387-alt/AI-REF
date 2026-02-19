const WEB_DEVICE_TOKEN_KEY = 'prometheus_device_token';

export async function loadDeviceToken(): Promise<string | null> {
  try {
    return typeof localStorage !== 'undefined' ? localStorage.getItem(WEB_DEVICE_TOKEN_KEY) : null;
  } catch {
    return null;
  }
}

export async function saveDeviceToken(token: string): Promise<void> {
  const normalized = token.trim();
  if (!normalized) return;
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(WEB_DEVICE_TOKEN_KEY, normalized);
    }
  } catch {
    // ignore
  }
}

export async function clearDeviceToken(): Promise<void> {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(WEB_DEVICE_TOKEN_KEY);
    }
  } catch {
    // ignore
  }
}
