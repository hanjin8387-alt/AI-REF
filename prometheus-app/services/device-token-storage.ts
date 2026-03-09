import AsyncStorage from '@react-native-async-storage/async-storage';

const DEVICE_TOKEN_KEY = 'prometheus_device_token';

export async function loadDeviceToken(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(DEVICE_TOKEN_KEY);
  } catch {
    return null;
  }
}

export async function saveDeviceToken(token: string): Promise<void> {
  const normalized = token.trim();
  if (!normalized) return;
  try {
    await AsyncStorage.setItem(DEVICE_TOKEN_KEY, normalized);
  } catch {
    // ignore
  }
}

export async function clearDeviceToken(): Promise<void> {
  try {
    await AsyncStorage.removeItem(DEVICE_TOKEN_KEY);
  } catch {
    // ignore
  }
}
