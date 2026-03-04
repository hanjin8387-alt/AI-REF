import { describe, expect, it } from 'vitest';

import { isLegacyAppTokenEnabled, resolveLegacyAppToken } from '../services/config/legacy-auth';

describe('legacy app token compatibility', () => {
  it('disables legacy token by default', () => {
    expect(
      resolveLegacyAppToken({
        envLegacyToken: 'legacy-token',
      })
    ).toBe('');
  });

  it('accepts legacy token only when explicitly enabled by env', () => {
    expect(
      resolveLegacyAppToken({
        envLegacyEnabled: 'true',
        envLegacyToken: 'legacy-token',
      })
    ).toBe('legacy-token');
  });

  it('accepts config fallback when explicitly enabled by config', () => {
    expect(
      resolveLegacyAppToken({
        configLegacyEnabled: true,
        configLegacyToken: 'config-legacy-token',
      })
    ).toBe('config-legacy-token');
  });

  it('treats invalid boolean values as disabled', () => {
    expect(
      isLegacyAppTokenEnabled({
        envLegacyEnabled: 'sometimes',
        configLegacyEnabled: 'enabled',
      })
    ).toBe(false);
  });
});
