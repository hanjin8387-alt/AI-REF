# DB Schema 점검 지침

## 개요
PostgreSQL (Supabase) 스키마와 애플리케이션 코드 간의 일관성을 점검합니다.

## 주요 점검 파일
- `prometheus-api/schema.sql` — DDL 정의
- `prometheus-api/app/schemas/schemas.py` — Pydantic 모델
- `prometheus-api/app/api/*.py` — 쿼리 실행 코드
- `prometheus-app/services/api.types.ts` — 프론트엔드 타입

## 테이블별 점검 매트릭스

| 테이블 | FK 확인 | 인덱스 확인 | RLS 확인 | 타입 매핑 확인 |
|--------|---------|-----------|---------|--------------|
| `devices` | - | ✓ | ✓ | ✓ |
| `scans` | ✓ | ✓ | ✓ | ✓ |
| `inventory` | ✓ | ✓ | ✓ | ✓ |
| `recipes` | ✓ | ✓ | ✓ | ✓ |
| `favorite_recipes` | ✓ | ✓ | ✓ | ✓ |
| `cooking_history` | ✓ | ✓ | ✓ | ✓ |
| `notifications` | ✓ | ✓ | ✓ | ✓ |
| `shopping_items` | ✓ | ✓ | ✓ | ✓ |
| `inventory_logs` | ✓ | ✓ | ✓ | ✓ |
| `price_history` | ✓ | ✓ | ✓ | ✓ |

## 알려진 이슈 (이전 리뷰에서 확인)
1. `cooking_history.recipe_id UUID REFERENCES recipes(id)` — AI 생성 레시피 ID는 UUID가 아님
2. `favorite_recipes.recipe_id VARCHAR(255)` — UUID가 아닌 문자열 사용

## 타입 매핑 대조표

| SQL 타입 | Python 타입 | TypeScript 타입 | 비고 |
|----------|-------------|-----------------|------|
| `UUID` | `str` | `string` | |
| `VARCHAR(N)` | `str` | `string` | |
| `TEXT` | `str` | `string` | |
| `DECIMAL(M,N)` | `float` | `number` | 정밀도 손실 주의 |
| `INTEGER` | `int` | `number` | |
| `BOOLEAN` | `bool` | `boolean` | |
| `TIMESTAMPTZ` | `datetime` | `string` (ISO) | |
| `DATE` | `date` / `str` | `string` | |
| `JSONB` | `dict` / `list` | `object` / `array` | 스키마 검증 필요 |

## Stored Function 점검
- `complete_cooking_transaction()` — 파라미터 타입/순서가 호출 코드와 일치하는지
- `update_updated_at_column()` — 모든 대상 테이블에 트리거 적용 확인
