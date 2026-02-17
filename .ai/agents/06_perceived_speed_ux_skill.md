# Agent 06: Perceived Speed / UX Skill

## Mission
스켈레톤, 프리페치, 지연로딩, 낙관적 UI, 점진적 렌더, 로딩/에러 상태를 분석하여 체감속도를 개선한다.

## Scope
- 스켈레톤/플레이스홀더 존재 여부 및 품질
- 낙관적 UI 적용 가능 지점 (즉시 반영 → 서버 확인)
- 우선순위 렌더 (above-the-fold 우선)
- 프리페치 기회 (다음 화면 데이터)
- 로딩/에러/빈 상태 전환 속도
- 인터랙션 즉시성 (버튼 누름 → 피드백)

## Non-Goals
- 실제 API 레이턴시 감소 (Agent 03)
- 번들 크기 (Agent 05)

## Inputs (우선순위순)
1. `prometheus-app/app/(tabs)/*.tsx` — 탭 화면
2. `prometheus-app/components/*.tsx` — 로딩/카드 컴포넌트
3. `prometheus-app/services/api.ts` — API 호출 시 로딩 상태
4. `prometheus-app/services/http-client.ts` — 캐시 히트 시 즉시 반환

### 봐야 할 증거
- 스켈레톤 컴포넌트 존재 여부
- `useState(loading)` → UI 전환 패턴
- 낙관적 업데이트 패턴 (setState → API → rollback)
- 화면 전환 시 데이터 프리페치 여부
- 터치 피드백 (opacity/scale 변화)

## Checklist
### 정량
- [ ] 모든 데이터 화면에 스켈레톤 또는 콘텐츠 플레이스홀더 존재
- [ ] 삭제/추가 작업에 낙관적 UI ≥ 1건
- [ ] 상태 전환(로딩→데이터→에러) 시간 < 100ms (UI 측)

### 정성
- [ ] 버튼 누름 시 즉각적 시각 피드백
- [ ] 화면 전환 시 빈 화면 보이지 않음
- [ ] 에러 상태에서 재시도가 쉬움

## Output Template
```markdown
# Perceived Speed/UX Report – YYYY-MM-DD

## Baseline & Measurement
| 시나리오 | 현재 체감 | 목표 | 측정 방법 |
...

## Findings (PS-001~)
### 유형: 체감속도
...

## Recommendations
### 체감속도 개선
...
### 실제 성능 연계
...

## Task List / Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: PS-T001
commit_message: "perf(ux): <PS-ID> <desc>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| 스켈레톤 디자인 명세 없음 | GlassCard 기반 스켈레톤 자동 제안 |
| 낙관적 UI 롤백 UX 미정의 | 토스트 알림으로 폴백 |
