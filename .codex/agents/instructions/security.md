# Security 점검 지침

## 개요
OWASP Top 10 및 모바일 앱 보안 기준으로 PROMETHEUS 코드베이스를 점검합니다.

## 체크리스트

### A01: Broken Access Control
- [ ] 모든 API 엔드포인트에 `require_app_token` 의존성 주입 확인
- [ ] `device_id` 기반 데이터 격리가 모든 쿼리에 적용되는지 확인
- [ ] Admin 엔드포인트의 별도 인증 토큰 검증 방식 확인
- [ ] 다른 device_id의 데이터에 접근 가능한 경로 탐색

### A02: Cryptographic Failures
- [ ] 토큰 비교에 `secrets.compare_digest()` 사용 여부
- [ ] 민감 정보 (API 키, DB 비밀번호)의 환경변수 관리
- [ ] 클라이언트 번들에 포함된 비밀값 확인

### A03: Injection
- [ ] Supabase 쿼리의 파라미터 바인딩 확인
- [ ] `ilike` / `like` 패턴에서 사용자 입력 이스케이프 확인
- [ ] AI 출력의 JSON 파싱 후 필드 검증

### A04: Insecure Design
- [ ] Rate limiting 설정 확인 (slowapi)
- [ ] 파일 업로드 크기/타입 제한 확인
- [ ] 백업 복원 시 입력 데이터 스키마 검증

### A05: Security Misconfiguration
- [ ] CORS 설정: 프로덕션에서 와일드카드 허용 여부
- [ ] 디버그 모드 프로덕션 노출 여부
- [ ] Dockerfile 보안 (non-root user, 최소 이미지)

### A07: Identification and Authentication Failures
- [ ] Device ID 생성 알고리즘의 충돌 가능성
- [ ] FCM 토큰 갱신 및 무효화 처리

### A08: Software and Data Integrity Failures
- [ ] 의존성 버전 고정 여부
- [ ] Gemini AI 응답의 무결성 검증

### A09: Security Logging and Monitoring Failures
- [ ] 보안 이벤트 로깅 (실패한 인증, 권한 위반)
- [ ] 민감 정보 로그 유출 여부
