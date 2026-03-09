import Constants from 'expo-constants';
import { isLegacyAppTokenEnabled as resolveLegacyEnabled, resolveLegacyAppToken } from './legacy-auth';

type ExtraConfig = {
  apiUrl?: string;
  appId?: string;
};

const DEFAULT_API_URL = 'http://localhost:8000';

function readExtraConfig(): ExtraConfig {
  return (Constants.expoConfig?.extra as ExtraConfig | undefined) || {};
}

export function getApiBaseUrl(): string {
  const extra = readExtraConfig();
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  const fromConfig = extra.apiUrl;
  return (fromEnv || fromConfig || DEFAULT_API_URL).trim();
}

export function getAppId(): string {
  const extra = readExtraConfig();
  const fromEnv = process.env.EXPO_PUBLIC_APP_ID;
  const fromConfig = extra.appId;
  return (fromEnv || fromConfig || 'prometheus-app').trim();
}

export function isLegacyAppTokenEnabled(): boolean {
  return resolveLegacyEnabled({
    envLegacyEnabled: process.env.EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN,
  });
}

export function getLegacyAppToken(): string {
  return resolveLegacyAppToken({
    envLegacyEnabled: process.env.EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN,
    envLegacyToken: process.env.EXPO_PUBLIC_APP_TOKEN,
  });
}
