# AI REF

> PROMETHEUS — AI 기반 식품 관리 앱

---

## 프로젝트 구조

```
AI-REF/
├── prometheus-api/          # FastAPI 백엔드 (Python 3.11+)
├── prometheus-app/          # React Native / Expo SDK 52 (TypeScript)
└── scripts/                 # 유틸리티 스크립트
```

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | Python 3.11+ · FastAPI · Supabase (PostgreSQL + RLS) |
| 프론트 | React Native · Expo SDK 52 · TypeScript |
| AI | Google Gemini API |
| 배포 | Docker · Google Cloud Run |

## 시작하기

```bash
# 백엔드
cd prometheus-api
pip install -r requirements.txt
uvicorn app.main:app --reload

# 프론트엔드
cd prometheus-app
npm install
npx expo start
```

## 라이선스

Private — All rights reserved.
