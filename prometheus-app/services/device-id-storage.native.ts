import * as FileSystem from 'expo-file-system/legacy';

const WEB_DEVICE_ID_KEY = 'prometheus_device_id';
const DEVICE_ID_FILE = 'prometheus-device-id.txt';

function generateDeviceId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `device-${crypto.randomUUID()}`;
  }
  return `device-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

export async function loadOrCreateDeviceId(): Promise<string> {
  // Some test and hybrid environments may expose localStorage even for native modules.
  try {
    const existing = typeof localStorage !== 'undefined' ? localStorage.getItem(WEB_DEVICE_ID_KEY) : null;
    if (existing) return existing;
  } catch {
    // ignore
  }

  const documentDirectory = FileSystem.documentDirectory;
  if (!documentDirectory) {
    return generateDeviceId();
  }

  const fileUri = `${documentDirectory}${DEVICE_ID_FILE}`;
  try {
    const existing = await FileSystem.readAsStringAsync(fileUri);
    const trimmed = existing.trim();
    if (trimmed) return trimmed;
  } catch {
    // first run
  }

  const created = generateDeviceId();
  await FileSystem.writeAsStringAsync(fileUri, created);
  return created;
}

