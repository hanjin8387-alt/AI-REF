import * as FileSystem from 'expo-file-system/legacy';

const WEB_DEVICE_TOKEN_KEY = 'prometheus_device_token';
const DEVICE_TOKEN_FILE = 'prometheus-device-token.txt';

export async function loadDeviceToken(): Promise<string | null> {
  // Some test and hybrid environments may expose localStorage even for native modules.
  try {
    const existing = typeof localStorage !== 'undefined' ? localStorage.getItem(WEB_DEVICE_TOKEN_KEY) : null;
    if (existing) return existing;
  } catch {
    // ignore
  }

  const documentDirectory = FileSystem.documentDirectory;
  if (!documentDirectory) {
    return null;
  }

  const fileUri = `${documentDirectory}${DEVICE_TOKEN_FILE}`;
  try {
    const existing = await FileSystem.readAsStringAsync(fileUri);
    const trimmed = existing.trim();
    return trimmed || null;
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
      return;
    }
  } catch {
    // ignore
  }

  const documentDirectory = FileSystem.documentDirectory;
  if (!documentDirectory) return;
  const fileUri = `${documentDirectory}${DEVICE_TOKEN_FILE}`;
  await FileSystem.writeAsStringAsync(fileUri, normalized);
}

export async function clearDeviceToken(): Promise<void> {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(WEB_DEVICE_TOKEN_KEY);
    }
  } catch {
    // ignore
  }

  const documentDirectory = FileSystem.documentDirectory;
  if (!documentDirectory) return;
  const fileUri = `${documentDirectory}${DEVICE_TOKEN_FILE}`;
  try {
    await FileSystem.deleteAsync(fileUri, { idempotent: true });
  } catch {
    // ignore
  }
}
