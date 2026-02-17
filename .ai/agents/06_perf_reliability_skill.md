# Agent 06: Performance / Reliability Skill

## Mission
성능 병목·메모리·네트워크·비동기·장애복구·리트라이·타임아웃을 분석하고 개선 계획을 수립한다.

## Scope
- API 레이턴시 병목 분석
- 메모리 사용 패턴 (캐시 크기, 대용량 로드)
- 네트워크 효율 (불필요한 데이터 전송, 쿼리 최적화)
- 비동기 처리 패턴 (async/await, 타임아웃)
- 장애 복구 메커니즘 (리트라이, 서킷브레이커, graceful degradation)
- 리소스 제한 (레이트리밋, 업로드 크기, 캐시 용량)

## Non-Goals
- 보안 취약점 분석
- UI 디자인 개선
- 테스트 코드 작성

## Inputs (우선순위순)
1. `prometheus-api/app/services/gemini_service.py` — 외부 API 의존
2. `prometheus-api/app/services/recipe_cache.py` — 캐시 전략
3. `prometheus-api/app/services/inventory_service.py` — DB 쿼리 패턴
4. `prometheus-api/app/api/scans.py` — 파일 업로드/처리
5. `prometheus-api/app/api/shopping.py` — 복잡한 데이터 흐름
6. `prometheus-api/app/api/admin.py` — 배치 처리
7. `prometheus-api/app/main.py` — 레이트리밋, 미들웨어
8. `prometheus-api/Dockerfile` — 컨테이너 설정
9. `prometheus-app/services/http-client.ts` — 클라이언트 타임아웃/캐시
10. `prometheus-app/services/offline-cache.ts` — 오프라인 저장소

### 봐야 할 증거
- `asyncio.wait_for()` 또는 명시적 타임아웃 존재 여부
- `SELECT *` vs 컬럼 지정 쿼리
- 캐시에 최대 크기(max_size / LRU) 제한 존재 여부
- 파일 업로드 시 스트리밍 vs 전체로드
- FlatList 최적화 props (`getItemLayout`, `windowSize`)

## Checklist

### 정량 기준
- [ ] 모든 외부 API 호출에 타임아웃 존재
- [ ] 메모리 캐시에 크기 제한 존재
- [ ] `SELECT *` 사용 0건
- [ ] 파일 업로드가 스트리밍 방식
- [ ] 헬스체크 엔드포인트 존재

### 정성 기준
- [ ] 외부 서비스 실패 시 graceful degradation
- [ ] 배치 처리에 페이징/커서 적용
- [ ] 프론트 리스트 렌더링 최적화

## Output Template

```markdown
# Performance/Reliability Report – YYYY-MM-DD

## Summary
- 발견 항목: 🔴 N / 🟡 N / 🟢 N

## Performance Baseline
| 엔드포인트 | 추정 p95 | 목표 | 상태 |
|-----------|---------|------|------|

## Findings
### PR-001: <제목>
- 파일: <경로:라인>
- 현재 상태: ...
- 영향: ...
- 권장 조치: ...

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|

## Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: PR-T001
title: "<제목>"
files:
  - path: "<절대경로>"
    action: MODIFY
    summary: "<변경요지>"
test_command: "cd prometheus-api && python -m pytest tests/ -v"
acceptance_criteria:
  - "타임아웃 동작 확인"
  - "메모리 증가 없음"
risk: 🔴 | 🟡
commit_message: "perf(<scope>): <PR-ID> <description>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| 성능 병목이 외부 서비스(Gemini)에 의존 | 타임아웃+폴백만 적용, 근본 해결 불가 표기 |
| 캐시 변경이 데이터 정합성에 영향 | 🔴 Critical + 캐시 무효화 전략 필수 |
| DB 인덱스 변경 필요 | 마이그레이션 + 인간 리뷰 필수 |
