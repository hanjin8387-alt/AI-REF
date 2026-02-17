export async function saveBackupJsonAsFile(jsonText: string, filename: string): Promise<string | null> {
  if (typeof document === 'undefined') {
    throw new Error('웹 다운로드를 사용할 수 없어요.');
  }

  const blob = new Blob([jsonText], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
  } finally {
    URL.revokeObjectURL(url);
  }

  return null;
}

export async function loadBackupJsonFromFile(_path?: string): Promise<string> {
  if (typeof document === 'undefined') {
    throw new Error('웹 파일 선택기를 사용할 수 없어요.');
  }

  return new Promise((resolve, reject) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';

    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) {
        reject(new Error('선택된 파일이 없어요.'));
        return;
      }

      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('파일을 읽지 못했어요.'));
      reader.readAsText(file, 'utf-8');
    };

    input.click();
  });
}

