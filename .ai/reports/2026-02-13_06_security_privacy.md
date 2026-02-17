# Security & Privacy Report – 2026-02-13

## Summary
- **발견 항목**: 🔴 Critical: 2 / 🟡 Warning: 3 / 🟢 Info: 2

---

## Findings

### 🔴 Critical

#### SEC-001: Admin 토큰 검증이 timing-safe 하지 않음 (= CR-001)
- **OWASP**: A07 Identification and Authentication Failures
- **파일**: `prometheus-api/app/api/admin.py` L28
- **취약점**: `x_admin_token != token` (문자열 직접 비교) → 타이밍 사이드채널 공격
- **권장 조치**: `secrets.compare_digest()` 사용
- **작업량**: S

#### SEC-002: Dockerfile이 root 사용자로 실행
- **OWASP**: A05 Security Misconfiguration
- **파일**: `prometheus-api/Dockerfile`
- **취약점**: `USER` 지시자 없음 → 컨테이너 탈출 시 호스트 root 권한 가능
- **권장 조치**: non-root 사용자 생성 및 `USER` 지시자 추가
- **작업량**: S

### 🟡 Warning

#### SEC-003: CORS_ORIGINS 기본값이 개발용 localhost 3개
- **파일**: `prometheus-api/app/core/config.py` L15
- **현재 상태**: `"http://localhost:8081,http://localhost:19006,http://localhost:3000"` — 프로덕션에서도 동일 적용 가능
- **보호 장치**: lifespan에서 production+`*` 조합은 차단하지만, localhost가 포함된 것은 허용.
- **권장 조치**: 프로덕션 배포 시 명시적 오리진만 허용하도록 문서/검증 강화
- **작업량**: S

#### SEC-004: APP_TOKEN이 빈 문자열이 기본값
- **파일**: `prometheus-api/app/core/config.py` L14
- **현재 상태**: `app_token: str = ""` — REQUIRE_APP_TOKEN=true이면 lifespan에서 차단하지만, false일 때는 인증 없이 동작
- **권장 조치**: 프로덕션에서 APP_TOKEN 미설정 시 경고 로그 + 문서화
- **작업량**: S

#### SEC-005: 프론트엔드 APP_TOKEN이 클라이언트 번들에 포함
- **파일**: `prometheus-app/services/http-client.ts` L5-8
- **현재 상태**: `process.env.EXPO_PUBLIC_APP_TOKEN` → 빌드 시 번들에 포함. 앱 디컴파일로 추출 가능.
- **영향**: 공유 비밀(APP_TOKEN)이 클라이언트에 노출
- **권장 조치**: APP_TOKEN을 "앱 진정성 검증"이 아닌 "기본 접근 제어"로 문서화. 강한 인증이 필요하면 Firebase App Check 등 추가.
- **작업량**: M (인증 아키텍처 검토 필요)

### 🟢 Info

#### SEC-006: requirements.txt에 버전 범위가 없음 (일부 항목)
- 특정 버전 고정 없이 최소 버전만 명시. 보안 패치 추적 어려움.
- **권장 조치**: `pip-compile` 또는 `pip freeze`로 정확한 버전 고정
- **작업량**: S

#### SEC-007: `.dockerignore` 파일 부재
- `.env`, `__pycache__`, `.git` 등이 이미지에 포함될 수 있음
- **권장 조치**: `.dockerignore` 생성
- **작업량**: S

---

## OWASP Top 10 Mapping
| OWASP | 상태 | 관련 |
|-------|------|------|
| A01 Broken Access Control | ✅ 양호 | device_id 필터 일관 적용 |
| A02 Cryptographic Failures | ✅ 양호 | 비밀번호/암호화 미사용 |
| A03 Injection | ✅ 양호 | Supabase SDK 사용 (파라미터화) |
| A04 Insecure Design | 🟡 | SEC-005 (클라이언트 토큰) |
| A05 Security Misconfiguration | 🔴 | SEC-002 (root), SEC-003 |
| A06 Vulnerable Components | 🟡 | SEC-006 (버전 미고정) |
| A07 Auth Failures | 🔴 | SEC-001 (timing attack) |
| A08 Data Integrity | ✅ 양호 | |
| A09 Logging/Monitoring | 🟡 | PR-006 (헬스체크 없음) |
| A10 SSRF | ✅ 양호 | 바코드 API 외부 호출은 고정 URL |

## Action Items
| # | 제목 | 위험도 | 작업량 |
|---|------|--------|--------|
| SEC-001 | Admin 토큰 timing-safe 비교 | 🔴 | S |
| SEC-002 | Dockerfile non-root 사용자 | 🔴 | S |
| SEC-003 | CORS 프로덕션 검증 강화 | 🟡 | S |
| SEC-004 | APP_TOKEN 기본값 경고 | 🟡 | S |
| SEC-005 | 클라이언트 토큰 보안 검토 | 🟡 | M |
| SEC-006 | requirements.txt 버전 고정 | 🟢 | S |
| SEC-007 | .dockerignore 생성 | 🟢 | S |
