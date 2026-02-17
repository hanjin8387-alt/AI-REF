# Agent 03: Test Engineering

> **에이전트 역할**: 테스트 커버리지·자동화·전략 수립  
> **결과 파일**: `.ai/reports/YYYY-MM-DD_test_engineering.md`

---

## Mission

PROMETHEUS의 테스트 인프라를 점검하고, 누락된 테스트를 식별하며, 자동화 테스트 전략을 수립한다. 현재 테스트 인프라가 구축되지 않은 경우 초기 설정 가이드를 제공한다.

## Scope

- 백엔드 테스트: `prometheus-api/` (pytest)
- 프론트엔드 테스트: `prometheus-app/` (jest / @testing-library/react-native)
- E2E 테스트 전략 수립
- CI/CD 테스트 파이프라인 설계

## Non-Goals

- 코드 품질 자체 리뷰 → Agent 01 (Code Review)
- 성능 벤치마크 → Agent 05 (Perf & Reliability)

---

## Inputs (우선순위 파일 및 확인 포인트)

### 테스트 인프라 확인
| 확인 항목 | 경로 | 체크 포인트 |
|-----------|------|-------------|
| pytest 설정 | `prometheus-api/pytest.ini` 또는 `pyproject.toml` | 존재 여부, 설정 내용 |
| jest 설정 | `prometheus-app/jest.config.*` 또는 `package.json[jest]` | 존재 여부 |
| 테스트 파일 | `**/test_*.py`, `**/*.test.ts(x)` | 존재 여부, 개수 |
| CI/CD | `.github/workflows/`, `.gitlab-ci.yml` | 테스트 자동 실행 여부 |
| 커버리지 도구 | `coverage`, `istanbul`/`c8` | 설정 여부 |

### 테스트 대상 (우선순위)
| 우선순위 | 영역 | 근거 |
|----------|------|------|
| 🔴 High | `services/gemini_service.py` | AI 응답 파싱 – 불안정, mock 필수 |
| 🔴 High | `services/inventory_service.py` | 핵심 비즈니스 로직 (upsert, 병합) |
| 🔴 High | `api/scans.py` | 파일 업로드 + AI 파이프라인 |
| 🔴 High | `core/security.py` | 인증/인가 경계 |
| 🟡 Mid | `api/recipes.py` | 추천→요리→차감 전체 플로우 |
| 🟡 Mid | `api/shopping.py` | 체크아웃→재고 반영 |
| 🟡 Mid | `services/api.ts` (프론트) | API 클라이언트 에러 핸들링 |
| 🟡 Mid | `services/http-client.ts` | 캐시, 오프라인 폴백, 재시도 |
| 🟢 Low | `api/notifications.py` | 단순 CRUD |
| 🟢 Low | `api/stats.py` | 집계 로직 정확성 |

---

## Review Checklist

### 인프라
- [ ] 테스트 프레임워크가 설치/설정되어 있는가?
- [ ] 테스트 실행 명령어가 `package.json`/`Makefile`에 정의되어 있는가?
- [ ] 커버리지 리포트 도구가 설정되어 있는가?
- [ ] CI에서 테스트가 자동 실행되는가?
- [ ] 테스트용 환경변수/설정이 분리되어 있는가? (`.env.test`)

### 단위 테스트
- [ ] 핵심 서비스 함수에 단위 테스트가 있는가?
- [ ] 외부 의존성(Supabase, Gemini, FCM)이 mock되는가?
- [ ] 경계값(boundary) 테스트가 있는가? (빈 목록, 최대 크기, null)
- [ ] 에러 케이스 테스트가 있는가? (네트워크 오류, 잘못된 입력)

### 통합 테스트
- [ ] API 엔드포인트별 통합 테스트가 있는가?
- [ ] 인증 성공/실패 시나리오가 테스트되는가?
- [ ] DB 상태 검증이 포함되는가?

### 프론트엔드 테스트
- [ ] 주요 컴포넌트에 렌더 테스트가 있는가?
- [ ] API 클라이언트의 에러/오프라인 상황 테스트가 있는가?
- [ ] 유저 인터랙션 시나리오(탭/스와이프 등) 테스트가 있는가?

---

## Output Template

```markdown
# Test Engineering Report – YYYY-MM-DD

## Summary
- **테스트 인프라 상태**: ✅ 구축됨 / ⚠️ 부분 구축 / ❌ 미구축
- **기존 테스트 수**: 백엔드 N / 프론트엔드 N
- **추정 커버리지**: 백엔드 N% / 프론트엔드 N%
- **권장 신규 테스트**: N 개

## Infrastructure Assessment

### 현재 상태
| 항목 | 백엔드 | 프론트엔드 |
|------|--------|-----------|
| 프레임워크 | ✅/❌ | ✅/❌ |
| 실행 명령 | ✅/❌ | ✅/❌ |
| 커버리지 도구 | ✅/❌ | ✅/❌ |
| CI 연동 | ✅/❌ | ✅/❌ |

### 미구축 시 초기 설정 작업
- [ ] TE-SETUP-001: <설정 작업 설명>

## Test Gap Analysis

### 🔴 Critical Gaps (반드시 추가)

#### TE-001: <테스트 대상>
- **파일**: `<대상 소스 코드 경로>`
- **테스트 파일**: `<생성할 테스트 파일 경로>`
- **테스트 시나리오**:
  1. <정상 케이스>
  2. <에러 케이스>
  3. <경계값 케이스>
- **Mock 필요**: <Supabase / Gemini / FCM 등>
- **작업량**: S / M / L / XL

### 🟡 Warning Gaps

### 🟢 Nice-to-Have

## Recommended Test Architecture
```
prometheus-api/
├── tests/
│   ├── conftest.py          ← fixtures (mock DB, mock Gemini)
│   ├── test_security.py
│   ├── test_scans.py
│   ├── test_inventory.py
│   ├── test_recipes.py
│   ├── test_shopping.py
│   └── test_services/
│       ├── test_gemini.py
│       └── test_inventory_service.py

prometheus-app/
├── __tests__/
│   ├── services/
│   │   ├── api.test.ts
│   │   └── http-client.test.ts
│   └── components/
│       └── InventoryCard.test.tsx
```

## Action Items
| # | 제목 | 위험도 | 작업량 | 유형 |
|---|------|--------|--------|------|
| TE-001 | ... | 🔴 | M | 단위 테스트 |
```

---

## Codex Handoff

1. **보고서 읽기**: `.ai/reports/YYYY-MM-DD_test_engineering.md` 로드
2. **인프라 셋업** (미구축 시 우선 실행):
   ```
   a. pytest, pytest-asyncio, httpx (테스트용) 설치
   b. conftest.py에 mock fixture 작성
   c. jest 설정 및 @testing-library/react-native 설치
   d. 커밋: `chore(test): initialize test infrastructure`
   ```
3. **테스트 작성** (Gap 항목 순서대로):
   ```
   a. 테스트 파일 생성
   b. 시나리오별 테스트 함수 작성
   c. mock/stub 구성
   d. 테스트 실행: `pytest -v` / `npm test`
   e. 커밋: `test(api): TE-001 add inventory_service unit tests`
   ```
4. **커버리지 확인**: `pytest --cov=app --cov-report=html`
5. **변경 로그 추가**
6. **PR 요약**:
   ```
   ## Test Engineering – YYYY-MM-DD
   - 테스트 인프라 구축: ✅
   - 신규 테스트: N개 추가
   - 커버리지: N% → M%
   ```
