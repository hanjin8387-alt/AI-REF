# Agent 05: Observability / Analytics Skill

## Mission
로깅·메트릭·트레이싱·이벤트 스키마·퍼널 분석·디버깅 가시성을 강화하여 운영 품질을 높인다.

## Scope
- 로깅 수준 및 구조화 로그 패턴 평가
- 메트릭 수집 포인트 식별 (요청수, 에러율, 레이턴시 등)
- 분산 트레이싱 상태 확인
- 이벤트 스키마 설계 (사용자 행동 추적)
- 퍼널 분석 포인트 (스캔→재고→레시피→요리 전환율)
- 디버깅 가시성 (에러 컨텍스트, 요청 ID)

## Non-Goals
- 실제 모니터링 인프라(Datadog, Sentry) 설치
- 프론트엔드 UI 개선
- 코드 리팩토링

## Inputs (우선순위순)
1. `prometheus-api/app/main.py` — 미들웨어, 로깅 설정
2. `prometheus-api/app/api/*.py` — 라우터별 로깅 패턴
3. `prometheus-api/app/services/*.py` — 서비스 레이어 로깅
4. `prometheus-app/services/http-client.ts` — 프론트 에러/네트워크 로깅
5. `prometheus-api/app/core/config.py` — LOG_LEVEL 등 설정

### 봐야 할 증거
- `logger.info/warning/error` 호출 빈도 및 컨텍스트 정보
- 에러 로그에 request_id/device_id 포함 여부
- 구조화 로그(JSON) vs 자유형 메시지
- 메트릭 엔드포인트 또는 Prometheus 클라이언트 존재 여부
- 프론트 에러 리포팅 (아날리틱스/크래시 리포팅)

## Checklist

### 정량 기준
- [ ] 모든 에러 로그에 device_id 포함
- [ ] 모든 외부 API 호출에 소요시간 로깅
- [ ] 핵심 비즈니스 이벤트(스캔, 요리완료, 장보기체크아웃)에 로그 존재
- [ ] request_id 또는 correlation_id 미들웨어 존재

### 정성 기준
- [ ] 로그 메시지가 디버깅에 충분한 컨텍스트 제공
- [ ] 민감 정보(토큰, 비밀번호)가 로그에 노출되지 않음
- [ ] 에러 로그와 info 로그의 구분이 명확

## Output Template

```markdown
# Observability/Analytics Report – YYYY-MM-DD

## Summary
- 발견 항목: 🔴 N / 🟡 N / 🟢 N

## Current State
| 영역 | 상태 | 비고 |
|------|------|------|
| 구조화 로그 | ✅/❌ | ... |
| 메트릭 수집 | ✅/❌ | ... |
| 분산 트레이싱 | ✅/❌ | ... |
| 에러 리포팅 | ✅/❌ | ... |
| 이벤트/퍼널 | ✅/❌ | ... |

## Findings
### OA-001: <제목>
- 파일: <경로:라인>
- 설명: ...
- 권장 조치: ...

## Event Schema Proposal
| 이벤트명 | 트리거 | 포함 데이터 | 분석 가치 |
|---------|--------|-----------|----------|

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|

## Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: OA-T001
title: "<제목>"
files:
  - path: "<절대경로>"
    action: MODIFY
    summary: "<변경요지>"
test_command: "cd prometheus-api && python -m pytest tests/ -v"
acceptance_criteria:
  - "로그 출력 확인"
risk: 🟢
commit_message: "feat(observability): <OA-ID> <description>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| PII가 로그에 노출 | 🔴 Critical + 즉시 마스킹 권고 |
| 로깅이 성능에 영향 (hot path에 동기 I/O) | 비동기 로깅 전환 제안 |
| 외부 모니터링 서비스 미선정 | 로컬 로깅만 우선, 인프라 결정은 백로그 |
