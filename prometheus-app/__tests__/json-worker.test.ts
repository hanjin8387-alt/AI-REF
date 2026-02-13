import { parseJsonWithWorker } from '../utils/json-worker';

describe('json-worker', () => {
  const originalWorker = (global as { Worker?: unknown }).Worker;
  const originalBlob = (global as { Blob?: unknown }).Blob;
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;

  afterEach(() => {
    (global as { Worker?: unknown }).Worker = originalWorker;
    (global as { Blob?: unknown }).Blob = originalBlob;
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  it('parses directly when payload is small', async () => {
    (global as { Worker?: unknown }).Worker = undefined;
    const raw = JSON.stringify({ ok: true, count: 1 });

    const parsed = await parseJsonWithWorker<{ ok: boolean; count: number }>(raw, { minimumSize: 1000 });

    expect(parsed).toEqual({ ok: true, count: 1 });
  });

  it('uses worker path for large payload when worker APIs are available', async () => {
    const createObjectURL = jest.fn().mockReturnValue('blob:json-worker-test');
    const revokeObjectURL = jest.fn();
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = revokeObjectURL;

    class FakeBlob {
      constructor(public _parts: unknown[], public _options: { type?: string }) {}
    }

    class FakeWorker {
      onmessage: ((event: { data: unknown }) => void) | null = null;
      onerror: (() => void) | null = null;

      constructor(public _url: string) {}

      postMessage(payload: string) {
        const parsed = JSON.parse(payload);
        setTimeout(() => {
          this.onmessage?.({ data: { ok: true, data: parsed } });
        }, 0);
      }

      terminate() {
        // no-op
      }
    }

    (global as { Blob?: unknown }).Blob = FakeBlob as unknown;
    (global as { Worker?: unknown }).Worker = FakeWorker as unknown;

    const payload = {
      items: Array.from({ length: 300 }, (_, idx) => ({ id: idx, name: `item-${idx}` })),
    };
    const raw = JSON.stringify(payload);

    const parsed = await parseJsonWithWorker<typeof payload>(raw, {
      minimumSize: 200,
      timeoutMs: 500,
    });

    expect(parsed.items).toHaveLength(300);
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:json-worker-test');
  });

  it('falls back to direct parse when worker path fails', async () => {
    const createObjectURL = jest.fn().mockReturnValue('blob:json-worker-fallback');
    const revokeObjectURL = jest.fn();
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = revokeObjectURL;

    class FakeBlob {
      constructor(public _parts: unknown[], public _options: { type?: string }) {}
    }

    class FailingWorker {
      onmessage: ((event: { data: unknown }) => void) | null = null;
      onerror: (() => void) | null = null;

      constructor(public _url: string) {}

      postMessage(_payload: string) {
        setTimeout(() => {
          this.onmessage?.({ data: { ok: false, error: 'parse error' } });
        }, 0);
      }

      terminate() {
        // no-op
      }
    }

    (global as { Blob?: unknown }).Blob = FakeBlob as unknown;
    (global as { Worker?: unknown }).Worker = FailingWorker as unknown;

    const payload = { value: 'fallback-ok', count: 2 };
    const raw = JSON.stringify(payload);

    const parsed = await parseJsonWithWorker<typeof payload>(raw, {
      minimumSize: 1,
      timeoutMs: 500,
    });

    expect(parsed).toEqual(payload);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:json-worker-fallback');
  });
});
