# Agent 04: Test Engineering Skill

## Mission
테스트 피라미드 전략을 수립하고, 커버리지 갭을 식별하며, 기능강화에 필요한 테스트 계획과 회귀 전략을 설계한다.

## Scope
- 테스트 인프라 상태 진단 (프레임워크, 설정, CI 연동)
- 테스트 커버리지 갭 분석
- 테스트 피라미드 설계 (단위/통합/E2E 비율)
- 회귀 전략 및 자동화 커맨드 확정
- 신규 기능에 대한 테스트 시나리오 설계

## Non-Goals
- 비즈니스 로직 구현
- UI/UX 개선
- 성능 튜닝

## Inputs (우선순위순)
1. `prometheus-api/tests/` — 기존 테스트 (미구축 가능)
2. `prometheus-app/__tests__/` — 기존 프론트 테스트
3. `prometheus-api/requirements.txt` — pytest 의존성 확인
4. `prometheus-app/package.json` — jest 의존성 확인
5. `prometheus-api/app/api/*.py` — 테스트 대상 엔드포인트
6. `prometheus-api/app/services/*.py` — 테스트 대상 서비스
7. `prometheus-app/services/*.ts` — 프론트 서비스 레이어

### 봐야 할 증거
- `conftest.py` 존재 여부
- `jest.config.js` / `jest.config.ts` 존재 여부
- 기존 테스트 파일 수 및 assert 품질
- mock/fixture 패턴
- test script in package.json

## Checklist

### 정량 기준
- [ ] 백엔드 테스트 인프라 존재 (pytest 설치, conftest.py)
- [ ] 프론트 테스트 인프라 존재 (jest 설치, jest.config)
- [ ] 🔴 변경 → 단위+통합 테스트 존재
- [ ] 🟡 변경 → 최소 1개 관련 테스트
- [ ] 테스트 실행 커맨드 동작 확인

### 정성 기준
- [ ] mock이 현실적 (실제 응답 구조 반영)
- [ ] 테스트 이름이 시나리오를 설명
- [ ] 부정 케이스(에러/경계)가 포함

## Output Template

```markdown
# Test Engineering Report – YYYY-MM-DD

## Infrastructure Status
| 항목 | 백엔드 | 프론트엔드 |
|------|--------|-----------|
| 프레임워크 | ✅/❌ | ✅/❌ |
| 실행 커맨드 | ... | ... |
| 커버리지 도구 | ✅/❌ | ✅/❌ |

## Coverage Gap Analysis
### 🔴 Critical Gaps
#### TE-001: <제목>
- 대상: <파일/함수>
- 시나리오: ...
- Mock 필요: ...

## Recommended Test Architecture
(디렉터리 트리)

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|

## Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: TE-T001
title: "<제목>"
files:
  - path: "<절대경로>"
    action: NEW | MODIFY
    summary: "<변경요지>"
test_command: "cd prometheus-api && python -m pytest tests/<file> -v"
acceptance_criteria:
  - "테스트 통과"
  - "커버리지 증가"
risk: 🟡
commit_message: "test(<scope>): <TE-ID> <description>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| 테스트 인프라 미구축 | 인프라 구축 Task를 P0으로 선행 생성 |
| 외부 서비스 mock 불가 | 통합 테스트로 격하 + 주의 표기 |
| 테스트 2회 연속 실패 | 블로커 리포트 생성 후 중단 |
