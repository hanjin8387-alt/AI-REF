# AI REF (PROMETHEUS)

현재 체크아웃 기준으로 동작하는 식재료 관리 앱/서버 저장소입니다.

## 저장소 구조

- `prometheus-api/`: FastAPI 백엔드
- `prometheus-app/`: Expo React Native 프론트엔드
- `scripts/perf-smoke.sh`: 인증 기반 성능 스모크 스크립트
- `docs/`: 갭 리포트, 리팩터링 설계, 아키텍처/마이그레이션 노트

## 지원 워크플로

현재 체크아웃 기준 공식 지원 경로는 로컬/개발 실행입니다.

- Docker/Cloud Run 배포 파일은 현재 체크아웃에서 제거되어 있으므로 이 README는 로컬 기준만 문서화합니다.

## Backend 실행 (`prometheus-api`)

### 1) 의존성 설치

```bash
cd prometheus-api
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

### 2) 환경 변수 준비

```bash
copy .env.example .env
```

필수 핵심 값:

- `APP_IDS` (예: `prometheus-app,prometheus-web`)
- `SUPABASE_URL`, `SUPABASE_KEY`
- `GEMINI_API_KEY`

### 3) 마이그레이션 적용

```bash
# DATABASE_URL 환경변수 필요
bash scripts/apply-migrations.sh
```

또는 `migrations/0001_initial.sql` -> `migrations/0002_auth_idempotency.sql` 순서로 직접 적용합니다.

### 4) 서버 실행

```bash
uvicorn app.main:app --reload
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
- `EXPO_PUBLIC_APP_TOKEN` (레거시 호환이 필요한 경우에만)

### 3) 개발 서버

```bash
npm run start
```

## 인증 모델 요약

- 기본 앱 식별: `X-App-ID` (공개 식별자)
- 레거시 호환: `X-App-Token` (서버 설정 시에만 허용)
- 디바이스 인증: `X-Device-ID` + `X-Device-Token`
  - 토큰은 서버 발급/회전/폐기 가능
  - 해시 저장, 만료/버전/마지막 사용 시각 추적

## 검증 명령

### Backend

```bash
cd prometheus-api
python -m compileall app
pytest -q
```

### Frontend

```bash
cd prometheus-app
npm run typecheck
npm run lint
npm test
```

## 성능 스모크

```bash
API_URL=http://localhost:8000 \
APP_ID=prometheus-app \
DEVICE_ID=perf-smoke-device \
DEVICE_TOKEN=<device-token> \
bash scripts/perf-smoke.sh
```

`DEVICE_TOKEN` 없이 실행하면 실패하도록 설계되어 있습니다.

## 참고 문서

- `docs/repo-gap-report.md`
- `docs/refactor-design.md`
- `docs/architecture-note.md`
- `docs/migration-note.md`
