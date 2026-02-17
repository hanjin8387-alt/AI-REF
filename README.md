# AI REF

> AI 에이전트 오케스트레이션 참조 아키텍처 — PROMETHEUS 프로젝트

코드 리뷰, 기능 강화, 성능 최적화를 위한 **AI 에이전트 워크플로우·스킬·리포트·실행계획** 모음.

---

## 프로젝트 구조

```
AI-REF/
├── prometheus-api/          # FastAPI 백엔드 (Python 3.11+)
├── prometheus-app/          # React Native / Expo SDK 52 (TypeScript)
├── scripts/                 # 유틸리티 스크립트 (perf-smoke 등)
└── .ai/                     # AI 에이전트 산출물
    ├── CODEX_Skill.md       # Codex 실행 스킬 (최신: 성능 최적화)
    ├── Skill.md             # 범용 AI 스킬 정의
    ├── workflow.md           # 코드리뷰 워크플로우
    ├── feature_cycle_workflow.md  # 기능강화 사이클 (6단계)
    ├── perf_cycle_workflow.md     # 성능최적화 사이클 (7단계)
    ├── agents/              # 서브에이전트 스킬 정의 (21개)
    ├── reports/             # 에이전트 분석 리포트 (28개)
    └── plans/               # 마스터 실행계획 (3개)
```

## AI 에이전트 사이클

### 1. 코드 리뷰 사이클
- 코드 품질·보안·테스트·UX 종합 리뷰
- 산출물: `.ai/reports/2026-02-13_*` (6개 리포트)

### 2. 기능 강화 사이클 (Feature Enhancement)
- 7개 서브에이전트: 아키텍처, UI/UX, 백엔드, 테스트, 관측성, 성능, 보안
- 58건 발견 → P0(9)/P1(16)/P2(14) 우선순위
- 산출물: `.ai/plans/2026-02-13_feature_master_plan.md`

### 3. 성능 최적화 사이클 (Performance Optimization)
- 8개 서브에이전트: 프로파일링, 프론트렌더, 백엔드레이턴시, 네트워크, 번들, 체감속도, 안정성, 관측
- 40건 발견 → P0(8)/P1(15)/P2(14) + 성능 예산(perf budget)
- **"측정 없이 최적화 금지"** 원칙
- 산출물: `.ai/plans/2026-02-13_perf_master_plan.md`

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
