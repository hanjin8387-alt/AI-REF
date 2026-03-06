export type LegacyAuthResolutionInput = {
  envLegacyToken?: string;
  envLegacyEnabled?: string | boolean;
};

export function parseBoolean(value: unknown): boolean | null {
  if (typeof value === 'boolean') return value;
  if (typeof value !== 'string') return null;

  const normalized = value.trim().toLowerCase();
  if (['1', 'true', 'yes', 'on'].includes(normalized)) return true;
  if (['0', 'false', 'no', 'off'].includes(normalized)) return false;
  return null;
}

export function isLegacyAppTokenEnabled(input: LegacyAuthResolutionInput): boolean {
  const envValue = parseBoolean(input.envLegacyEnabled);
  if (envValue !== null) return envValue;
  return false;
}

export function resolveLegacyAppToken(input: LegacyAuthResolutionInput): string {
  if (!isLegacyAppTokenEnabled(input)) {
    return '';
  }
  return (input.envLegacyToken || '').trim();
}
