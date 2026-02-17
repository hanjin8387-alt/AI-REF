# Agent 06: Security & Privacy

> **에이전트 역할**: 보안·개인정보·인증/인가 점검  
> **결과 파일**: `.ai/reports/YYYY-MM-DD_security_privacy.md`

---

## Mission

PROMETHEUS의 인증/인가 체계, 데이터 보호, API 보안, 의존성 안전성을 점검하고 취약점 해소 방안을 제시한다.

## Scope

- 인증: `core/security.py`, 헤더 X-App-Token / X-Device-ID
- DB 접근 제어: RLS, device_id 필터
- API 입력 검증: Pydantic 스키마, 파일 업로드 제한
- 의존성 보안: `requirements.txt`, `package.json`
- 환경변수 / 시크릿 관리
- CORS, Rate Limiting, 에러 메시지 노출

## Non-Goals

- 코드 품질 → Agent 01 · 성능 → Agent 05

---

## Inputs

| 우선순위 | 파일 | 확인 포인트 |
|----------|------|------------|
| 🔴 | `core/security.py` | 토큰 비교(timing-safe), device_id 검증 |
| 🔴 | `api/scans.py` | 파일 업로드: MIME 검증, 경로 주입, 크기 제한 |
| 🔴 | `api/admin.py` | 관리자 토큰 검증, 외부 접근 차단 |
| 🔴 | `core/config.py` | 시크릿 하드코딩, CORS_ORIGINS=`*` |
| 🔴 | `schema.sql` | RLS 정책 완전성, 권한 설정 |
| 🟡 | `api/*.py` (전체) | device_id 필터 누락, SQL 인젝션 가능성 |
| 🟡 | `services/fcm_service.py` | Firebase 크레덴셜 관리 |
| 🟡 | `services/http-client.ts` | 토큰/키 클라이언트 노출, HTTPS 강제 |
| 🟡 | `.env.example` | 기본값 안전성 |
| 🟢 | `requirements.txt` / `package.json` | 알려진 취약점 (CVE) |
| 🟢 | `Dockerfile` | root 사용자 실행, 불필요 패키지 |

---

## Review Checklist

### 인증/인가
- [ ] `secrets.compare_digest()`로 타이밍 안전 비교하는가?
- [ ] REQUIRE_APP_TOKEN=true 시 모든 라우터에 토큰 검증 적용되는가?
- [ ] device_id 화이트리스트(ALLOWED_DEVICE_IDS) 동작하는가?
- [ ] admin 엔드포인트에 별도 인증(X-Admin-Token)이 있는가?
- [ ] 인증 실패 시 일관된 응답(401/403)과 최소 정보 노출인가?

### 데이터 보호
- [ ] 모든 DB 쿼리에 `.eq("device_id", device_id)` 필터 있는가?
- [ ] RLS 정책이 모든 테이블에 활성화되어 있는가?
- [ ] 다른 디바이스의 데이터에 수평 접근(IDOR) 불가능한가?
- [ ] 로그에 민감 정보(토큰, API 키, 개인 데이터)가 기록되지 않는가?
- [ ] 에러 응답에 스택 트레이스/내부 경로가 노출되지 않는가?

### 입력 검증
- [ ] Pydantic에서 문자열 길이, 숫자 범위가 제한되어 있는가?
- [ ] 파일 업로드: 확장자/MIME 화이트리스트, 크기 제한(MAX_UPLOAD_SIZE_MB)
- [ ] 경로/파일명 인젝션 방지(Path Traversal)되어 있는가?
- [ ] JSON 파싱 시 깊이/크기 제한이 있는가?

### 네트워크 보안
- [ ] CORS_ORIGINS가 프로덕션에서 `*`가 아닌가?
- [ ] HTTPS 강제 설정이 있는가?
- [ ] 보안 헤더(HSTS, X-Content-Type-Options 등) 반환하는가?
- [ ] Rate Limiting이 브루트포스 공격을 방어하는가?

### 의존성 보안
- [ ] 알려진 CVE가 있는 패키지가 없는가?
- [ ] 의존성 버전이 고정(pinned)되어 있는가?
- [ ] 불필요한 의존성이 없는가?

### 컨테이너 보안
- [ ] Dockerfile에서 non-root 사용자로 실행하는가?
- [ ] 민감 파일(.env, 키 파일)이 이미지에 포함되지 않는가?
- [ ] `.dockerignore`에 시크릿 파일이 명시되어 있는가?

---

## Output Template

```markdown
# Security & Privacy Report – YYYY-MM-DD

## Summary
- **발견 항목**: 🔴 N / 🟡 N / 🟢 N
- **OWASP Top 10 해당 항목**: <목록>

## Findings

### 🔴 Critical

#### SEC-001: <제목>
- **OWASP 분류**: A01 / A02 / ...
- **파일**: `<경로>`
- **취약점 설명**: <공격 시나리오 포함>
- **영향**: <데이터 유출/서비스 중단 등>
- **권장 조치**: <구체적 수정 방안>
- **작업량**: S / M / L / XL

### 🟡 Warning · 🟢 Info (동일 형식)

## OWASP Top 10 Mapping
| OWASP | 상태 | 관련 발견 |
|-------|------|-----------|
| A01 Broken Access Control | 🟡 | SEC-003 |
| ... | ... | ... |

## Action Items
| # | 제목 | 위험도 | 작업량 |
|---|------|--------|--------|
```

---

## Codex Handoff

1. **보고서 읽기** → 🔴 Critical 최우선 처리
2. **변경 실행** (항목당 1 커밋):
   - 수정 + 테스트 + 커밋: `security(api): SEC-001 enforce CORS whitelist`
3. **보안 테스트**: 인증 우회, IDOR, 입력 인젝션 시나리오 테스트
4. **의존성 감사**: `pip audit` / `npm audit`
5. **PR 요약** 작성
