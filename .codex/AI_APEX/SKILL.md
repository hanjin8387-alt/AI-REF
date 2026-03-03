---
name: AI_APEX Multi-Agent Code Inspection
description: Codex CLI 다중 에이전트를 활용한 코드베이스 전수 점검 프레임워크
---

# AI_APEX SKILL

## 목적
OpenAI Codex CLI의 multi-agent 기능을 활용하여 코드베이스를 6개 전문 에이전트로 **병렬 전수 점검**합니다.
이 스킬은 Gemini, Codex, 또는 다른 AI 에이전트가 이 프레임워크를 이해하고 활용할 수 있도록 합니다.

## 프레임워크 구조

### 설정 파일
- `.codex/config.toml` — 에이전트 역할 등록 및 `multi_agent = true` 활성화
- `.codex/agents/*.toml` — 에이전트별 모델/샌드박스/지침 설정
- `.codex/agents/instructions/*.md` — 에이전트별 상세 체크리스트

### 에이전트 목록

| 에이전트 | config 파일 | 지침 파일 | 모드 |
|---------|------------|----------|------|
| `dead-code` | `agents/dead-code.toml` | `agents/instructions/dead-code.md` | read-only |
| `security` | `agents/security.toml` | `agents/instructions/security.md` | read-only |
| `performance` | `agents/performance.toml` | `agents/instructions/performance.md` | read-only |
| `quality` | `agents/quality.toml` | `agents/instructions/quality.md` | read-only |
| `architecture` | `agents/architecture.toml` | `agents/instructions/architecture.md` | read-only |
| `db-schema` | `agents/db-schema.toml` | `agents/instructions/db-schema.md` | read-only |

## 사용법

### Codex CLI에서 실행
```bash
# 프로젝트 디렉토리에서 Codex 시작
cd <프로젝트 루트>
codex

# multi-agent 활성화 확인
/experimental → multi_agent 활성화

# 전체 점검 프롬프트 입력 (prompts.md 참조)
```

### 개별 에이전트 실행
특정 점검만 실행하고 싶을 때:
```
dead-code 에이전트를 실행하여 prometheus-api/ 코드에서 미사용 import와 변수를 찾아라.
.codex/agents/instructions/dead-code.md를 읽고 해당 지침에 따라 점검하라.
```

### Gemini에서 활용
이 스킬 파일을 참조하여 `.codex/` 폴더 구조를 이해하고,
각 에이전트의 지침 파일을 기반으로 코드를 분석할 수 있습니다.

## 점검 대상 프로젝트
- `prometheus-api/` — Python FastAPI 백엔드 (~2,500 LOC)
- `prometheus-app/` — TypeScript React Native Expo 프론트엔드 (~4,500 LOC)
- `prometheus-api/schema.sql` — PostgreSQL 스키마 (321 lines)

## 출력 기대값
각 에이전트는 아래 형식으로 결과를 반환합니다:

```markdown
## [에이전트명] 점검 결과

### 요약
- 발견 건수: N건
- Critical: X건, High: Y건, Medium: Z건, Low: W건

### 상세 발견 사항
(에이전트별 출력 형식에 따라)
```

오케스트레이터는 이를 수집하여 통합 보고서를 작성합니다.
