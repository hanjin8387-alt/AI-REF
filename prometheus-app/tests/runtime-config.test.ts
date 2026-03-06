import { afterEach, describe, expect, it, vi } from 'vitest';

const expoConstantsMock = {
  expoConfig: {
    extra: {
      apiUrl: 'http://localhost:8000',
      appId: 'prometheus-app',
    },
  },
};

vi.mock('expo-constants', () => ({
  default: expoConstantsMock,
}));

describe('runtime config legacy auth flags', () => {
  afterEach(() => {
    delete process.env.EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN;
    delete process.env.EXPO_PUBLIC_APP_TOKEN;
    (expoConstantsMock.expoConfig.extra as Record<string, unknown>).legacyAppToken = '';
    vi.resetModules();
  });

  it('keeps legacy token disabled by default even if a token value exists', async () => {
    process.env.EXPO_PUBLIC_APP_TOKEN = 'legacy-token';
    const runtime = await import('../services/config/runtime');

    expect(runtime.isLegacyAppTokenEnabled()).toBe(false);
    expect(runtime.getLegacyAppToken()).toBe('');
  });

  it('allows explicit env opt-in for deprecated legacy token path', async () => {
    process.env.EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN = 'true';
    process.env.EXPO_PUBLIC_APP_TOKEN = 'legacy-token';
    const runtime = await import('../services/config/runtime');

    expect(runtime.isLegacyAppTokenEnabled()).toBe(true);
    expect(runtime.getLegacyAppToken()).toBe('legacy-token');
  });

  it('ignores legacy tokens injected through expo extra config', async () => {
    process.env.EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN = 'true';
    (expoConstantsMock.expoConfig.extra as Record<string, unknown>).legacyAppToken = 'config-legacy-token';
    const runtime = await import('../services/config/runtime');

    expect(runtime.isLegacyAppTokenEnabled()).toBe(true);
    expect(runtime.getLegacyAppToken()).toBe('');
  });
});
