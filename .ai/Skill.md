# PROMETHEUS – AI 리뷰/개선 오케스트레이터 Skill

> **버전**: 1.0 · **최종 수정**: 2026-02-13  
> 이 문서는 Codex 확장프로그램이 PROMETHEUS 저장소에서 분석·리뷰·테스트·개선·백로그 운영을 수행할 때 **항상 적용하는 상시 규칙**을 선언한다.

---

## 1. Assumptions (저장소 추정 및 불확실성)

| 항목 | 추정 | 불확실성 |
|------|------|----------|
| 백엔드 언어/프레임워크 | Python 3.11+ / FastAPI ≥0.115 | 낮음 – `requirements.txt`, `main.py` 확인 |
| 프론트엔드 | React Native / Expo SDK 52, TypeScript | 낮음 – `package.json`, `tsconfig.json` 확인 |
| DB | Supabase (PostgreSQL) + RLS | 낮음 – `schema.sql`, `database.py` 확인 |
| 빌드 도구(백엔드) | Docker (`Dockerfile`) | 낮음 |
| 빌드 도구(프론트) | Expo CLI / npm | 낮음 – `package.json` 확인 |
| 테스트 프레임워크 | **미확인** – pytest / jest 설정 파일 미발견 | **높음** – 테스트 구조 미설정 가능성 |
| CI/CD | **미확인** – `.github/workflows` 미발견 | **높음** |
| Linting/Formatting | **미확인** – `.eslintrc`, `ruff.toml` 미발견 | 중간 |
| 배포 | Google Cloud Run (Dockerfile 기반) | 낮음 |

---

## 2. 역할 정의

이 Skill은 **6개 에이전트 역할**을 정의한다. 각 역할의 상세 사양은 `.ai/agents/` 하위 파일에 기술된다.

| # | 에이전트 | 파일 | 핵심 미션 |
|---|---------|------|-----------|
| 01 | Code Review | `01_code_review.md` | 코드 품질·아키텍처·버그 탐지 |
| 02 | UI/UX | `02_uiux.md` | 접근성·디자인 시스템·UX 일관성 |
| 03 | Test Engineering | `03_test_engineering.md` | 테스트 커버리지·자동화·전략 수립 |
| 04 | Feature Discovery | `04_feature_discovery.md` | 신규 기능 발굴·백로그 관리 |
| 05 | Perf & Reliability | `05_perf_reliability.md` | 성능·안정성·모니터링 개선 |
| 06 | Security & Privacy | `06_security_privacy.md` | 보안·개인정보·인증/인가 점검 |

---

## 3. 상시 규칙 (Global Rules)

### 3.1 커밋 규칙
- **하나의 커밋 = 하나의 논리적 변경**. 파일 10개 이상을 한 커밋에 넣지 않는다.
- 커밋 메시지 형식: `<type>(<scope>): <description>` (Conventional Commits)
  - type: `fix`, `feat`, `refactor`, `test`, `docs`, `perf`, `security`, `style`, `chore`
  - scope: `api`, `app`, `schema`, `service`, `component`, `config`

### 3.2 위험도 분류 (Risk Level)
| 등급 | 정의 | 허용 조건 |
|------|------|-----------|
| 🔴 Critical | 데이터 손실, 보안 결함, 서비스 중단 가능 | 반드시 인간 리뷰 후 머지 |
| 🟡 Warning | 기능 저하, UX 불일치, 성능 하락 가능 | 자동화 테스트 통과 시 진행 |
| 🟢 Info | 코드 스타일, 문서 보강, 사소한 개선 | Codex 단독 진행 가능 |

### 3.3 테스트 요구사항
- 🔴 Critical 변경: 단위 + 통합 테스트 필수.
- 🟡 Warning 변경: 최소 1개 관련 테스트 필수.
- 🟢 Info 변경: 기존 테스트 통과 확인만.

### 3.4 롤백 기준
- 배포 후 **5분 내 에러율 > 5%** 또는 **p95 레이턴시 > 3초**: 즉시 이전 리비전으로 롤백.
- DB 마이그레이션은 반드시 **역방향 마이그레이션 SQL**을 함께 작성.

### 3.5 보고서 파일 경로
```
.ai/reports/YYYY-MM-DD_<agent-name>.md
```
예: `.ai/reports/2026-02-13_code_review.md`

### 3.6 언어 규칙
- 코드, 커밋 메시지, 변수명, 주석 → **영어**
- 보고서, 사용자 대면 문서 → **한국어** (사용자 선호 시)

### 3.7 의존성 변경
- `requirements.txt` 또는 `package.json` 변경 시 반드시 보고서에 명시.
- 새 패키지 추가 전 라이선스(MIT/Apache 2.0 허용)와 유지보수 상태 확인.

### 3.8 DB 스키마 변경
- `schema.sql` 변경 시 반드시 위험도 🔴 설정.
- RLS 정책 변경은 **보안 에이전트 리뷰** 필수.

---

## 4. 워크플로우 참조

1회 리뷰-개선 사이클의 절차는 `.ai/workflow.md`를 참조한다.

---

## 5. 백로그 운영 규칙

- 모든 발견 사항은 **위험도 + 예상 작업량(S/M/L/XL)** 태그.
- 에이전트 보고서에서 추출된 작업 항목은 `.ai/reports/backlog.md`에 누적.
- 우선순위: 🔴 Critical → 🟡 Warning → 🟢 Info 순서. 같은 등급 내에서는 영향 범위가 큰 순서.
- Sprint 시작 시 백로그에서 S·M 항목 우선 발췌.
