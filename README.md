# AI REF (PROMETHEUS)

현재 체크아웃 기준으로 **실행에 필요한 파일만 유지**한 식재료 관리 앱/서버 저장소입니다.

## 저장소 구조

- `prometheus-api/`: FastAPI 백엔드 실행 코드
- `prometheus-app/`: Expo React Native 프론트엔드 실행 코드

## 지원 워크플로

현재 공식 지원 경로는 **로컬 실행**입니다.

## Backend 실행 (`prometheus-api`)

### 1) 의존성 설치

```bash
cd prometheus-api
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
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

또는 `migrations/0001_initial.sql` → `migrations/0002_auth_idempotency.sql` 순서로 직접 적용합니다.

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
