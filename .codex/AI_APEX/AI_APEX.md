# AI_APEX — 다중 에이전트 코드 전수 점검 오케스트레이터

## 개요

AI_APEX는 OpenAI Codex CLI의 **multi-agent** 기능을 활용하여 PROMETHEUS 코드베이스를
6개 전문 에이전트로 **병렬 전수 점검**하는 프레임워크입니다.

## 에이전트 구성

| 역할 | 에이전트 이름 | 점검 범위 |
|------|-------------|----------|
| 🔍 Dead Code | `dead-code` | 미사용 변수/함수/import, 도달 불가 코드, 버려지는 반환값 |
| 🔒 Security | `security` | OWASP 기반 보안 취약점, 인증/인가, 인젝션 |
| ⚡ Performance | `performance` | 캐시 누수, N+1 쿼리, 불필요한 렌더링 |
| 🧹 Quality | `quality` | 코드 중복, 명명 규칙, 에러 처리 일관성 |
| 📐 Architecture | `architecture` | 계층 위반, 순환 의존성, API 계약 |
| 🗃️ DB Schema | `db-schema` | FK 불일치, 인덱스 누락, 타입 매핑 |

## 실행 방법

### 1단계: 사전 설정
```bash
# Codex CLI에서 multi-agent 기능 활성화
codex /experimental
# → "multi_agent" 선택하여 활성화

# 또는 config에 직접 추가 (이미 .codex/config.toml에 설정됨)
```

### 2단계: 전체 점검 실행
Codex CLI에서 아래 프롬프트를 입력합니다:

```
PROMETHEUS 코드베이스 전수 점검을 시작합니다.

아래 6개 점검 항목을 각각 전담 에이전트에게 할당하여 병렬로 실행하고,
모든 결과를 수집한 후 통합 보고서를 작성해 주세요.

각 에이전트는 .codex/agents/instructions/ 폴더의 해당 지침 파일을 읽고 따릅니다.

1. Dead Code 점검 (dead-code 에이전트) → .codex/agents/instructions/dead-code.md 참조
2. Security 점검 (security 에이전트) → .codex/agents/instructions/security.md 참조
3. Performance 점검 (performance 에이전트) → .codex/agents/instructions/performance.md 참조
4. Code Quality 점검 (quality 에이전트) → .codex/agents/instructions/quality.md 참조
5. Architecture 점검 (architecture 에이전트) → .codex/agents/instructions/architecture.md 참조
6. DB Schema 점검 (db-schema 에이전트) → .codex/agents/instructions/db-schema.md 참조

통합 보고서에는:
- 각 에이전트별 발견 사항 요약
- 전체 발견 건수 (심각도별 분류)
- 우선 수정 권장 항목 TOP 10
- 각 발견 항목의 구체적인 파일 위치와 수정 방안
을 포함해 주세요.
```

### 3단계: 결과 확인
- `/agent` 명령으로 각 에이전트의 진행 상황 모니터링
- 모든 에이전트 완료 시 통합 보고서 자동 생성

## 파일 구조

```
.codex/
├── config.toml                     ← 프로젝트 설정 + 에이전트 등록
├── agents/
│   ├── dead-code.toml              ← 에이전트별 실행 설정
│   ├── security.toml
│   ├── performance.toml
│   ├── quality.toml
│   ├── architecture.toml
│   ├── db-schema.toml
│   └── instructions/
│       ├── dead-code.md            ← 에이전트별 상세 점검 지침
│       ├── security.md
│       ├── performance.md
│       ├── quality.md
│       ├── architecture.md
│       └── db-schema.md
└── AI_APEX/
    ├── AI_APEX.md                  ← 이 문서 (오케스트레이션 가이드)
    ├── SKILL.md                    ← 스킬 정의 (Gemini 등 AI 연동)
    ├── workflow.md                 ← 단계별 워크플로우
    └── prompts.md                  ← 재사용 프롬프트 템플릿
```
