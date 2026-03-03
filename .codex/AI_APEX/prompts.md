# AI_APEX 프롬프트 템플릿

재사용 가능한 Codex CLI 프롬프트 모음입니다. 복사-붙여넣기하여 사용하세요.

---

## 🔥 P1: 전체 코드베이스 전수 점검 (권장)

```
PROMETHEUS 코드베이스 전수 점검을 시작합니다.

아래 6개 점검 항목을 각각 전담 에이전트에게 할당하여 병렬로 실행하고,
모든 결과를 수집한 후 통합 보고서를 작성해 주세요.

각 에이전트는 .codex/agents/instructions/ 폴더의 해당 지침 파일을 먼저 읽고 따릅니다.

1. Dead Code 점검 (dead-code 에이전트) → .codex/agents/instructions/dead-code.md 참조
   - 미사용 변수, 도달 불가 코드, 사용되지 않는 import, 계산되지만 사용되지 않는 값
2. Security 점검 (security 에이전트) → .codex/agents/instructions/security.md 참조
   - OWASP 기반 보안 취약점 전수 점검
3. Performance 점검 (performance 에이전트) → .codex/agents/instructions/performance.md 참조
   - 무한 성장 캐시, N+1 쿼리, 불필요한 재렌더링
4. Code Quality 점검 (quality 에이전트) → .codex/agents/instructions/quality.md 참조
   - 코드 중복, 명명 규칙 위반, 에러 처리 일관성
5. Architecture 점검 (architecture 에이전트) → .codex/agents/instructions/architecture.md 참조
   - 계층 위반, 순환 의존성, API 계약 불일치
6. DB Schema 점검 (db-schema 에이전트) → .codex/agents/instructions/db-schema.md 참조
   - FK 불일치, 인덱스 누락, 스키마-코드 동기화

통합 보고서에는:
- 각 에이전트별 발견 사항 요약
- 전체 발견 건수 (심각도별: Critical / High / Medium / Low)
- 우선 수정 권장 항목 TOP 10 (구체적 파일 위치 + 수정 diff)
을 포함해 주세요.
```

---

## 🎯 P2: 백엔드 전용 점검

```
prometheus-api/ 폴더만 대상으로 아래 4개 에이전트를 병렬 실행해 주세요.
각 에이전트는 .codex/agents/instructions/ 의 해당 지침을 먼저 읽습니다.

1. dead-code 에이전트 — 미사용 코드 전수 점검
2. security 에이전트 — 보안 취약점 전수 점검
3. performance 에이전트 — 성능 문제 전수 점검
4. quality 에이전트 — 코드 품질 점검

모든 결과를 수집하여 심각도별로 정리한 통합 보고서를 작성해 주세요.
```

---

## 🎯 P3: 프론트엔드 전용 점검

```
prometheus-app/ 폴더만 대상으로 아래 4개 에이전트를 병렬 실행해 주세요.
각 에이전트는 .codex/agents/instructions/ 의 해당 지침을 먼저 읽습니다.

1. dead-code 에이전트 — 미사용 코드/타입/스타일 점검
2. performance 에이전트 — 렌더링 최적화, 메모리 누수 점검
3. quality 에이전트 — 코드 중복, React Hook 규칙 점검
4. architecture 에이전트 — 컴포넌트 구조, 서비스 계층 점검

모든 결과를 수집하여 심각도별로 정리한 통합 보고서를 작성해 주세요.
```

---

## 🔍 P4: Dead Code 집중 점검

```
dead-code 에이전트를 실행하여 전체 코드베이스에서 다음을 찾아주세요:

1. 선언되었지만 한 번도 사용되지 않는 변수
2. import되었지만 참조되지 않는 모듈/타입
3. 정의되었지만 어디서도 호출되지 않는 함수
4. return/raise 이후의 도달 불가 코드
5. 계산되지만 결과가 사용되지 않는 표현식
6. StyleSheet에 정의되었지만 참조되지 않는 스타일

.codex/agents/instructions/dead-code.md를 먼저 읽고 따라주세요.
결과를 파일별로 그룹화하여 보고해 주세요.
```

---

## 🔒 P5: Security 집중 점검

```
security 에이전트를 실행하여 OWASP Top 10 기준으로 전수 점검해 주세요.

특히 아래 포인트에 집중:
- 모든 API 엔드포인트의 인증/인가 검증 여부
- 사용자 입력이 쿼리에 직접 전달되는 경우 (SQL/패턴 인젝션)
- AI (Gemini) 응답의 무결성 검증 여부
- 클라이언트에 노출되는 비밀값
- CORS 설정의 안전성

.codex/agents/instructions/security.md를 먼저 읽고 따라주세요.
각 취약점에 대해 구체적인 공격 시나리오와 수정 방안을 포함해 주세요.
```

---

## 🗃️ P6: DB Schema 집중 점검

```
db-schema 에이전트를 실행하여 다음을 점검해 주세요:

1. prometheus-api/schema.sql 의 각 테이블을 분석
2. Pydantic 모델 (schemas.py)과 SQL 스키마 간 타입 일치 여부
3. TypeScript 타입 (api.types.ts)과 API 응답 간 필드 일치 여부
4. 코드에서 쿼리하는 컬럼이 실제 스키마에 존재하는지
5. 누락된 외래키, 인덱스, 제약 조건

.codex/agents/instructions/db-schema.md를 먼저 읽고 따라주세요.
```

---

## 🔧 P7: 점검 후 자동 수정

```
이전 점검에서 발견된 Critical 및 High 심각도 항목을 수정해 주세요.

수정 규칙:
1. 각 수정은 하나의 논리적 변경 단위로 구성
2. 기존 기능을 훼손하지 않을 것
3. 수정 사항에 대한 테스트 코드 작성
4. 수정 전후 diff를 명확히 보여줄 것

순서: Critical → High → Medium
```

---

## 📊 P8: 변경 사항 비교 점검 (PR 리뷰)

```
현재 브랜치와 main 브랜치의 차이점을 대상으로 아래 점검을 병렬 실행해 주세요:

1. security 에이전트 — 새로 도입된 보안 문제
2. quality 에이전트 — 코드 품질 저하
3. dead-code 에이전트 — 새로 추가된 미사용 코드
4. performance 에이전트 — 성능 저하 요소

각 에이전트는 변경된 파일만 점검합니다.
```
