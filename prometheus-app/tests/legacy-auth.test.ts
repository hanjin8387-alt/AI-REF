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

  it('does not accept token values without explicit env opt-in', () => {
    expect(
      resolveLegacyAppToken({
        envLegacyEnabled: 'false',
        envLegacyToken: 'legacy-token',
      })
    ).toBe('');
  });

  it('treats invalid boolean values as disabled', () => {
    expect(
      isLegacyAppTokenEnabled({
        envLegacyEnabled: 'sometimes',
      })
    ).toBe(false);
  });
});
