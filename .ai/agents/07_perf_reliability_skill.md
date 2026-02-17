# Agent 07: Perf Reliability Skill

## Mission
성능 회귀 방지, 성능 예산(perf budget), 로드 테스트/스모크 벤치, 메모리 릭 감지를 분석하고 가드레일을 설계한다.

## Scope
- 성능 예산 정의 (API p95, 번들 크기, FPS, 메모리)
- 회귀 감지 메커니즘 (CI 게이트, 벤치마크 비교)
- 로드 테스트 / 스모크 벤치 계획
- 메모리 릭 징후 검사 (무제한 성장, 이벤트 리스너, 클로저)
- 리소스 제한 (레이트 리밋, 캐시 크기, 업로드 크기)
- 장애 복구 (타임아웃, 서킷브레이커, graceful degradation)

## Non-Goals
- 특정 병목 최적화 구현 (다른 에이전트 역할)
- 보안 분석

## Inputs (우선순위순)
1. `prometheus-api/app/services/recipe_cache.py` — 메모리 캐시 크기 제한
2. `prometheus-api/app/services/gemini_service.py` — 외부 API 타임아웃
3. `prometheus-api/app/main.py` — 레이트 리밋, 미들웨어
4. `prometheus-api/app/api/scans.py` — 업로드 크기 검증
5. `prometheus-app/services/http-client.ts` — 클라이언트 캐시 Map
6. `prometheus-app/services/offline-cache.ts` — AsyncStorage 무제한 성장

### 봐야 할 증거
- 캐시/컬렉션에 max size / eviction 정책 존재 여부
- 이벤트 리스너 등록 후 해제 여부
- setInterval/setTimeout 정리 여부
- 무한 성장 가능한 데이터 구조 (Map, dict, Array)

## Checklist
- [ ] 모든 캐시/Map에 크기 제한 존재
- [ ] 모든 외부 호출에 타임아웃 존재
- [ ] 성능 예산 초안 정의
- [ ] 메모리 릭 징후 0건
- [ ] 로드 테스트 계획 수립

## Output Template
```markdown
# Perf Reliability Report – YYYY-MM-DD

## Perf Budget (초안)
| 지표 | 상한 | 경고 | 현재 추정 |
...

## Memory Leak Risk
| # | 파일 | 구조 | 위험 | 조치 |
...

## Load Test Plan
...

## Findings (PRL-001~) / Task List / Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: PRL-T001
commit_message: "perf(reliability): <PRL-ID> <desc>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| 로드 테스트 인프라 없음 | 커맨드라인 도구(wrk/hey)로 대체 |
| CI 파이프라인 없음 | 로컬 벤치 스크립트로 대체 |
