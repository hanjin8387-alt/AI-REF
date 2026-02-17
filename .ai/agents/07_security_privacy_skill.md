# Agent 07: Security / Privacy Skill

## Mission
입력검증·비밀정보·권한·저장데이터·PII·취약점·의존성 리스크를 분석하고 보안 강화 계획을 수립한다.

## Scope
- 입력 검증 (SQL Injection, XSS, Path Traversal)
- 비밀정보 관리 (토큰, API 키, 환경변수)
- 인증/인가 메커니즘
- 저장 데이터 보호 (RLS, 암호화)
- PII (개인식별정보) 처리 (로그, 캐시, 전송)
- 의존성 취약점 (CVE, 라이선스)
- 컨테이너/인프라 보안

## Non-Goals
- 성능 최적화
- 기능 구현
- UI 개선

## Inputs (우선순위순)
1. `prometheus-api/app/core/security.py` — 인증/인가 핵심
2. `prometheus-api/app/core/config.py` — 비밀정보, 토큰 설정
3. `prometheus-api/app/api/admin.py` — 관리자 엔드포인트
4. `prometheus-api/app/api/scans.py` — 파일 업로드 (입력 검증)
5. `prometheus-api/Dockerfile` — 컨테이너 보안
6. `prometheus-api/requirements.txt` — 의존성 버전
7. `prometheus-api/schema.sql` — RLS 정책
8. `prometheus-app/services/http-client.ts` — 클라이언트 토큰 노출
9. `prometheus-api/app/main.py` — CORS, 미들웨어

### 봐야 할 증거
- `secrets.compare_digest()` 사용 여부 (모든 토큰 비교)
- `USER` 지시자(Dockerfile)
- `.dockerignore` 존재 여부
- `process.env.EXPO_PUBLIC_*` (클라이언트 번들 노출)
- RLS 정책이 모든 테이블에 적용되는지
- 파일 업로드 시 MIME 타입/확장자 검증

## Checklist

### 정량 기준
- [ ] 모든 토큰 비교에 `secrets.compare_digest()` 사용
- [ ] Dockerfile에 `USER` 지시자 존재
- [ ] `.dockerignore` 파일 존재
- [ ] 모든 테이블에 RLS 정책 존재
- [ ] requirements.txt 버전 고정

### 정성 기준
- [ ] PII가 로그에 노출되지 않음
- [ ] 에러 메시지에 내부 구현 노출 없음
- [ ] CORS 설정이 프로덕션 적합
- [ ] 클라이언트 토큰의 보안 한계가 문서화됨

## Output Template

```markdown
# Security/Privacy Report – YYYY-MM-DD

## Summary
- 발견 항목: 🔴 N / 🟡 N / 🟢 N

## OWASP Top 10 Mapping
| OWASP | 상태 | 관련 |
|-------|------|------|

## Findings
### SEC-001: <제목>
- OWASP: <카테고리>
- 파일: <경로:라인>
- 취약점: ...
- 권장 조치: ...

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|

## Risk & Rollback
...
```

## Codex Handoff Contract
```yaml
task_id: SEC-T001
title: "<제목>"
files:
  - path: "<절대경로>"
    action: MODIFY
    summary: "<변경요지>"
test_command: "cd prometheus-api && python -m pytest tests/test_security.py -v"
acceptance_criteria:
  - "보안 검증 통과"
risk: 🔴
commit_message: "security(<scope>): <SEC-ID> <description>"
```

## Stop Conditions
| 상황 | 조치 |
|------|------|
| 실제 데이터 유출 가능성 | 🔴 Critical + 즉시 인간 알림 |
| RLS 우회 가능 | 🔴 Critical + 모든 쿼리 감사 |
| 의존성에 알려진 CVE | 버전 업그레이드 Task 즉시 생성 |
| 클라이언트 번들 비밀 노출 | 아키텍처 레벨 검토 요청 |
