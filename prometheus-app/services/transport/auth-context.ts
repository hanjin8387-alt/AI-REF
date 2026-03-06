import { Platform } from 'react-native';

import { loadOrCreateDeviceId } from '../device-id-storage';
import { loadDeviceToken, saveDeviceToken } from '../device-token-storage';
import { buildAppAuthHeaders } from '../auth-headers';
import { getAppId, getLegacyAppToken } from '../config/runtime';

type RegisterDeviceResult = {
  data?: {
    device_token?: string;
  };
  error?: string;
};

export class AuthContext {
  private deviceId: string | null = null;
  private deviceToken: string | null = null;
  private initialized = false;
  private initializingPromise: Promise<void> | null = null;

  constructor(
    private readonly registerDeviceRequest: (deviceId: string, pushToken?: string, platform?: string) => Promise<RegisterDeviceResult>
  ) {}

  getDeviceId() {
    return this.deviceId;
  }

  getDeviceToken() {
    return this.deviceToken;
  }

  async ensureInitialized() {
    if (this.initialized) return;
    if (this.initializingPromise) {
      await this.initializingPromise;
      return;
    }

    this.initializingPromise = (async () => {
      const [deviceId, existingDeviceToken] = await Promise.all([
        loadOrCreateDeviceId(),
        loadDeviceToken(),
      ]);
      this.deviceId = deviceId;
      this.deviceToken = existingDeviceToken;

      if (!this.deviceToken) {
        const registerResult = await this.registerDevice(deviceId, undefined, Platform.OS);
        if (!registerResult.data?.device_token) {
          throw new Error(registerResult.error || 'Device token registration failed');
        }
      }

      this.initialized = true;
    })();

    try {
      await this.initializingPromise;
    } finally {
      this.initializingPromise = null;
    }
  }

  async registerDevice(deviceId: string, pushToken?: string, platform?: string) {
    const result = await this.registerDeviceRequest(deviceId, pushToken, platform);
    if (result.data?.device_token) {
      this.deviceToken = result.data.device_token;
      await saveDeviceToken(result.data.device_token);
    }
    return result;
  }

  buildHeaders(options: RequestInit, idempotencyKey?: string): Record<string, string> {
    const headers: Record<string, string> = {
      ...buildAppAuthHeaders(getAppId(), getLegacyAppToken()),
      ...(this.deviceId && { 'X-Device-ID': this.deviceId }),
      ...(this.deviceToken && { 'X-Device-Token': this.deviceToken }),
      ...(idempotencyKey && { 'X-Idempotency-Key': idempotencyKey }),
    };

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const customHeaders = options.headers as Record<string, string> | undefined;
    return { ...headers, ...customHeaders };
  }
}
