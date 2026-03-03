# Code Quality 점검 지침

## 개요
코드 중복, 명명 규칙, 에러 처리 일관성 등 코드 품질을 점검합니다.

## 중복 코드 탐지

### 알려진 중복 패턴 (이전 리뷰에서 확인)
1. `normalizeStorageCategory` — `scans.py`, `inventory.py`, `scan.tsx`, `inventory.tsx`에 4회 중복
2. `_normalize_unit` / `normalizeDisplayUnit` — 백엔드/프론트엔드에 각각 중복
3. 에러 응답 형식 — 각 라우터에서 개별적으로 HTTPException 구성

### 새로운 중복 탐지
- 3줄 이상의 동일/유사 코드 블록이 2개 이상 파일에 나타나는 경우
- 같은 비즈니스 로직이 함수명만 다르게 구현된 경우
- 프론트엔드와 백엔드에서 동일한 검증/변환 로직이 반복되는 경우

## 명명 규칙

### Python (PEP 8)
- 함수/변수: `snake_case`
- 클래스: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

### TypeScript
- 함수/변수: `camelCase`
- 타입/인터페이스: `PascalCase`
- 상수: `UPPER_SNAKE_CASE`
- 컴포넌트: `PascalCase`

## 에러 처리 일관성
- `try/except Exception` (bare) — 구체적 예외 사용 권장
- `except: pass` — silent 무시 탐지
- 한국어/영어 혼용 에러 메시지 — 에러 코드 표준화 필요
- HTTPException `detail` 형식 불일치 (문자열 vs dict)

## TODO/FIXME 감사
- 모든 `TODO`, `FIXME`, `HACK`, `XXX`, `TEMP` 주석 수집
- 각각에 대해 심각도 및 해결 여부 판단
