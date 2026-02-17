const WEB_DEVICE_ID_KEY = 'prometheus_device_id';

function generateDeviceId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `device-${crypto.randomUUID()}`;
  }
  return `device-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

export async function loadOrCreateDeviceId(): Promise<string> {
  try {
    const existing = typeof localStorage !== 'undefined' ? localStorage.getItem(WEB_DEVICE_ID_KEY) : null;
    if (existing) return existing;
  } catch {
    // ignore
  }

  const generated = generateDeviceId();
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(WEB_DEVICE_ID_KEY, generated);
    }
  } catch {
    // ignore
  }
  return generated;
}

