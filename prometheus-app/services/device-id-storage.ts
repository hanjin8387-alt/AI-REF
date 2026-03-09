import AsyncStorage from '@react-native-async-storage/async-storage';

const DEVICE_ID_KEY = 'prometheus_device_id';

function generateDeviceId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `device-${crypto.randomUUID()}`;
  }
  return `device-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

export async function loadOrCreateDeviceId(): Promise<string> {
  try {
    const existing = await AsyncStorage.getItem(DEVICE_ID_KEY);
    if (existing) return existing;
  } catch {
    // ignore
  }

  const created = generateDeviceId();
  try {
    await AsyncStorage.setItem(DEVICE_ID_KEY, created);
  } catch {
    // ignore
  }
  return created;
}
