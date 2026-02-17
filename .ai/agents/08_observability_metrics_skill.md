# Agent 08: Observability / Metrics Skill

## Mission
성능 지표 수집/대시보드/로그, 클라이언트 이벤트 스키마, 서버 APM, 릴리즈 비교를 분석하고 관측 강화 계획을 수립한다.

## Scope
- 서버 사이드 성능 로그 (요청 시간, 외부 API 시간)
- 클라이언트 성능 이벤트 (화면 로딩, 인터랙션 지연)
- APM 도구 상태 (Sentry Performance, OpenTelemetry)
- 메트릭 수집 (Prometheus, StatsD, 커스텀)
- 릴리즈 간 성능 비교 메커니즘
- 알림/대시보드 설계

## Non-Goals
- 성능 최적화 구현
- 헬스체크 구현 (Feature Cycle에서 처리)

## Inputs (우선순위순)
1. `prometheus-api/app/main.py` — 미들웨어, 로깅 설정
2. `prometheus-api/app/api/*.py` — 라우터별 로깅
3. `prometheus-api/app/services/*.py` — 서비스 레이어 로깅
4. `prometheus-app/services/http-client.ts` — 클라이언트 타이밍

### 봐야 할 증거
- `logger.*` 호출에 performance_ prefix 또는 duration 정보
- request_id 미들웨어 존재 여부
- APM SDK import 여부
- perf_hooks 또는 Performance API 사용 여부

## Checklist
- [ ] 서버 요청에 응답 시간 로깅 미들웨어 존재
- [ ] 외부 API 호출에 duration 로깅
- [ ] 클라이언트 성능 이벤트 스키마 정의
- [ ] 릴리즈 비교 가능한 지표 저장

## Output Template
```markdown
# Observability/Metrics Report – YYYY-MM-DD

## Current State
| 영역 | 상태 | 비고 |
...

## Perf Event Schema
| 이벤트 | 트리거 | 데이터 | 분석 가치 |
...

## Findings (OM-001~) / Recommendations / Task List / Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: OM-T001
commit_message: "feat(observability): <OM-ID> <desc>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| APM 도구 미선정 | 로컬 로그 우선, 도구 선정은 백로그 |
| 성능 로그 볼륨 과다 우려 | 샘플링률 설정 제안 |
