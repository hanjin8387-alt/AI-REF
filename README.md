# AI REF (PROMETHEUS)

[![CI](https://github.com/hanjin8387-alt/AI-REF/actions/workflows/ci.yml/badge.svg)](https://github.com/hanjin8387-alt/AI-REF/actions/workflows/ci.yml)

현재 체크아웃 기준으로 **실행 + 검증에 필요한 파일만 유지**한 식재료 관리 앱/서버 저장소입니다.

## 저장소 구조

- `prometheus-api/`: FastAPI 백엔드
- `prometheus-app/`: Expo React Native 프론트엔드
- `scripts/`: 로컬/CI 공통 검증 스크립트

## 표준 검증 (로컬, CI와 동일한 기준)

```bash
bash scripts/validate-all.sh
```

- 검증 결과는 `artifacts/` 하위에 생성됩니다.
- 기본 경로:
  - `artifacts/backend/junit.xml`
  - `artifacts/frontend/junit.xml`
  - `artifacts/validation-summary.json`
  - `artifacts/docs/config-drift.json`
  - `artifacts/docs/readme-command-check.json`
  - `artifacts/docs/optional-smoke.json`

선택적 라이브 smoke 검증(기본은 skip):

```bash
RUN_LIVE_SMOKE=true SMOKE_API_URL=http://localhost:8000 SMOKE_APP_ID=prometheus-app bash scripts/validate-all.sh --mode docs --skip-install
```

## Backend 실행 (`prometheus-api`)

### 1) 의존성 설치

```bash
cd prometheus-api
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

### 2) 환경 변수 준비

```bash
cd prometheus-api
copy .env.example .env
```

필수 핵심 값:

- `APP_IDS` (예: `prometheus-app,prometheus-web`)
- `SUPABASE_URL`, `SUPABASE_KEY`
- `GEMINI_API_KEY`

기본값/마이그레이션 관련:

- `GEMINI_MODEL=gemini-2.5-flash`
- `ALLOW_LEGACY_APP_TOKEN=false`
- `REQUIRE_APP_TOKEN=false`
- `APP_TOKEN` 은 `ALLOW_LEGACY_APP_TOKEN=true` 일 때만 필요

### 3) 마이그레이션 적용

```bash
# DATABASE_URL, psql 필요
cd prometheus-api
bash scripts/apply-migrations.sh
```

또는 `migrations/0001_initial.sql` -> `migrations/0002_auth_idempotency.sql` 순서로 직접 적용합니다.

### 4) 서버 실행

```bash
cd prometheus-api
uvicorn app.main:app --reload
```

### 5) 백엔드 테스트

```bash
cd prometheus-api
python -m pytest -q tests
```

## Frontend 실행 (`prometheus-app`)

### 1) 의존성 설치

```bash
cd prometheus-app
npm ci
```

### 2) 런타임 환경 변수(선택)

- `EXPO_PUBLIC_API_URL` (기본: `http://localhost:8000`)
- `EXPO_PUBLIC_APP_ID` (기본: `prometheus-app`)
- `EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN` (기본: `false`)
- `EXPO_PUBLIC_APP_TOKEN` (`EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN=true` 일 때만 사용)

### 3) 개발 서버

```bash
cd prometheus-app
npm run start
```

### 4) 프론트 검증

```bash
cd prometheus-app
npm run typecheck
npm run test
```

## 인증 모델 및 레거시 전환

- 기본 앱 식별: `X-App-ID` (공개 식별자)
- 레거시 호환: `X-App-Token` (명시적 opt-in일 때만 허용)
- 디바이스 인증: `X-Device-ID` + `X-Device-Token`

레거시 토큰 호환을 사용하려면 서버에서 아래를 명시해야 합니다.

- `ALLOW_LEGACY_APP_TOKEN=true`
- `APP_TOKEN=<legacy-secret>`

프론트엔드에서도 아래를 명시해야만 레거시 토큰을 전송합니다.

- `EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN=true`
- `EXPO_PUBLIC_APP_TOKEN=<legacy-token>`

서버는 레거시 토큰 경로 사용 시 구조화된 경고 로그와 카운터를 기록합니다.
운영 관찰이 필요하면 관리자 토큰으로 `GET /admin/legacy-auth-metrics` 를 조회할 수 있습니다.

### 레거시 Sunset 경로

1. `X-App-ID` 기반 호출 전환 완료 전까지만 `ALLOW_LEGACY_APP_TOKEN=true` 유지
2. 로그/카운터로 레거시 사용량 관찰
3. 사용량 0 확인 후 `ALLOW_LEGACY_APP_TOKEN=false` 고정

## GitHub Actions CI

표준 CI는 OpenAI 비밀 키 없이 동작합니다.

- `Backend Test`: 설치 + `pytest` + JUnit 업로드
- `Frontend Typecheck + Test`: `npm ci`, `typecheck`, `vitest` JUnit 업로드
- `Docs Drift + Validation Summary`: drift/readme/smoke(옵션) 검증 + 요약 업로드

업로드 아티팩트 이름:

- `backend-test-results`
- `frontend-test-results`
- `docs-validation-results`
