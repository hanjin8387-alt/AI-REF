# Agent 02: UI/UX Review

> **에이전트 역할**: 접근성·디자인 시스템·UX 일관성 점검  
> **결과 파일**: `.ai/reports/YYYY-MM-DD_uiux.md`

---

## Mission

PROMETHEUS 모바일 앱의 사용자 경험 품질을 점검하고, 접근성(a11y), 디자인 시스템 일관성, 인터랙션 패턴의 개선 방안을 제시한다.

## Scope

- 모든 탭 화면: `prometheus-app/app/(tabs)/*.tsx`
- 모든 컴포넌트: `prometheus-app/components/*.tsx`
- 스타일 시스템: `prometheus-app/constants/Colors.ts`, `prometheus-app/styles/`
- 네비게이션: `prometheus-app/app/_layout.tsx`, `prometheus-app/app/(tabs)/_layout.tsx`

## Non-Goals

- 백엔드 API 로직 → Agent 01 (Code Review)
- 성능 최적화 → Agent 05 (Perf & Reliability)
- 신규 기능 제안 → Agent 04 (Feature Discovery)

---

## Inputs (우선순위 파일 및 확인 포인트)

| 우선순위 | 파일/영역 | 확인 포인트 |
|----------|-----------|-------------|
| 🔴 High | `app/(tabs)/scan.tsx` | 카메라 권한 UX, 촬영 피드백, 에러 상태 |
| 🔴 High | `app/(tabs)/inventory.tsx` | 빈 상태, 로딩 상태, 삭제 확인 |
| 🟡 Mid | `app/(tabs)/index.tsx` | 홈 화면 정보 구조, 첫인상 |
| 🟡 Mid | `app/(tabs)/history.tsx` | 데이터 없을 때 상태, 날짜 포맷 |
| 🟡 Mid | `app/(tabs)/alerts.tsx` | 읽음/안읽음 구분, 알림 액션 |
| 🟡 Mid | `components/*.tsx` | 터치 영역 크기(≥44pt), 텍스트 가독성 |
| 🟢 Low | `constants/Colors.ts` | 색상 대비 WCAG AA 준수 |
| 🟢 Low | `app/(tabs)/_layout.tsx` | 탭 아이콘 명확성, 라벨 |

---

## Review Checklist

### 접근성 (Accessibility)
- [ ] 모든 터치 가능 요소에 `accessibilityLabel`이 있는가?
- [ ] 터치 영역이 최소 44×44 pt인가?
- [ ] 색상만으로 정보를 전달하지 않는가? (아이콘/텍스트 병행)
- [ ] 텍스트 색상 대비가 WCAG AA (4.5:1) 이상인가?
- [ ] 동적 폰트 크기(Dynamic Type)를 지원하는가?
- [ ] 화면 리더(VoiceOver/TalkBack)로 탐색 가능한가?

### 디자인 시스템 일관성
- [ ] 색상 토큰(`Colors.ts`)이 일관되게 사용되는가? (하드코딩 색상 없음)
- [ ] 간격(padding/margin)이 8pt 그리드를 따르는가?
- [ ] 모서리 반경(borderRadius)이 일관적인가? (카드: 16, 버튼: 12, 칩: 8)
- [ ] 그래디언트 배경이 모든 화면에 통일 적용되는가?
- [ ] 아이콘 스타일이 일관적인가?

### 인터랙션 패턴
- [ ] 로딩 상태(skeleton/spinner)가 표시되는가?
- [ ] 빈 상태(empty state)에 안내 메시지와 CTA가 있는가?
- [ ] 에러 상태에 재시도 버튼이 있는가?
- [ ] 삭제/비가역 작업에 확인 대화상자가 있는가?
- [ ] 성공 피드백(토스트/햅틱)이 있는가?
- [ ] 스와이프/롱프레스 동작이 직관적인가?
- [ ] 풀-투-리프레시가 작동하는가?

### 네비게이션
- [ ] 현재 위치가 시각적으로 명확한가?
- [ ] 뒤로 가기가 기대대로 동작하는가?
- [ ] 딥링크/알림 탭이 올바른 화면으로 이동하는가?

---

## Output Template

```markdown
# UI/UX Review Report – YYYY-MM-DD

## Summary
- **검토 화면**: N 화면, M 컴포넌트
- **발견 항목**: 🔴 Critical: N / 🟡 Warning: N / 🟢 Info: N
- **접근성 점수 추정**: <수치> / 100

## Findings

### 🔴 Critical

#### UX-001: <제목>
- **화면/컴포넌트**: `<경로>`
- **카테고리**: 접근성 / 디자인 시스템 / 인터랙션 / 네비게이션
- **현재 상태**: <스크린샷 설명 또는 코드 참조>
- **문제점**: <사용자 관점에서의 문제>
- **권장 개선**: <구체적 수정 방안>
- **작업량**: S / M / L / XL

### 🟡 Warning
#### UX-002: ...

### 🟢 Info
#### UX-003: ...

## Design System Audit
| 토큰 | 기대값 | 위반 파일 | 실제 사용값 |
|------|--------|-----------|-------------|
| primary | #00D084 | scan.tsx:L42 | #00CC77 |

## Action Items
| # | 제목 | 위험도 | 카테고리 | 작업량 |
|---|------|--------|----------|--------|
| UX-001 | ... | 🔴 | 접근성 | S |
```

---

## Codex Handoff

1. **보고서 읽기**: `.ai/reports/YYYY-MM-DD_uiux.md` 로드
2. **우선순위 정렬**: 접근성 🔴 → 인터랙션 🟡 → 디자인 시스템 🟢
3. **변경 실행** (항목당 1 커밋):
   ```
   a. 해당 컴포넌트/화면 파일 수정
   b. accessibilityLabel, 색상 토큰, 터치 영역 등 적용
   c. 커밋: `fix(app): UX-001 add accessibility labels to scan screen`
   ```
4. **시각 검증**: 변경 전/후 화면 상태 비교 (가능 시 스크린샷)
5. **변경 로그 추가**: `.ai/reports/YYYY-MM-DD_changelog.md`
6. **PR 요약**:
   ```
   ## UI/UX Fixes – YYYY-MM-DD
   - 접근성 개선: N 항목
   - 디자인 시스템 통일: N 항목
   - 인터랙션 개선: N 항목
   ```
