export type MutationIdentity = {
  fingerprint: string;
  idempotencyKey?: string;
};

function stableHash(input: string): string {
  let hash = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return Math.abs(hash >>> 0).toString(36);
}

function normalizeBody(body?: string): string {
  return (body || '').trim();
}

export function createMutationIdentity(
  endpoint: string,
  method: string,
  body?: string,
  explicitIdempotencyKey?: string
): MutationIdentity {
  const upperMethod = method.toUpperCase();
  if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(upperMethod)) {
    return { fingerprint: `${upperMethod}:${endpoint}` };
  }

  const normalizedBody = normalizeBody(body);
  const fingerprint = `${upperMethod}:${endpoint}:${stableHash(normalizedBody)}`;
  if (explicitIdempotencyKey) {
    return {
      fingerprint,
      idempotencyKey: explicitIdempotencyKey,
    };
  }

  const seed = `${fingerprint}:${Date.now()}:${Math.random().toString(36).slice(2, 12)}`;
  return {
    fingerprint,
    idempotencyKey: `ikey-${stableHash(seed)}`,
  };
}
