# Agent 04: Network / Cache / Data Skill

## Mission
HTTP/앱 캐시 전략, 페이로드 최소화, 프리페치, 배치 요청, 중복 요청 제거, 오프라인/재시도를 분석하여 네트워크 효율을 개선한다.

## Scope
- HTTP 캐시 헤더 (Cache-Control, ETag)
- 앱 캐시 전략 (인메모리, AsyncStorage, TTL)
- 응답 페이로드 크기 최소화
- 프리페치/배치 기회
- 중복 요청 방지 (deduplication)
- 오프라인 큐 / 재시도 전략

## Non-Goals
- 서버 사이드 쿼리 최적화 (Agent 03)
- UI 렌더 최적화 (Agent 02)

## Inputs (우선순위순)
1. `prometheus-app/services/http-client.ts` — 클라이언트 캐시, 요청 로직
2. `prometheus-app/services/offline-cache.ts` — 오프라인 캐시
3. `prometheus-app/services/api.ts` — API 호출 패턴
4. `prometheus-api/app/services/recipe_cache.py` — 서버 캐시
5. `prometheus-api/app/main.py` — 미들웨어 (압축 등)

### 봐야 할 증거
- `Cache-Control`/`ETag` 응답 헤더 설정 여부
- `cacheTtlMs` 사용 패턴 및 값
- 동시 요청 시 같은 엔드포인트 중복 호출 여부
- 응답 body에 불필요한 필드 포함 여부
- gzip/brotli 압축 미들웨어 존재 여부

## Checklist
- [ ] GET 응답에 Cache-Control 또는 ETag 존재
- [ ] 클라이언트 캐시 TTL이 적절 (30s~5min)
- [ ] 동일 엔드포인트 중복 호출 0건
- [ ] 응답 payload에 불필요 필드 0건
- [ ] gzip 압축 적용

## Output Template
```markdown
# Network/Cache/Data Report – YYYY-MM-DD

## Baseline & Measurement
| 지표 | 현재 | 목표 | 측정 방법 |
...

## Findings (NC-001~)
...

## Recommendations (실제 성능 vs 체감속도)
...

## Task List / Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: NC-T001
commit_message: "perf(network): <NC-ID> <desc>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| CDN/프록시 설정 필요 | 인프라 작업으로 분류, blocker |
| 캐시 무효화 로직 복잡 | 단순 TTL 우선, 고급 전략은 백로그 |
