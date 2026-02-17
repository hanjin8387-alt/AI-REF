# Agent 03: Backend Latency Skill

## Mission
N+1 쿼리, 인덱스 누락, 캐시 전략, 페이징, 직렬→병렬 변환, 타임아웃을 분석하여 p95/p99 API 레이턴시를 개선한다.

## Scope
- DB 쿼리 패턴 분석 (N+1, SELECT *, 인덱스 활용)
- 직렬 I/O → asyncio.gather 병렬화 기회
- 캐시 hit rate 및 TTL 적절성
- 레이트 리밋 적절성
- 타임아웃/리트라이 패턴
- 페이징/커서 미적용 엔드포인트

## Non-Goals
- 프론트엔드 렌더 최적화
- 번들 크기
- 보안 분석

## Inputs (우선순위순)
1. `prometheus-api/app/services/gemini_service.py` — 외부 API 의존 (최대 병목)
2. `prometheus-api/app/services/recipe_cache.py` — 캐시 전략
3. `prometheus-api/app/services/inventory_service.py` — DB 쿼리 패턴
4. `prometheus-api/app/api/scans.py` — 파일 업로드 + Gemini
5. `prometheus-api/app/api/shopping.py` — 734줄, 복잡한 데이터 흐름
6. `prometheus-api/app/api/recipes.py` — 추천 파이프라인
7. `prometheus-api/app/api/admin.py` — 배치 처리
8. `prometheus-api/schema.sql` — 인덱스 정의

### 봐야 할 증거
- `.select("*")` 빈도
- `await` 직렬 체인 (병렬화 가능 여부)
- `asyncio.wait_for()` / timeout 존재 여부
- `.limit()` / `.range()` 누락 (풀 테이블 스캔)
- 인덱스 vs 쿼리 조건 매칭

## Checklist
- [ ] SELECT * 사용 0건
- [ ] 모든 외부 API(Gemini, 바코드)에 타임아웃 존재
- [ ] 병렬화 가능한 직렬 await ≤ 1건
- [ ] 모든 목록 API에 limit/offset 존재
- [ ] 캐시 TTL이 비즈니스 요구에 적합

## Output Template
```markdown
# Backend Latency Report – YYYY-MM-DD

## Baseline & Measurement
| 엔드포인트 | 추정 p95 | 목표 | 측정 방법 |
...

## Findings (BL-001~)
...

## Recommendations (실제 성능 vs 체감속도)
...

## Task List
| # | 파일 | 변경요지 | 벤치 커맨드 | 테스트 커맨드 | 수용기준 | 예상 영향 | 위험도 |
...

## Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: BL-T001
commit_message: "perf(api): <BL-ID> <desc>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| Gemini API 자체 레이턴시가 병목 | 타임아웃+폴백만 적용, 근본 해결 불가 표기 |
| DB 인덱스 변경 필요 | 마이그레이션 + 인간 리뷰 필수 |
| 캐시 변경이 데이터 정합성 영향 | 🔴 Critical + 캐시 무효화 전략 필수 |
