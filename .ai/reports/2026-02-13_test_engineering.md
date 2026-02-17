# Test Engineering Report – 2026-02-13

## Summary
- **테스트 인프라 상태**: ❌ 미구축
- **기존 테스트 수**: 백엔드 0 / 프론트엔드 0
- **추정 커버리지**: 백엔드 0% / 프론트엔드 0%
- **권장 신규 테스트**: 27 개 (단위 22 + 통합 5)

---

## Infrastructure Assessment

### 현재 상태
| 항목 | 백엔드 | 프론트엔드 |
|------|--------|-----------|
| 프레임워크 | ❌ pytest 미설치 | ❌ jest 미설치 |
| 실행 명령 | ❌ 없음 | ❌ 없음 (`package.json` scripts에 `test` 없음) |
| 커버리지 도구 | ❌ coverage/pytest-cov 없음 | ❌ istanbul/c8 없음 |
| CI 연동 | ❌ `.github/workflows/` 없음 | ❌ CI 없음 |
| 테스트 환경변수 | ❌ `.env.test` 없음 | ❌ 없음 |

### 상세 분석
- **백엔드** (`prometheus-api/`):
  - `requirements.txt`에 `pytest`, `pytest-asyncio`, `pytest-cov` 없음
  - `pyproject.toml` / `pytest.ini` 없음
  - `tests/` 디렉토리 없음, `test_*.py` 파일 0개
- **프론트엔드** (`prometheus-app/`):
  - `package.json`에 `jest`, `@testing-library/react-native` 없음
  - `devDependencies`에 `react-test-renderer` 존재하지만 미사용
  - `jest.config.*` 없음, `__tests__/` 디렉토리 없음
  - `*.test.ts(x)` 파일 0개 (node_modules 제외)

### 미구축 시 초기 설정 작업

- [ ] **TE-SETUP-001**: 백엔드 테스트 프레임워크 설치
  - `requirements.txt`에 `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx` (TestClient용) 추가
  - `pytest.ini` 또는 `pyproject.toml [tool.pytest.ini_options]` 생성
  - `prometheus-api/tests/__init__.py` 생성
- [ ] **TE-SETUP-002**: 백엔드 공통 fixtures 작성
  - `prometheus-api/tests/conftest.py` 생성
  - mock Supabase Client, mock GeminiService, mock Settings, TestClient fixture
- [ ] **TE-SETUP-003**: 프론트엔드 테스트 프레임워크 설치
  - `jest`, `@testing-library/react-native`, `@testing-library/jest-native`, `ts-jest` 설치
  - `jest.config.ts` 생성 (react-native preset 사용)
  - `jest.setup.ts` 생성 (AsyncStorage, expo-file-system mock)
- [ ] **TE-SETUP-004**: `package.json` scripts에 `test`, `test:coverage` 추가
- [ ] **TE-SETUP-005**: `.env.test` 환경변수 파일 생성 (더미 키 포함)

---

## Test Gap Analysis

### 🔴 Critical Gaps (반드시 추가)

#### TE-001: GeminiService – AI 응답 파싱
- **파일**: `prometheus-api/app/services/gemini_service.py` (309줄, 15함수)
- **테스트 파일**: `prometheus-api/tests/test_services/test_gemini_service.py`
- **테스트 시나리오**:
  1. `analyze_food_image()` – 정상 JSON 파싱, 복수 아이템 반환
  2. `analyze_food_image()` – Gemini API 에러 (NotFound → fallback 모델 전환)
  3. `analyze_food_image()` – 비정상 JSON 응답 (파싱 실패 시 빈 리스트)
  4. `analyze_receipt_image()` – 영수증 파싱 정상 (store, date, items 추출)
  5. `analyze_receipt_image()` – 빈 이미지 / invalid mime type
  6. `_coerce_expiry_days()` – 문자열, 숫자, None 경계값
  7. `_format_expiry_days()` – int, str, None 변환
  8. `_build_model_candidates()` – 모델 후보 리스트 생성
  9. `_generate_with_model_fallback()` – 첫 번째 모델 실패 → 두번째 성공
  10. `generate_recipe_recommendations()` – 재고 기반 레시피 추천 정상/에러
- **Mock 필요**: `google.generativeai` (genai), `GenerativeModel.generate_content`
- **작업량**: L

#### TE-002: InventoryService – 핵심 비즈니스 로직
- **파일**: `prometheus-api/app/services/inventory_service.py` (174줄, 5함수)
- **테스트 파일**: `prometheus-api/tests/test_services/test_inventory_service.py`
- **테스트 시나리오**:
  1. `bulk_upsert_inventory()` – 신규 아이템 추가 (added_count 검증)
  2. `bulk_upsert_inventory()` – 기존 아이템 수량 병합 (updated_count 검증)
  3. `bulk_upsert_inventory()` – 빈 목록 입력 → (0, 0, [])
  4. `bulk_upsert_inventory()` – 이름 없는 아이템 스킵
  5. `bulk_upsert_inventory()` – 대소문자 무시 병합 (name.lower())
  6. `bulk_upsert_inventory()` – 만료일 비교 (더 이른 날짜 유지)
  7. `bulk_upsert_inventory()` – 수량 ≤ 0 필터링
  8. `_to_iso_date()` – datetime, str, None 변환
  9. `log_inventory_change()` – 로그 기록 정상
  10. `_write_inventory_logs()` – DB 에러 시 best-effort (warning 로그만)
- **Mock 필요**: Supabase Client (`table().select().eq().execute()`)
- **작업량**: M

#### TE-003: Scans API – 파일 업로드 + AI 파이프라인
- **파일**: `prometheus-api/app/api/scans.py` (473줄, 14함수)
- **테스트 파일**: `prometheus-api/tests/test_scans.py`
- **테스트 시나리오**:
  1. `upload_scan()` – camera 이미지 업로드 → Gemini 분석 → 재고 반영 → scan 저장
  2. `upload_scan()` – receipt 이미지 업로드 → 영수증 파싱 + 가격 기록
  3. `upload_scan()` – 파일 크기 초과 에러
  4. `upload_scan()` – Gemini 서비스 에러 시 scan status=failed
  5. `get_scan_result()` – 존재하는 scan 조회
  6. `get_scan_result()` – 존재하지 않는 scan → 404
  7. `lookup_barcode()` – Open Food Facts API 정상 응답
  8. `lookup_barcode()` – 바코드 미등록 → 404
  9. `_normalize_storage_category()` – 냉장/냉동/상온 정규화
  10. `_extract_receipt_metadata()` – 가게명, 날짜 추출
  11. `_safe_amount()` – 금액 파싱 (정상, None, 비정상)
- **Mock 필요**: Supabase Client, GeminiService, httpx (Open Food Facts)
- **작업량**: XL

#### TE-004: Security – 인증/인가 경계
- **파일**: `prometheus-api/app/core/security.py` (56줄, 2함수)
- **테스트 파일**: `prometheus-api/tests/test_security.py`
- **테스트 시나리오**:
  1. `require_app_token()` – 유효한 토큰 → 통과
  2. `require_app_token()` – 잘못된 토큰 → 401
  3. `require_app_token()` – 토큰 헤더 누락 → 401
  4. `require_app_token()` – `require_app_token=False` 설정 시 → 토큰 검사 스킵
  5. `require_app_token()` – 서버 APP_TOKEN 미설정 → 500
  6. `get_device_id()` – 정상 device ID → 반환
  7. `get_device_id()` – 헤더 누락 → 400
  8. `get_device_id()` – 길이 부적합 (< 8 또는 > 128) → 400
  9. `get_device_id()` – 허용 목록 기능 (allowed_device_ids에 없는 ID → 403)
  10. `get_device_id()` – 허용 목록 비어있으면 모든 ID 허용
- **Mock 필요**: Settings (get_settings override)
- **작업량**: S

---

### 🟡 Warning Gaps

#### TE-005: Recipes API – 추천→요리→차감 플로우
- **파일**: `prometheus-api/app/api/recipes.py` (449줄, 12함수)
- **테스트 파일**: `prometheus-api/tests/test_recipes.py`
- **테스트 시나리오**:
  1. `get_recommendations()` – 캐시 히트 시 Gemini 호출 안 함
  2. `get_recommendations()` – `force_refresh=True` → Gemini 재호출
  3. `get_recommendations()` – 재고 0개 → 빈 추천
  4. `complete_cooking()` – 재고 차감 + cooking_history 기록
  5. `complete_cooking()` – 레시피 미존재 → 404
  6. `get_favorite_recipes()` – 즐겨찾기 목록 조회
  7. `add_favorite_recipe()` / `remove_favorite_recipe()` – 토글 동작
- **Mock 필요**: Supabase Client, GeminiService, RecipeCache
- **작업량**: L

#### TE-006: Shopping API – 체크아웃→재고 반영
- **파일**: `prometheus-api/app/api/shopping.py` (734줄, 18함수)
- **테스트 파일**: `prometheus-api/tests/test_shopping.py`
- **테스트 시나리오**:
  1. `add_shopping_items()` – 수동 아이템 추가
  2. `add_shopping_from_recipe()` – 레시피 기반 쇼핑 목록 생성
  3. `checkout_shopping_items()` – 체크아웃 → 재고 반영 (addToInventory=true)
  4. `checkout_shopping_items()` – 재고 반영 없이 체크아웃 (addToInventory=false)
  5. `get_low_stock_suggestions()` – 소비 패턴 기반 제안
  6. `_aggregate_items()` – 동일 아이템 합산
  7. `_parse_quantity()` – 수량 파싱 에러/경계값
  8. `update_shopping_item()` / `delete_shopping_item()` – CRUD
- **Mock 필요**: Supabase Client, `bulk_upsert_inventory`
- **작업량**: L

#### TE-007: 프론트엔드 api.ts – API 클라이언트 에러 핸들링
- **파일**: `prometheus-app/services/api.ts` (502줄, 39함수)
- **테스트 파일**: `prometheus-app/__tests__/services/api.test.ts`
- **테스트 시나리오**:
  1. `uploadScan()` – FormData 구성 + 타임아웃 설정 검증
  2. `getInventory()` – 쿼리파라미터 조합
  3. `completeCooking()` – 성공 후 캐시 무효화 확인
  4. `normalizeImageExtension()` / `extensionFromMimeType()` – 확장자 변환
  5. 네트워크 에러 시 `ApiResponse.error` 반환 확인
- **Mock 필요**: `HttpClient` (fetch)
- **작업량**: M

#### TE-008: 프론트엔드 http-client.ts – 캐시, 오프라인 폴백, 재시도
- **파일**: `prometheus-app/services/http-client.ts` (388줄, 24함수)
- **테스트 파일**: `prometheus-app/__tests__/services/http-client.test.ts`
- **테스트 시나리오**:
  1. `request()` – 캐시 TTL 내 요청 → 캐시 히트
  2. `request()` – 오프라인 시 → 캐시 폴백 + `offline: true`
  3. `request()` – 오프라인 + 뮤테이션 → 큐 저장
  4. `retryPendingMutations()` – 저장된 뮤테이션 재전송
  5. `loadOrCreateDeviceId()` – 최초 생성 + 파일 저장 확인
  6. `buildHeaders()` – X-App-Token, X-Device-ID 헤더 포함
  7. `invalidateCache()` – 프리픽스 매칭 삭제
  8. `localizeServerError()` – 에러 메시지 한글 변환
- **Mock 필요**: `fetch`, `expo-file-system`, `AsyncStorage`
- **작업량**: L

---

### 🟢 Nice-to-Have

#### TE-009: Notifications API – 단순 CRUD
- **파일**: `prometheus-api/app/api/notifications.py` (75줄, 2함수)
- **테스트 파일**: `prometheus-api/tests/test_notifications.py`
- **테스트 시나리오**:
  1. `get_notifications()` – 페이지네이션, `only_unread` 필터
  2. `mark_notifications_read()` – 전체 읽음 / 특정 ID 읽음
- **Mock 필요**: Supabase Client
- **작업량**: S

#### TE-010: Stats API – 집계 로직 정확성
- **파일**: `prometheus-api/app/api/stats.py` (205줄, 5함수)
- **테스트 파일**: `prometheus-api/tests/test_stats.py`
- **테스트 시나리오**:
  1. `get_stats_summary()` – period별 기간 필터 (week/month/all)
  2. `get_stats_summary()` – cooking_history 테이블 미존재 시 graceful
  3. `get_price_history()` – 이름 필터/날짜 범위 확인
  4. `_period_start()` – 경계값 (week, month, all, unknown)
- **Mock 필요**: Supabase Client
- **작업량**: M

---

## Recommended Test Architecture
```
prometheus-api/
├── pytest.ini                           ← asyncio_mode=auto, testpaths
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      ← fixtures (mock DB, mock Gemini, TestClient)
│   ├── test_security.py                 ← TE-004
│   ├── test_scans.py                    ← TE-003
│   ├── test_recipes.py                  ← TE-005
│   ├── test_shopping.py                 ← TE-006
│   ├── test_notifications.py            ← TE-009
│   ├── test_stats.py                    ← TE-010
│   └── test_services/
│       ├── __init__.py
│       ├── test_gemini_service.py       ← TE-001
│       └── test_inventory_service.py    ← TE-002

prometheus-app/
├── jest.config.ts                       ← react-native preset, ts-jest
├── jest.setup.ts                        ← AsyncStorage/FileSystem mock
├── __tests__/
│   └── services/
│       ├── api.test.ts                  ← TE-007
│       └── http-client.test.ts          ← TE-008
```

---

## Action Items
| # | 제목 | 위험도 | 작업량 | 유형 |
|---|------|--------|--------|------|
| TE-SETUP-001 | 백엔드 pytest 설치 + 설정 | 🔴 | S | 인프라 |
| TE-SETUP-002 | 백엔드 conftest.py (mock fixtures) | 🔴 | M | 인프라 |
| TE-SETUP-003 | 프론트엔드 jest 설치 + 설정 | 🔴 | S | 인프라 |
| TE-SETUP-004 | package.json test scripts 추가 | 🔴 | S | 인프라 |
| TE-SETUP-005 | .env.test 환경변수 파일 생성 | 🟡 | S | 인프라 |
| TE-001 | GeminiService 단위 테스트 | 🔴 | L | 단위 테스트 |
| TE-002 | InventoryService 단위 테스트 | 🔴 | M | 단위 테스트 |
| TE-003 | Scans API 통합 테스트 | 🔴 | XL | 통합 테스트 |
| TE-004 | Security 단위 테스트 | 🔴 | S | 단위 테스트 |
| TE-005 | Recipes API 통합 테스트 | 🟡 | L | 통합 테스트 |
| TE-006 | Shopping API 통합 테스트 | 🟡 | L | 통합 테스트 |
| TE-007 | api.ts 클라이언트 테스트 | 🟡 | M | 단위 테스트 |
| TE-008 | http-client.ts 테스트 | 🟡 | L | 단위 테스트 |
| TE-009 | Notifications API 테스트 | 🟢 | S | 통합 테스트 |
| TE-010 | Stats API 테스트 | 🟢 | M | 통합 테스트 |

---

## Codex Task List

> 아래 Task는 순서대로 실행합니다. 각 Task 완료 후 커밋합니다.

---

### Phase 0: 인프라 셋업

#### Task 0-1: 백엔드 테스트 의존성 설치
- **파일**: `prometheus-api/requirements.txt`
- **수정 요지**: 파일 끝에 아래 추가:
  ```
  pytest>=8.0.0
  pytest-asyncio>=0.23.0
  pytest-cov>=5.0.0
  ```
- **테스트 명령**: `cd prometheus-api && pip install -r requirements.txt`
- **커밋**: `chore(test): add pytest dependencies to requirements.txt`

#### Task 0-2: pytest 설정 파일 생성
- **파일**: `prometheus-api/pytest.ini` [NEW]
- **내용**:
  ```ini
  [pytest]
  asyncio_mode = auto
  testpaths = tests
  python_files = test_*.py
  python_classes = Test*
  python_functions = test_*
  addopts = -v --tb=short
  ```
- **테스트 명령**: `cd prometheus-api && python -m pytest --co` (collect only)
- **커밋**: `chore(test): add pytest.ini configuration`

#### Task 0-3: 백엔드 테스트 디렉토리 + conftest.py 생성
- **파일**: `prometheus-api/tests/__init__.py` [NEW] (빈 파일)
- **파일**: `prometheus-api/tests/test_services/__init__.py` [NEW] (빈 파일)
- **파일**: `prometheus-api/tests/conftest.py` [NEW]
- **수정 요지**: 아래 fixtures 구현:
  - `mock_settings()` – `app.core.config.get_settings`를 오버라이드, 더미 환경변수 반환
  - `mock_db()` – Supabase `Client`의 `MagicMock`, `table().select().eq().execute()` 체인 지원
  - `mock_gemini()` – `GeminiService`의 `MagicMock`, `analyze_food_image()` / `analyze_receipt_image()` / `generate_recipe_recommendations()` stub
  - `test_client(mock_settings, mock_db, mock_gemini)` – FastAPI `TestClient` 생성, `get_db` / `get_settings` / `get_gemini_service` 의존성 오버라이드
  - `device_headers()` – `{"X-App-Token": "test-token", "X-Device-ID": "test-device-12345678"}`
- **테스트 명령**: `cd prometheus-api && python -m pytest --co`
- **커밋**: `chore(test): initialize test infrastructure with conftest.py`

#### Task 0-4: .env.test 파일 생성
- **파일**: `prometheus-api/.env.test` [NEW]
- **내용**:
  ```env
  APP_TOKEN=test-token
  REQUIRE_APP_TOKEN=true
  SUPABASE_URL=https://test.supabase.co
  SUPABASE_KEY=eyJ-test-key
  GEMINI_API_KEY=test-gemini-key
  GEMINI_MODEL=gemini-3-flash-preview
  ENVIRONMENT=test
  DEBUG=true
  CORS_ORIGINS=http://localhost:3000
  ```
- **커밋**: `chore(test): add .env.test for test environment`

#### Task 0-5: 프론트엔드 테스트 프레임워크 설치
- **파일**: `prometheus-app/package.json`
- **수정 요지**:
  - `devDependencies`에 추가: `jest`, `@testing-library/react-native`, `@testing-library/jest-native`, `ts-jest`, `@types/jest`
  - `scripts`에 추가: `"test": "jest"`, `"test:coverage": "jest --coverage"`
- **테스트 명령**: `cd prometheus-app && npm install && npx jest --version`
- **커밋**: `chore(test): add jest and testing-library dependencies`

#### Task 0-6: jest 설정 + setup 파일 생성
- **파일**: `prometheus-app/jest.config.ts` [NEW]
- **수정 요지**: react-native preset, `transformIgnorePatterns` 설정, `setupFiles: ['./jest.setup.ts']`
- **파일**: `prometheus-app/jest.setup.ts` [NEW]
- **수정 요지**: `@react-native-async-storage/async-storage` mock, `expo-file-system` mock, global `fetch` mock
- **테스트 명령**: `cd prometheus-app && npx jest --passWithNoTests`
- **커밋**: `chore(test): add jest.config.ts and jest.setup.ts`

---

### Phase 1: Critical Tests (🔴)

#### Task 1-1: TE-004 – Security 단위 테스트
- **파일**: `prometheus-api/tests/test_security.py` [NEW]
- **대상 함수**: `require_app_token()`, `get_device_id()` in `app/core/security.py`
- **테스트 함수 목록**:
  - `test_require_app_token_valid()` – 유효 토큰 → 예외 없음
  - `test_require_app_token_invalid()` – 잘못된 토큰 → `HTTPException(401)`
  - `test_require_app_token_missing_header()` – 헤더 없음 → `HTTPException(401)`
  - `test_require_app_token_disabled()` – `require_app_token=False` → 통과
  - `test_require_app_token_server_not_configured()` – `app_token=""` → `HTTPException(500)`
  - `test_get_device_id_valid()` – 정상 ID → 반환
  - `test_get_device_id_missing()` – 헤더 없음 → `HTTPException(400)`
  - `test_get_device_id_too_short()` – 7자 → `HTTPException(400)`
  - `test_get_device_id_too_long()` – 129자 → `HTTPException(400)`
  - `test_get_device_id_not_in_allowlist()` – `allowed_device_ids` 설정 시 미포함 → `HTTPException(403)`
- **테스트 명령**: `cd prometheus-api && python -m pytest tests/test_security.py -v`
- **커밋**: `test(core): TE-004 add security unit tests`

#### Task 1-2: TE-002 – InventoryService 단위 테스트
- **파일**: `prometheus-api/tests/test_services/test_inventory_service.py` [NEW]
- **대상 함수**: `bulk_upsert_inventory()`, `_to_iso_date()`, `log_inventory_change()`, `_write_inventory_logs()` in `app/services/inventory_service.py`
- **테스트 함수 목록**:
  - `test_bulk_upsert_new_items()` – 신규 2개 → added=2, updated=0
  - `test_bulk_upsert_merge_existing()` – 기존 아이템에 수량 합산
  - `test_bulk_upsert_empty_list()` – 빈 리스트 → (0, 0, [])
  - `test_bulk_upsert_skip_no_name()` – 이름 없는 아이템 제외
  - `test_bulk_upsert_case_insensitive_merge()` – "사과" == "사과" 병합
  - `test_bulk_upsert_earliest_expiry()` – 더 이른 만료일 유지
  - `test_bulk_upsert_zero_quantity_skipped()` – 합산 ≤ 0 제외
  - `test_to_iso_date_datetime()` – datetime 객체 → ISO 문자열
  - `test_to_iso_date_string()` – str 그대로 반환
  - `test_to_iso_date_none()` – None → None
  - `test_write_inventory_logs_db_error_swallowed()` – DB 에러 시 warning 로그만
- **테스트 명령**: `cd prometheus-api && python -m pytest tests/test_services/test_inventory_service.py -v`
- **커밋**: `test(service): TE-002 add inventory_service unit tests`

#### Task 1-3: TE-001 – GeminiService 단위 테스트
- **파일**: `prometheus-api/tests/test_services/test_gemini_service.py` [NEW]
- **대상 함수**: 모든 `GeminiService` 메서드 in `app/services/gemini_service.py`
- **테스트 함수 목록**:
  - `test_analyze_food_image_success()` – mock Gemini → JSON 파싱 → FoodItem 리스트
  - `test_analyze_food_image_model_fallback()` – 첫 모델 NotFound → 두번째 성공
  - `test_analyze_food_image_invalid_json()` – JSON 아닌 응답 → 빈 리스트
  - `test_analyze_receipt_image_success()` – 영수증 파싱 (store, date, items)
  - `test_analyze_receipt_image_empty_response()` – 빈 응답 → 빈 결과
  - `test_coerce_expiry_days_int()` – 정수 입력
  - `test_coerce_expiry_days_string()` – "7일" → 7
  - `test_coerce_expiry_days_none()` – None → None
  - `test_build_model_candidates()` – 후보 리스트 길이/순서 검증
  - `test_generate_recipe_recommendations()` – 재고 기반 추천 정상
- **테스트 명령**: `cd prometheus-api && python -m pytest tests/test_services/test_gemini_service.py -v`
- **커밋**: `test(service): TE-001 add gemini_service unit tests`

#### Task 1-4: TE-003 – Scans API 통합 테스트
- **파일**: `prometheus-api/tests/test_scans.py` [NEW]
- **대상 함수**: `upload_scan()`, `get_scan_result()`, `lookup_barcode()` + 헬퍼 함수들 in `app/api/scans.py`
- **테스트 함수 목록**:
  - `test_upload_scan_camera_success()` – POST `/scans/upload` file + source_type=camera → 200
  - `test_upload_scan_receipt_success()` – source_type=receipt → 200 + 가격 기록
  - `test_upload_scan_oversize_file()` – 8MB 초과 → 413 에러
  - `test_upload_scan_gemini_failure()` – Gemini 에러 → scan status=failed
  - `test_get_scan_result_found()` – GET `/scans/{scan_id}` → 200
  - `test_get_scan_result_not_found()` – 없는 scan_id → 404
  - `test_lookup_barcode_found()` – GET `/scans/barcode?code=...` → 200 (httpx mock)
  - `test_lookup_barcode_not_found()` – Open Food Facts 미등록 → 404
  - `test_normalize_storage_category()` – 냉장/냉동/상온 정규화
  - `test_extract_receipt_metadata()` – 가게명 + 날짜 추출
  - `test_safe_amount()` – "1,500" → 1500.0, None → None
- **테스트 명령**: `cd prometheus-api && python -m pytest tests/test_scans.py -v`
- **커밋**: `test(api): TE-003 add scans API integration tests`

---

### Phase 2: Warning Tests (🟡)

#### Task 2-1: TE-005 – Recipes API 통합 테스트
- **파일**: `prometheus-api/tests/test_recipes.py` [NEW]
- **대상 함수**: `get_recommendations()`, `complete_cooking()`, `get_favorite_recipes()`, `add_favorite_recipe()`, `remove_favorite_recipe()` in `app/api/recipes.py`
- **테스트 함수 목록**:
  - `test_get_recommendations_cached()` – 캐시 존재 시 Gemini 미호출
  - `test_get_recommendations_force_refresh()` – Gemini 호출 확인
  - `test_get_recommendations_empty_inventory()` – 빈 재고 → `{"recipes": []}`
  - `test_complete_cooking_success()` – 재고 차감 + history 기록
  - `test_complete_cooking_recipe_not_found()` – 404
  - `test_favorite_add_remove()` – 즐겨찾기 추가/삭제
  - `test_get_cooking_history()` – 페이지네이션
- **테스트 명령**: `cd prometheus-api && python -m pytest tests/test_recipes.py -v`
- **커밋**: `test(api): TE-005 add recipes API integration tests`

#### Task 2-2: TE-006 – Shopping API 통합 테스트
- **파일**: `prometheus-api/tests/test_shopping.py` [NEW]
- **대상 함수**: `add_shopping_items()`, `checkout_shopping_items()`, `get_low_stock_suggestions()`, `_aggregate_items()`, `_parse_quantity()` in `app/api/shopping.py`
- **테스트 함수 목록**:
  - `test_add_shopping_items_manual()` – POST 수동 추가
  - `test_add_shopping_from_recipe()` – 레시피 기반 추가
  - `test_checkout_with_inventory()` – 체크아웃 + 재고 반영
  - `test_checkout_without_inventory()` – 체크아웃만
  - `test_low_stock_suggestions()` – 소비 패턴 분석
  - `test_aggregate_items()` – 동일 아이템 합산
  - `test_parse_quantity_edge_cases()` – "1.5", "0", 음수
  - `test_update_delete_shopping_item()` – CRUD
- **테스트 명령**: `cd prometheus-api && python -m pytest tests/test_shopping.py -v`
- **커밋**: `test(api): TE-006 add shopping API integration tests`

#### Task 2-3: TE-007 – api.ts 클라이언트 테스트
- **파일**: `prometheus-app/__tests__/services/api.test.ts` [NEW]
- **대상 함수**: `ApiClient` 클래스 in `services/api.ts`
- **테스트 함수 목록**:
  - `test uploadScan constructs FormData correctly` – imageUri → FormData field 확인
  - `test getInventory passes query params` – category, sortBy, limit, offset 검증
  - `test completeCooking invalidates cache` – `invalidateCache` 호출 확인
  - `test normalizeImageExtension` – "JPEG" → "jpg", "png" → "png", undefined → "jpg"
  - `test extensionFromMimeType` – "image/jpeg" → "jpg"
  - `test network error returns ApiResponse with error` – fetch reject → `{error: "..."}`
- **테스트 명령**: `cd prometheus-app && npx jest __tests__/services/api.test.ts`
- **커밋**: `test(frontend): TE-007 add api.ts client unit tests`

#### Task 2-4: TE-008 – http-client.ts 테스트
- **파일**: `prometheus-app/__tests__/services/http-client.test.ts` [NEW]
- **대상 함수**: `HttpClient` 클래스 in `services/http-client.ts`
- **테스트 함수 목록**:
  - `test request uses cache within TTL` – 두 번째 호출 시 fetch 미호출
  - `test request returns offline fallback` – fetch throw → 캐시 데이터 반환 + `offline: true`
  - `test mutation enqueued when offline` – POST + offline → `enqueueMutation` 호출
  - `test retryPendingMutations replays` – 큐에서 꺼내 fetch 재시도
  - `test loadOrCreateDeviceId creates new ID` – 파일 없을 시 UUID 생성
  - `test buildHeaders includes tokens` – X-App-Token, X-Device-ID 포함
  - `test invalidateCache removes prefixed keys` – prefix 매칭 삭제
  - `test localizeServerError translates messages` – 영어 → 한글 변환
- **테스트 명령**: `cd prometheus-app && npx jest __tests__/services/http-client.test.ts`
- **커밋**: `test(frontend): TE-008 add http-client.ts unit tests`

---

### Phase 3: Nice-to-Have Tests (🟢)

#### Task 3-1: TE-009 – Notifications API 테스트
- **파일**: `prometheus-api/tests/test_notifications.py` [NEW]
- **대상 함수**: `get_notifications()`, `mark_notifications_read()` in `app/api/notifications.py`
- **테스트 함수 목록**:
  - `test_get_notifications_pagination()` – limit/offset 동작
  - `test_get_notifications_unread_filter()` – only_unread=True
  - `test_mark_read_specific_ids()` – 특정 ID만 읽음 처리
  - `test_mark_read_all()` – 빈 ids → 전체 읽음
- **테스트 명령**: `cd prometheus-api && python -m pytest tests/test_notifications.py -v`
- **커밋**: `test(api): TE-009 add notifications API tests`

#### Task 3-2: TE-010 – Stats API 테스트
- **파일**: `prometheus-api/tests/test_stats.py` [NEW]
- **대상 함수**: `get_stats_summary()`, `get_price_history()`, `_period_start()` in `app/api/stats.py`
- **테스트 함수 목록**:
  - `test_stats_summary_week()` – period=week 기간 필터
  - `test_stats_summary_missing_table()` – cooking_history 없을 시 graceful
  - `test_price_history_name_filter()` – 이름 필터
  - `test_period_start_boundaries()` – week/month/all/unknown
- **테스트 명령**: `cd prometheus-api && python -m pytest tests/test_stats.py -v`
- **커밋**: `test(api): TE-010 add stats API tests`

---

### Phase 4: 커버리지 확인

#### Task 4-1: 백엔드 커버리지 리포트
- **명령**: `cd prometheus-api && python -m pytest --cov=app --cov-report=html --cov-report=term-missing`
- **목표**: 핵심 모듈(`services/`, `core/security.py`) ≥ 80%

#### Task 4-2: 프론트엔드 커버리지 리포트
- **명령**: `cd prometheus-app && npx jest --coverage`
- **목표**: `services/` ≥ 70%

---

### PR 요약 템플릿
```
## Test Engineering – 2026-02-13
- 테스트 인프라 구축: ✅ (pytest + jest)
- 신규 테스트: 27개 추가
- 커버리지: 0% → 목표 70%+
- 참조: .ai/reports/2026-02-13_test_engineering.md
```
