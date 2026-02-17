# Agent 02: Frontend Rendering Skill

## Mission
렌더 병목, 불필요 리렌더, 리스트 가상화, 이미지/애니메이션, 코드 스플리팅을 분석하고 개선안을 제시한다.

## Scope
- 불필요 리렌더 감지 (useMemo/useCallback/React.memo 누락)
- FlatList/SectionList 가상화 최적화
- 이미지 로딩/캐싱/리사이즈 패턴
- 애니메이션 성능 (JS vs Native driver)
- 코드 스플리팅/지연 로딩 기회
- 메인 스레드 차단 작업 (동기 연산, JSON.parse 대량 데이터)

## Non-Goals
- 백엔드 API 최적화
- 네트워크 캐시 전략 (Agent 04)
- 번들 크기 분석 (Agent 05)

## Inputs (우선순위순)
1. `prometheus-app/app/(tabs)/*.tsx` — 탭 화면 5개
2. `prometheus-app/components/*.tsx` — 재사용 컴포넌트 6개
3. `prometheus-app/services/api.ts` — API 호출 패턴 (상태 관리)
4. `prometheus-app/services/http-client.ts` — 캐시/응답 처리
5. `prometheus-app/app/_layout.tsx` — 네비게이션/레이아웃

### 봐야 할 증거
- `useMemo`, `useCallback`, `React.memo` 사용 빈도
- FlatList의 `getItemLayout`, `windowSize`, `maxToRenderPerBatch`, `removeClippedSubviews`
- `Animated` vs `Reanimated` 사용
- 인라인 함수/객체 생성 (렌더 함수 내)
- `useEffect` 의존성 배열 과다/누락

## Checklist
### 정량
- [ ] FlatList에 `getItemLayout` 적용률 100%
- [ ] 인라인 함수 생성 0건 (렌더 함수 내 `() => {}`)
- [ ] 이미지에 width/height 고정 + 캐시 정책

### 정성
- [ ] 화면 전환 시 프레임 드롭 없음 (60fps)
- [ ] 스크롤 시 버벅임 없음
- [ ] 대량 데이터(100+) 렌더 시 지연 없음

## Output Template
```markdown
# Frontend Rendering Report – YYYY-MM-DD

## Baseline & Measurement
| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|

## Findings
### FR-001: ...
- 파일: <경로:라인>
- 유형: 실제 성능 | 체감속도
...

## Recommendations (실제 성능 vs 체감속도 분리)
### 실제 성능
...
### 체감속도
...

## Task List
| # | 파일 | 변경요지 | 벤치 커맨드 | 테스트 커맨드 | 수용기준 | 예상 영향 | 위험도 |
...

## Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: FR-T001
commit_message: "perf(app): <FR-ID> <desc>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| React DevTools Profiler 실행 불가 | 수동 렌더 카운트로 대체 |
| Reanimated 도입 시 의존성 충돌 | 기존 Animated API 내에서 최적화 |
