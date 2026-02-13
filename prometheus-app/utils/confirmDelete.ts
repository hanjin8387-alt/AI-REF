import { Alert, Platform } from 'react-native';

const DELETE_CONFIRM_TITLE = '삭제 확인';

function getDeleteConfirmMessage(itemName: string): string {
  return `"${itemName}" 항목을 삭제하시겠어요?`;
}

export function confirmDeleteItem(itemName: string, onConfirm: () => void): void {
  const message = getDeleteConfirmMessage(itemName);
  const browserConfirm = (globalThis as { confirm?: (text: string) => boolean }).confirm;

  if (Platform.OS === 'web' && typeof browserConfirm === 'function') {
    if (browserConfirm(message)) {
      onConfirm();
    }
    return;
  }

  Alert.alert(DELETE_CONFIRM_TITLE, message, [
    { text: '취소', style: 'cancel' },
    { text: '삭제', style: 'destructive', onPress: onConfirm },
  ]);
}
