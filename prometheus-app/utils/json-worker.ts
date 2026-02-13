type WorkerParseSuccess = { ok: true; data: unknown };
type WorkerParseFailure = { ok: false; error?: string };
type WorkerParseMessage = WorkerParseSuccess | WorkerParseFailure;

const DEFAULT_MIN_WORKER_SIZE = 50_000;
const DEFAULT_WORKER_TIMEOUT_MS = 5000;

function canUseWorkerParser(): boolean {
  return (
    typeof Worker !== 'undefined' &&
    typeof Blob !== 'undefined' &&
    typeof URL !== 'undefined' &&
    typeof URL.createObjectURL === 'function' &&
    typeof URL.revokeObjectURL === 'function'
  );
}

function parseDirect<T>(raw: string): T {
  if (!raw) return {} as T;
  return JSON.parse(raw) as T;
}

export async function parseJsonWithWorker<T>(
  raw: string,
  options?: { minimumSize?: number; timeoutMs?: number }
): Promise<T> {
  const minimumSize = options?.minimumSize ?? DEFAULT_MIN_WORKER_SIZE;
  const timeoutMs = options?.timeoutMs ?? DEFAULT_WORKER_TIMEOUT_MS;

  if (raw.length < minimumSize || !canUseWorkerParser()) {
    return parseDirect<T>(raw);
  }

  const workerScript = `
self.onmessage = function (event) {
  try {
    self.postMessage({ ok: true, data: JSON.parse(event.data) });
  } catch (error) {
    self.postMessage({
      ok: false,
      error: error && error.message ? error.message : String(error)
    });
  }
};`.trim();

  const workerBlob = new Blob([workerScript], { type: 'application/javascript' });
  const objectUrl = URL.createObjectURL(workerBlob);
  const worker = new Worker(objectUrl);

  try {
    const parsed = await new Promise<T>((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error('worker-timeout'));
      }, timeoutMs);

      const cleanup = () => {
        clearTimeout(timeoutId);
        worker.terminate();
        URL.revokeObjectURL(objectUrl);
      };

      worker.onmessage = event => {
        const message = event.data as WorkerParseMessage;
        cleanup();
        if (message?.ok) {
          resolve(message.data as T);
          return;
        }
        reject(new Error(message?.error || 'worker-parse-failed'));
      };

      worker.onerror = () => {
        cleanup();
        reject(new Error('worker-error'));
      };

      worker.postMessage(raw);
    });

    return parsed;
  } catch {
    try {
      worker.terminate();
      URL.revokeObjectURL(objectUrl);
    } catch {
      // ignore cleanup failure
    }
    return parseDirect<T>(raw);
  }
}
