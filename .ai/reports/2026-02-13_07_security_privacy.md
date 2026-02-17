# Security / Privacy Report – 2026-02-13 (Feature Enhancement Cycle)

## Summary
- **발견 항목**: 🔴 Critical: 2 / 🟡 Warning: 4 / 🟢 Info: 3

---

## OWASP Top 10 Mapping
| OWASP | 상태 | 관련 항목 |
|-------|------|---------|
| A01 Broken Access Control | ✅ 양호 | device_id RLS 필터 일관 적용 |
| A02 Cryptographic Failures | ✅ 양호 | 비밀번호/암호화 미사용 구조 |
| A03 Injection | ✅ 양호 | Supabase SDK (파라미터화 쿼리) |
| A04 Insecure Design | 🟡 | SEC-005 (클라이언트 토큰 노출) |
| A05 Security Misconfiguration | 🔴 | SEC-002 (root 실행), SEC-003, SEC-007 |
| A06 Vulnerable Components | 🟡 | SEC-006 (버전 미고정) |
| A07 Auth Failures | 🔴 | SEC-001 (timing attack) |
| A08 Data Integrity | ✅ 양호 | |
| A09 Logging/Monitoring | 🟡 | OA-001 (request_id 없음) |
| A10 SSRF | ✅ 양호 | 바코드 API 고정 URL |

---

## Findings

### 🔴 Critical

#### SEC-001: Admin 토큰 비교가 timing-safe 하지 않음
- **OWASP**: A07
- **파일**: `prometheus-api/app/api/admin.py` L28
- **취약점**: `x_admin_token != token` 사용 → 타이밍 사이드채널으로 토큰 추론 가능
- **근거**: `security.py`의 `require_app_token()`은 `secrets.compare_digest()` 사용하나 admin은 누락
- **권장 조치**: `secrets.compare_digest(x_admin_token, token)` + `import secrets`
- **위험도**: 🔴

#### SEC-002: Dockerfile이 root 사용자로 실행
- **OWASP**: A05
- **파일**: `prometheus-api/Dockerfile`
- **취약점**: `USER` 지시자 없음 → 컨테이너 탈출 시 호스트 root 권한
- **권장 조치**: non-root 사용자 생성 + `USER appuser`
- **위험도**: 🔴

### 🟡 Warning

#### SEC-003: CORS 기본값에 localhost 포함
- **파일**: `config.py` L15
- **근거**: `"http://localhost:8081,http://localhost:19006,http://localhost:3000"` — 프로덕션 배포 시에도 포함 가능
- **권장 조치**: 프로덕션에서 localhost 제거 강제 또는 경고 로그

#### SEC-004: APP_TOKEN 기본값 빈 문자열
- **파일**: `config.py` L14
- **근거**: `REQUIRE_APP_TOKEN=false` 시 인증 없이 전체 API 접근 가능
- **권장 조치**: 프로덕션 기본값 강제 또는 경고

#### SEC-005: 프론트엔드 APP_TOKEN이 빌드 번들에 포함
- **파일**: `http-client.ts` L5-8
- **근거**: `process.env.EXPO_PUBLIC_APP_TOKEN` → 앱 디컴파일로 추출 가능
- **권장 조치**: APP_TOKEN을 "기본 접근 제어"로 문서화. 강한 인증은 Firebase App Check 검토.

#### SEC-006: `.dockerignore` 파일 부재
- **파일**: `prometheus-api/` 루트
- **근거**: `.env`, `__pycache__`, `.git` 등이 이미지에 포함될 수 있음
- **권장 조치**: `.dockerignore` 생성

### 🟢 Info

#### SEC-007: requirements.txt 일부 버전 범위만 명시 (정확한 버전 미고정)
- **권장 조치**: `pip freeze` 또는 `pip-compile`로 고정

#### SEC-008: 파일 업로드 MIME 타입 이중 검증 양호
- **파일**: `scans.py`
- `content_type` 검사 + 확장자 검사 존재. 양호.

#### SEC-009: RLS 정책이 모든 테이블에 적용됨
- **파일**: `schema.sql` L211-253
- `service_role` 전용 정책, `anon`/`authenticated` 권한 revoke. 양호.

---

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|
| 1 | `admin.py` | timing-safe 토큰 비교 | `pytest tests/test_admin.py -v` | `secrets.compare_digest` 사용 | 🔴 |
| 2 | `Dockerfile` | non-root user + `.dockerignore` | `docker build && docker run whoami` | appuser 출력 | 🔴 |
| 3 | `config.py` | CORS localhost 프로덕션 경고 | `pytest tests/ -v` | 경고 로그 확인 | 🟡 |
| 4 | `config.py` | APP_TOKEN 프로덕션 경고 | `pytest tests/ -v` | 경고 로그 확인 | 🟡 |
| 5 | 문서 | 클라이언트 토큰 보안 한계 문서화 | N/A | 문서 존재 | 🟡 |
| 6 | `requirements.txt` | 버전 고정 | `pip install -r requirements.txt` | 모든 버전 고정 | 🟢 |

## Risk & Rollback
- SEC-001: 1줄 수정, 안전
- SEC-002: 파일 권한 문제 시 `RUN chown` 추가 필요. 빌드 테스트 필수.
- SEC-003/004: 경고 추가만, 동작 변경 없음
- SEC-005: 아키텍처 레벨 변경은 별도 사이클 필요
