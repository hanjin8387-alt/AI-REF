import { describe, expect, it } from 'vitest';

import { buildAppAuthHeaders } from '../services/auth-headers';

describe('buildAppAuthHeaders', () => {
  it('always includes X-App-ID when provided', () => {
    expect(buildAppAuthHeaders('prometheus-app', '')).toEqual({
      'X-App-ID': 'prometheus-app',
    });
  });

  it('does not include X-App-Token unless explicitly provided', () => {
    expect(buildAppAuthHeaders('prometheus-app', '')).not.toHaveProperty('X-App-Token');
  });

  it('includes X-App-Token only when explicit token exists', () => {
    expect(buildAppAuthHeaders('prometheus-app', 'legacy-token')).toEqual({
      'X-App-ID': 'prometheus-app',
      'X-App-Token': 'legacy-token',
    });
  });
});
