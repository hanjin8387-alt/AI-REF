# Test Engineering Report – 2026-02-13 (Feature Enhancement Cycle)

## Summary
- **테스트 인프라 상태**: ❌ 미구축
- **기존 테스트**: 백엔드 0 / 프론트엔드 1 (`StyledText-test.js`, 레거시)
- **추정 커버리지**: 0%

---

## Infrastructure Status
| 항목 | 백엔드 | 프론트엔드 |
|------|--------|-----------|
| 프레임워크 | ❌ pytest 미설치 | ❌ jest 미설정 (의존성 없음) |
| 설정 파일 | ❌ pytest.ini 없음 | ❌ jest.config 없음 |
| 실행 커맨드 | ❌ | ❌ |
| 커버리지 | ❌ | ❌ |
| CI 연동 | ❌ | ❌ |
| Mock/Fixture | ❌ conftest.py 없음 | ❌ setup 없음 |

---

## Coverage Gap Analysis

### 🔴 Critical Gaps

#### TE-001: 백엔드 pytest 인프라 전무
- **대상**: 전체 백엔드
- **필요**: pytest, pytest-asyncio, httpx (TestClient), conftest.py (Supabase/Gemini/FCM mock)
- **수용기준**: `python -m pytest --co -q` 실행 시 테스트 수집 성공

#### TE-002: `security.py` 인증 테스트 없음
- **대상**: `require_app_token()`, `get_device_id()`, admin 토큰 검증
- **시나리오**: 유효/무효/미전송 토큰, device_id 범위 검증, 화이트리스트
- **Mock**: 없음 (settings mock만 필요)

#### TE-003: `gemini_service.py` AI 응답 파싱 테스트 없음
- **대상**: `analyze_image()`, `generate_recipes()`
- **시나리오**: 정상 JSON, 비정형 텍스트, 빈 응답, API 에러, 타임아웃
- **Mock**: Gemini API 전체 mock

#### TE-004: `inventory_service.py` bulk_upsert 테스트 없음
- **대상**: `bulk_upsert_inventory()`
- **시나리오**: 병합(기존+신규), 동일 이름 수량 합산, 빈 리스트

### 🟡 Warning Gaps

#### TE-005: `scans.py` 업로드 엔드포인트 테스트 없음
- **시나리오**: 정상 업로드, 크기 초과, 비이미지, Gemini 실패 시 상태

#### TE-006: `recipes.py` 추천/요리 완료 통합 테스트 없음
- **시나리오**: 캐시 hit/miss, 재고 차감, 히스토리 기록

#### TE-007: `shopping.py` 체크아웃→재고 반영 통합 테스트 없음
- **시나리오**: 체크아웃 → `bulk_upsert` → 재고 증가

#### TE-008: 프론트 jest 인프라 전무
- **필요**: jest, @testing-library/react-native, jest-expo

#### TE-009: `http-client.ts` 캐시/오프라인/재시도 테스트 없음
- **시나리오**: 캐시 히트/만료, 오프라인 큐잉, 재시도

#### TE-010: `api.ts` API 클라이언트 에러 핸들링 테스트 없음
- **시나리오**: 네트워크 에러, 4xx/5xx, 타임아웃

---

## Recommended Test Architecture
```
prometheus-api/
├── pytest.ini
├── .env.test
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Supabase/Gemini/FCM mock fixtures
│   ├── test_security.py     # TE-002
│   ├── test_scans.py        # TE-005
│   ├── test_inventory.py
│   ├── test_recipes.py      # TE-006
│   ├── test_shopping.py     # TE-007
│   ├── test_admin.py
│   └── test_services/
│       ├── test_gemini_service.py      # TE-003
│       ├── test_inventory_service.py   # TE-004
│       ├── test_recipe_cache.py
│       └── test_storage_utils.py

prometheus-app/
├── jest.config.js
├── __tests__/
│   ├── setup.ts
│   ├── services/
│   │   ├── api.test.ts           # TE-010
│   │   ├── http-client.test.ts   # TE-009
│   │   └── offline-cache.test.ts
│   └── components/
│       ├── InventoryItemCard.test.tsx
│       └── EmptyState.test.tsx
```

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|
| 1 | `tests/conftest.py` 등 (신규) | pytest 인프라 구축 | `pytest --co -q` | 수집 성공 | 🔴 |
| 2 | `tests/test_security.py` (신규) | 보안 모듈 테스트 | `pytest tests/test_security.py -v` | 6+ 케이스 통과 | 🔴 |
| 3 | `tests/test_services/test_gemini_service.py` (신규) | Gemini 서비스 테스트 | `pytest tests/test_services/ -v` | 5+ 케이스 통과 | 🔴 |
| 4 | `tests/test_services/test_inventory_service.py` (신규) | 재고 서비스 테스트 | `pytest tests/test_services/ -v` | 4+ 케이스 통과 | 🔴 |
| 5 | `jest.config.js` 등 (신규) | jest 인프라 구축 | `npm test -- --passWithNoTests` | 실행 성공 | 🟡 |
| 6 | `tests/test_scans.py` (신규) | 스캔 엔드포인트 테스트 | `pytest tests/test_scans.py -v` | 4+ 케이스 | 🟡 |
| 7 | `tests/test_recipes.py` (신규) | 레시피 통합 테스트 | `pytest tests/test_recipes.py -v` | 3+ 케이스 | 🟡 |
| 8 | `tests/test_shopping.py` (신규) | 장보기 통합 테스트 | `pytest tests/test_shopping.py -v` | 3+ 케이스 | 🟡 |
| 9 | `__tests__/services/http-client.test.ts` (신규) | HTTP 클라이언트 테스트 | `npm test` | 5+ 케이스 | 🟡 |
| 10 | `__tests__/services/api.test.ts` (신규) | API 클라이언트 테스트 | `npm test` | 3+ 케이스 | 🟡 |

## Risk & Rollback
- 테스트 인프라 구축은 프로덕션 코드 무관, 롤백 불필요
- `conftest.py` fixture 변경은 전체 테스트에 영향 → fixture 변경 시 전체 실행 필수
