export function getErrorMessage(error: unknown, fallback = '알 수 없는 오류가 발생했어요.') {
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function fireAndForget(
  task: Promise<unknown>,
  onError?: (message: string) => void,
  fallback = '알 수 없는 오류가 발생했어요.'
) {
  task.catch(error => {
    console.error('[async]', error);
    onError?.(getErrorMessage(error, fallback));
  });
}

