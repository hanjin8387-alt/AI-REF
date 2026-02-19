export type StorageCategory = '냉장' | '냉동' | '상온';
export type StorageGroup = StorageCategory | '미분류';

export const STORAGE_CATEGORIES: StorageCategory[] = ['냉장', '냉동', '상온'];
export const STORAGE_GROUPS: StorageGroup[] = ['냉장', '냉동', '상온', '미분류'];

const FROZEN_KEYWORDS = ['냉동', 'freezer', 'frozen', 'freeze'];
const CHILLED_KEYWORDS = ['냉장', 'fridge', 'refriger', 'chill', 'cold'];
const AMBIENT_KEYWORDS = ['상온', '실온', 'ambient', 'pantry', 'roomtemperature'];
const FALLBACK_FROZEN = /(냉동|아이스|ice|frozen|만두|피자)/;
const FALLBACK_CHILLED = /(우유|치즈|요거트|계란|두부|고기|생선|milk|egg|cheese|yogurt|tofu)/;

function detectStorageCategory(value?: string): StorageCategory | null {
  const normalized = (value || '').trim().toLowerCase().replace(/[_\-\s]/g, '');
  if (!normalized) {
    return null;
  }
  if (FROZEN_KEYWORDS.some(keyword => normalized.includes(keyword))) {
    return '냉동';
  }
  if (CHILLED_KEYWORDS.some(keyword => normalized.includes(keyword))) {
    return '냉장';
  }
  if (AMBIENT_KEYWORDS.some(keyword => normalized.includes(keyword))) {
    return '상온';
  }
  return null;
}

export function normalizeStorageCategory(value?: string, fallbackName?: string): StorageCategory {
  const detected = detectStorageCategory(value);
  if (detected) {
    return detected;
  }

  const byName = (fallbackName || '').toLowerCase();
  if (FALLBACK_FROZEN.test(byName)) {
    return '냉동';
  }
  if (FALLBACK_CHILLED.test(byName)) {
    return '냉장';
  }
  return '상온';
}

export function normalizeInventoryStorageCategory(value?: string): StorageGroup {
  return detectStorageCategory(value) ?? '미분류';
}

export function normalizeDisplayUnit(value?: string): string {
  const unit = (value || '').trim();
  if (!unit) return '개';
  if (unit.toLowerCase() === 'unit') return '개';
  return unit;
}
