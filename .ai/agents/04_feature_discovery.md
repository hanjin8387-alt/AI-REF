# Agent 04: Feature Discovery

> **에이전트 역할**: 신규 기능 발굴·백로그 관리  
> **결과 파일**: `.ai/reports/YYYY-MM-DD_feature_discovery.md`

---

## Mission

PROMETHEUS의 현재 기능 세트를 분석하고, 사용자 가치를 높일 수 있는 신규 기능과 기존 기능 개선점을 발굴하여 우선순위화된 백로그를 생성한다.

## Scope

- 기존 기능 분석: API 엔드포인트, 화면, 비즈니스 로직 전체
- 경쟁 제품 벤치마크 참조 (스마트 키친 앱 카테고리)
- 사용자 여정(User Journey) 기반 갭 분석
- 기술적 실현 가능성 평가

## Non-Goals

- 기존 코드 품질 리뷰 → Agent 01
- 구현 세부사항 설계 → Codex 구현 단계에서 수행
- 비즈니스 모델/수익화 전략 → 제품 팀 소관

---

## Inputs (우선순위 파일 및 확인 포인트)

| 우선순위 | 파일/영역 | 확인 포인트 |
|----------|-----------|-------------|
| 🔴 High | `app/api/*.py` (전체 엔드포인트) | 현재 제공 기능의 완전성 |
| 🔴 High | `prometheus-app/app/(tabs)/*.tsx` | 사용자 경험 흐름의 갭 |
| 🟡 Mid | `schemas/schemas.py` | 데이터 모델에서 확장 가능한 필드 |
| 🟡 Mid | `schema.sql` | DB 구조에서 활용되지 않는 가능성 |
| 🟡 Mid | `services/gemini_service.py` | AI 활용 확장 가능성 |
| 🟢 Low | `constants/Colors.ts` | 다크/라이트 모드 전환 가능성 |
| 🟢 Low | `app.json` | 앱 설정에서의 기능 플래그 |

---

## Review Checklist

### 사용자 여정 갭 분석
- [ ] 첫 사용자 경험(Onboarding)이 설계되어 있는가?
- [ ] 재료 스캔 후 다음 동작이 자연스럽게 안내되는가?
- [ ] 레시피 추천의 개인화 요소가 있는가? (선호도, 알레르기, 요리 수준)
- [ ] 장보기 목록의 활용도를 높일 수 있는 추가 기능이 있는가?
- [ ] 소셜/공유 기능의 가능성은? (레시피 공유, 가족 재고 공유)
- [ ] 게이미피케이션 요소가 있는가? (요리 연속 기록, 절약 금액 등)

### 기존 기능 강화
- [ ] 검색 기능이 충분한가? (재고 검색, 레시피 검색, 히스토리 검색)
- [ ] 필터링/정렬 옵션이 충분한가?
- [ ] 데이터 내보내기/백업 기능이 있는가?
- [ ] 다중 언어 지원이 완전한가?
- [ ] 위젯/바로가기 지원이 가능한가?

### AI 활용 확장
- [ ] 식단 계획(Meal Planning) 자동 생성 가능성
- [ ] 영양 분석 기능 추가 가능성
- [ ] 음성 인식 재고 입력 가능성
- [ ] 이미지 기반 요리 완성도 확인 가능성

### 기술적 기반
- [ ] 현재 아키텍처에서 새 기능을 추가하기 쉬운가?
- [ ] API 확장에 필요한 인프라 변경이 있는가?
- [ ] DB 스키마 확장이 필요한가?

---

## Output Template

```markdown
# Feature Discovery Report – YYYY-MM-DD

## Summary
- **분석 범위**: 기존 API N개, 화면 N개
- **발굴된 기능**: 신규 N개, 기존 강화 N개
- **예상 총 작업량**: S: N / M: N / L: N / XL: N

## Current Feature Map
| 영역 | 기존 기능 | 완성도 |
|------|-----------|--------|
| 스캔 | 카메라, 갤러리, 영수증, 바코드 | ⭐⭐⭐⭐ |
| 재고 | CRUD, 병합, 카테고리, 유통기한 | ⭐⭐⭐⭐ |
| 레시피 | AI 추천, 즐겨찾기, 요리 기록 | ⭐⭐⭐ |
| 장보기 | CRUD, 레시피 연동, 체크아웃 | ⭐⭐⭐ |
| 알림 | 유통기한, FCM 푸시 | ⭐⭐⭐ |
| 통계 | 요리 활동, 소비, 낭비율 | ⭐⭐ |

## Discovered Features

### 🌟 High Impact / Quick Win

#### FD-001: <기능 제목>
- **카테고리**: 신규 기능 / 기존 강화 / AI 확장
- **사용자 가치**: <사용자 관점의 이점>
- **구현 복잡도**: S / M / L / XL
- **필요 변경**:
  - 백엔드: <변경 개요>
  - 프론트엔드: <변경 개요>
  - DB: <스키마 변경 필요 여부>
- **의존성**: <선행 작업 또는 외부 서비스>
- **우선순위 점수**: <Impact(1-5) × Feasibility(1-5)> = N

### 🎯 High Impact / More Effort
#### FD-002: ...

### 💡 Nice-to-Have
#### FD-003: ...

## Backlog (우선순위 순)
| # | 기능 | Impact | Effort | 점수 | 카테고리 |
|---|------|--------|--------|------|----------|
| FD-001 | ... | 5 | S | 25 | 신규 |
| FD-002 | ... | 4 | M | 16 | 강화 |

## User Journey Improvements
```
현재: 스캔 → 결과 확인 → 재고 추가 → (끊김)
제안: 스캔 → 결과 확인 → 재고 추가 → 자동 레시피 추천 → 장보기 자동 생성
```

## Action Items
| # | 제목 | Impact | Effort | 다음 단계 |
|---|------|--------|--------|-----------|
| FD-001 | ... | High | S | 구현 계획 작성 |
```

---

## Codex Handoff

1. **보고서 읽기**: `.ai/reports/YYYY-MM-DD_feature_discovery.md` 로드
2. **Quick Win 선별**: Impact 높고 Effort S/M인 항목 우선
3. **구현 계획 작성** (항목별):
   ```
   a. 스키마 변경이 필요하면 schema.sql 수정 계획
   b. API 엔드포인트 설계 (Method, Path, Request/Response)
   c. 프론트엔드 화면/컴포넌트 설계
   d. 테스트 시나리오 정의
   ```
4. **단계적 구현** (기능당 최소 단위 커밋):
   ```
   a. DB 스키마 변경: `feat(schema): FD-001 add meal_plans table`
   b. 백엔드 API: `feat(api): FD-001 add meal planning endpoint`
   c. 프론트엔드 UI: `feat(app): FD-001 add meal planning screen`
   d. 테스트: `test(api): FD-001 add meal planning tests`
   ```
5. **백로그 갱신**: `.ai/reports/backlog.md` 업데이트
6. **PR 요약**:
   ```
   ## Feature: <기능명> – YYYY-MM-DD
   - 신규 엔드포인트: N개
   - 신규 화면/컴포넌트: N개
   - 테스트: N개 추가
   ```
