# Agent 02: UI/UX Skill

## Mission
기능강화의 UI/UX 측면을 분석한다. 화면흐름·정보구조·접근성·에러상태·상호작용·일관성을 평가하고 개선안을 제시한다.

## Scope
- 신규/변경 화면의 정보구조(IA) 설계
- 화면 전환 흐름(Navigation Flow) 검증
- 접근성(Accessibility) 준수 여부
- 에러/빈 상태/로딩 상태 처리
- 디자인 시스템 일관성 (Colors, Typography, Components)
- 인터랙션 패턴 (터치, 스와이프, 피드백)

## Non-Goals
- 백엔드 API 설계
- 성능 프로파일링
- 테스트 코드 작성

## Inputs (우선순위순)
1. `prometheus-app/app/(tabs)/*.tsx` — 탭 화면 5개
2. `prometheus-app/components/*.tsx` — 재사용 컴포넌트
3. `prometheus-app/constants/Colors.ts` — 디자인 토큰
4. `prometheus-app/services/api.ts` — API 호출 패턴 (로딩/에러 처리)
5. `prometheus-app/services/http-client.ts` — 에러 응답 로컬라이즈
6. `prometheus-app/app/_layout.tsx` — 네비게이션 구조

### 봐야 할 증거
- 모든 Touchable/Pressable에 `accessibilityLabel` 존재 여부
- 에러 발생 시 사용자에게 보여주는 UI (Alert, Toast, 인라인)
- 빈 상태 디자인 일관성
- 하드코딩 색상값 vs Colors 토큰 사용 비율
- 삭제/비가역 작업 시 확인 대화상자 존재 여부

## Checklist

### 정량 기준
- [ ] 인터랙티브 요소 중 `accessibilityLabel` 누락 비율 < 10%
- [ ] 에러 상태에 재시도 UX 존재
- [ ] 하드코딩 색상 0개 (모두 토큰화)
- [ ] 모든 삭제 작업에 확인 대화상자 존재

### 정성 기준
- [ ] 화면 전환 시 사용자 컨텍스트 유지
- [ ] 빈 상태에 가이딩 CTA 존재
- [ ] 로딩 상태에 스켈레톤/스피너 존재
- [ ] 일관된 타이포그래피/간격/색상

## Output Template

```markdown
# UI/UX Report – YYYY-MM-DD

## Summary
- 검토 화면: N개
- 발견 항목: 🔴 N / 🟡 N / 🟢 N

## Findings
### 🔴 Critical
#### UX-001: <제목>
- 화면/컴포넌트: <경로>
- 카테고리: 접근성 | 상호작용 | 일관성 | 에러처리
- 설명: ...
- 근거: <파일:라인>
- 권장 조치: ...

### 🟡 Warning
...

### 🟢 Info
...

## Recommendations
- ...

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|

## Risk & Rollback
- ...
```

## Codex Handoff Contract
```yaml
task_id: UX-T001
title: "<제목>"
files:
  - path: "<절대경로>"
    action: MODIFY
    summary: "<변경요지>"
test_command: "cd prometheus-app && npm test"
acceptance_criteria:
  - "<criteria>"
risk: 🔴 | 🟡 | 🟢
commit_message: "fix(app): <UX-ID> <description>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| 디자인 시스템 토큰이 정의되지 않음 | 토큰 정의 선행 Task 생성 후 중단 |
| 화면 흐름에서 데드엔드 발견 | 🔴 Critical 보고 |
| 접근성 위반이 법적 요구사항에 해당 | 🔴 Critical + 즉시 수정 권고 |
