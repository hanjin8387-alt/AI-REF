# Agent 03: Backend / API Skill

## Mission
API 계약·입력검증·에러모델·권한·캐시·데이터흐름을 분석하고, 기능강화에 필요한 백엔드 변경사항을 설계한다.

## Scope
- API 엔드포인트 계약 (경로, 메서드, 요청/응답 스키마)
- 입력 검증 (Pydantic, 수동 검증)
- 에러 모델 (HTTPException, 에러코드, 메시지 일관성)
- 인증/인가 (app_token, device_id, admin_token)
- 캐시 전략 (RecipeCache, HTTP 캐시)
- 데이터 흐름 (서비스 레이어, DB 쿼리 패턴)
- 리팩토링 포인트 (중복 코드, 과대 파일)

## Non-Goals
- 프론트엔드 UI 구현
- 인프라/배포 설정
- 테스트 코드 작성

## Inputs (우선순위순)
1. `prometheus-api/app/api/*.py` — 라우터 6개 (scans, inventory, recipes, shopping, admin, notifications)
2. `prometheus-api/app/services/*.py` — 서비스 레이어 (gemini_service, inventory_service, recipe_cache)
3. `prometheus-api/app/core/security.py` — 인증/인가
4. `prometheus-api/app/core/config.py` — 설정
5. `prometheus-api/app/main.py` — 앱 설정, 미들웨어
6. `prometheus-api/schema.sql` — DB 스키마
7. `prometheus-api/requirements.txt` — 의존성

### 봐야 할 증거
- `.eq("device_id", device_id)` 필터가 모든 쿼리에 적용되는지
- HTTPException detail 메시지 언어 일관성
- `SELECT *` 사용 빈도
- Gemini 응답 파싱 시 try/except 존재 여부
- 레이트 리밋 설정 적절성

## Checklist

### 정량 기준
- [ ] 모든 DB 쿼리에 device_id 필터 존재
- [ ] `SELECT *` 사용 0건
- [ ] 모든 Gemini 파싱에 try/except 존재
- [ ] 에러 메시지 언어 통일 (영어)
- [ ] 모든 라우터에 `Depends(require_app_token)` 적용

### 정성 기준
- [ ] 서비스 레이어 분리 원칙 준수
- [ ] 라우터 파일 ≤ 500줄
- [ ] 중복 함수 0개
- [ ] API 응답 스키마 일관

## Output Template

```markdown
# Backend/API Report – YYYY-MM-DD

## Summary
- 검토 엔드포인트: N개
- 발견 항목: 🔴 N / 🟡 N / 🟢 N

## Findings
### 🔴 Critical / 🟡 Warning / 🟢 Info
#### BA-001: <제목>
- 파일: <경로:라인>
- 설명: ...
- 근거: ...
- 권장 조치: ...

## API Contract Gaps
| Method | Path | 현재 문제 | 권장 수정 |
|--------|------|----------|----------|

## Recommendations
...

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|

## Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: BA-T001
title: "<제목>"
files:
  - path: "<절대경로>"
    action: NEW | MODIFY
    summary: "<변경요지>"
test_command: "cd prometheus-api && python -m pytest tests/ -v"
acceptance_criteria:
  - "<criteria>"
risk: 🔴 | 🟡 | 🟢
commit_message: "<type>(api): <BA-ID> <description>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| DB 스키마 변경이 RLS 정책에 영향 | 🔴 Critical + 보안 에이전트 리뷰 |
| API breaking change 필요 | 버전닝 전략 제안 후 인간 리뷰 |
| 서비스 레이어에 순환 의존 발견 | 리팩토링 선행 작업 생성 |
