import Constants from 'expo-constants';

type ExtraConfig = {
  apiUrl?: string;
  appId?: string;
  legacyAppToken?: string;
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

export function getLegacyAppToken(): string {
  const extra = readExtraConfig();
  const fromEnv = process.env.EXPO_PUBLIC_APP_TOKEN;
  const fromConfig = extra.legacyAppToken;
  return (fromEnv || fromConfig || '').trim();
}
