# Test Engineering Report – 2026-02-13

## Summary
- **테스트 인프라 상태**: ❌ 미구축
- **기존 테스트 수**: 백엔드 0 / 프론트엔드 1 (StyledText-test.js, 레거시)
- **추정 커버리지**: 0%
- **권장 신규 테스트**: 15+ 테스트 파일

---

## Infrastructure Assessment

| 항목 | 백엔드 | 프론트엔드 |
|------|--------|-----------|
| 프레임워크 | ❌ pytest 미설정 | ❌ jest 미설정 (package.json에 jest 의존성 없음) |
| 실행 명령 | ❌ 없음 | ❌ 없음 |
| 커버리지 도구 | ❌ 없음 | ❌ 없음 |
| CI 연동 | ❌ 없음 | ❌ 없음 |

### 초기 설정 작업

#### TE-SETUP-001: 백엔드 pytest 인프라 구축
- `pytest`, `pytest-asyncio`, `httpx` (TestClient용) 설치
- `prometheus-api/tests/conftest.py` – Supabase/Gemini/FCM mock fixture
- `.env.test` – 테스트용 환경변수
- **작업량**: M

#### TE-SETUP-002: 프론트엔드 jest 인프라 구축
- `jest`, `@testing-library/react-native`, `jest-expo` 설치
- `jest.config.js` 설정
- **작업량**: M

---

## Test Gap Analysis

### 🔴 Critical Gaps

#### TE-001: `security.py` 인증/인가 테스트 없음
- **테스트 시나리오**: 토큰 유효/무효/미전송, device_id 범위 밖, 화이트리스트 동작
- **작업량**: S

#### TE-002: `gemini_service.py` AI 파싱 테스트 없음
- **테스트 시나리오**: 정상 JSON 응답, 비정형 응답, 빈 응답, 타임아웃
- **Mock**: Gemini API 완전 mock
- **작업량**: M

#### TE-003: `inventory_service.py` bulk_upsert 테스트 없음
- **테스트 시나리오**: 병합(기존+신규), 동일 이름 수량 합산, 빈 리스트, 유통기한 우선
- **작업량**: M

#### TE-004: `scans.py` 업로드 엔드포인트 테스트 없음
- **테스트 시나리오**: 정상 업로드, 크기 초과, 비이미지 파일, Gemini 실패 시 FAILED 상태
- **작업량**: M

### 🟡 Warning Gaps

#### TE-005: `recipes.py` 추천/요리 완료 플로우 통합 테스트 없음
- **작업량**: M

#### TE-006: `shopping.py` 체크아웃 → 재고 반영 통합 테스트 없음
- **작업량**: M

#### TE-007: `http-client.ts` 캐시/오프라인/재시도 테스트 없음
- **작업량**: M

#### TE-008: `api.ts` API 클라이언트 에러 핸들링 테스트 없음
- **작업량**: M

---

## Recommended Test Architecture
```
prometheus-api/
├── tests/
│   ├── conftest.py
│   ├── test_security.py
│   ├── test_scans.py
│   ├── test_inventory.py
│   ├── test_recipes.py
│   ├── test_shopping.py
│   ├── test_admin.py
│   └── test_services/
│       ├── test_gemini_service.py
│       └── test_inventory_service.py

prometheus-app/
├── __tests__/
│   ├── services/
│   │   ├── api.test.ts
│   │   └── http-client.test.ts
│   └── components/
│       └── InventoryItemCard.test.tsx
```

## Action Items
| # | 제목 | 위험도 | 작업량 |
|---|------|--------|--------|
| TE-SETUP-001 | 백엔드 pytest 인프라 | 🔴 | M |
| TE-SETUP-002 | 프론트 jest 인프라 | 🔴 | M |
| TE-001 | security 테스트 | 🔴 | S |
| TE-002 | gemini_service 테스트 | 🔴 | M |
| TE-003 | inventory_service 테스트 | 🔴 | M |
| TE-004 | scans 엔드포인트 테스트 | 🔴 | M |
| TE-005 | recipes 통합 테스트 | 🟡 | M |
| TE-006 | shopping 통합 테스트 | 🟡 | M |
| TE-007 | http-client 테스트 | 🟡 | M |
| TE-008 | API 클라이언트 테스트 | 🟡 | M |
