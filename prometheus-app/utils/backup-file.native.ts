import * as FileSystem from 'expo-file-system/legacy';

export async function saveBackupJsonAsFile(jsonText: string, filename: string): Promise<string | null> {
  const basePath = FileSystem.documentDirectory;
  if (!basePath) {
    throw new Error('로컬 문서 디렉터리를 찾을 수 없어요.');
  }

  const fileUri = `${basePath}${filename}`;
  await FileSystem.writeAsStringAsync(fileUri, jsonText, { encoding: FileSystem.EncodingType.UTF8 });
  return fileUri;
}

export async function loadBackupJsonFromFile(path?: string): Promise<string> {
  const trimmedPath = (path || '').trim();
  if (!trimmedPath) {
    throw new Error('백업 파일 경로를 입력해 주세요.');
  }

  return await FileSystem.readAsStringAsync(trimmedPath, { encoding: FileSystem.EncodingType.UTF8 });
}

