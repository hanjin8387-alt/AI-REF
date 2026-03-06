const DIRECT_MAPPINGS: Array<[string, string]> = [
  ['inventory item not found', '인벤토리 항목을 찾을 수 없어요.'],
  ['shopping item not found', '장보기 항목을 찾을 수 없어요.'],
  ['recipe not found', '레시피를 찾을 수 없어요.'],
  ['cooking history entry not found', '요리 이력을 찾을 수 없어요.'],
  ['scan result not found', '스캔 결과를 찾을 수 없어요.'],
  ['only image files are supported', '이미지 파일만 업로드할 수 있어요.'],
  ['image file is too large', '이미지 파일이 너무 커요. 업로드 용량 제한을 확인해 주세요.'],
  ['name cannot be empty', '이름은 비워둘 수 없어요.'],
  ['quantity must be greater than or equal to 0', '수량은 0 이상이어야 해요.'],
  ['no fields to update', '수정할 항목이 없어요.'],
  ['at least one item is required', '최소 1개 이상의 항목이 필요해요.'],
  ['at least one ingredient is required', '최소 1개 이상의 재료가 필요해요.'],
  ['no valid item payload provided', '유효한 항목 정보가 없어요.'],
  ['no valid ingredient payload provided', '유효한 재료 정보가 없어요.'],
  ['sort_by must be one of', '정렬 기준이 올바르지 않아요.'],
  ['mode must be either merge or replace', '복원 모드는 merge 또는 replace만 사용할 수 있어요.'],
  ['recipe id does not match the request body', '레시피 ID가 요청 본문과 일치하지 않아요.'],
  ['recipe payload is required to save generated recommendations', '생성 레시피를 저장하려면 레시피 데이터가 필요해요.'],
  ['servings must be at least 1', '인분은 1 이상이어야 해요.'],
  ['failed to load shopping list', '장보기 목록을 불러오지 못했어요.'],
  ['failed to calculate low-stock suggestions', '저재고 추천 계산에 실패했어요.'],
  ['failed to add low-stock suggestions', '저재고 추천 항목 추가에 실패했어요.'],
  ['failed to add shopping items', '장보기 항목 추가에 실패했어요.'],
  ['failed to add recipe ingredients to shopping list', '레시피 재료를 장보기에 추가하지 못했어요.'],
  ['failed to process shopping checkout', '장보기 처리에 실패했어요.'],
  ['failed to update shopping item', '장보기 항목 수정에 실패했어요.'],
  ['failed to delete shopping item', '장보기 항목 삭제에 실패했어요.'],
  ['failed to update inventory item', '인벤토리 항목 수정에 실패했어요.'],
  ['failed to delete inventory item', '인벤토리 항목 삭제에 실패했어요.'],
  ['failed to restore inventory item', '인벤토리 항목 복구에 실패했어요.'],
  ['failed to complete cooking transaction', '요리 완료 처리에 실패했어요.'],
  ['failed to analyze scan image', '스캔 분석에 실패했어요.'],
  ['failed to export backup', '백업 내보내기에 실패했어요.'],
  ['failed to restore backup', '백업 복원에 실패했어요.'],
  ['shopping feature is not initialized', '장보기 기능이 초기화되지 않았어요. 서버 스키마를 확인해 주세요.'],
];

export function localizeServerError(message: string): string {
  const normalized = (message || '').trim();
  if (!normalized) return '요청을 처리하지 못했어요.';

  const lower = normalized.toLowerCase();
  for (const [needle, localized] of DIRECT_MAPPINGS) {
    if (lower.includes(needle)) return localized;
  }

  if (lower.includes('method not allowed')) return '지원하지 않는 요청 방식이에요.';
  if (lower.includes('internal server error')) return '서버 내부 오류가 발생했어요.';
  if (lower.includes('timeout') || lower.includes('timed out')) return '요청 시간이 초과되었어요. 잠시 후 다시 시도해 주세요.';
  if (lower.includes('failed to fetch') || lower.includes('network request failed') || lower.includes('load failed')) {
    return '서버에 연결하지 못했어요. 네트워크와 서버 상태를 확인해 주세요.';
  }

  return normalized;
}
