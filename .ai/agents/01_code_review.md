# Agent 01: Code Review

> **에이전트 역할**: 코드 품질·아키텍처·버그 탐지  
> **결과 파일**: `.ai/reports/YYYY-MM-DD_code_review.md`

---

## Mission

PROMETHEUS 코드베이스의 구조적 건전성, 코드 품질, 잠재 버그를 체계적으로 점검하고 개선 방안을 제시한다.

## Scope

- 백엔드: `prometheus-api/app/` 전체 (라우터, 서비스, 스키마, 코어)
- 프론트엔드: `prometheus-app/` (서비스, 컴포넌트, 화면, 유틸)
- 설정: `Dockerfile`, `requirements.txt`, `package.json`, `schema.sql`

## Non-Goals

- UI 디자인 평가 → Agent 02 (UI/UX)
- 테스트 커버리지 측정 → Agent 03 (Test Engineering)
- 기능 제안 → Agent 04 (Feature Discovery)

---

## Inputs (우선순위 파일 및 확인 포인트)

### 백엔드 (High → Low)
| 우선순위 | 파일/영역 | 확인 포인트 |
|----------|-----------|-------------|
| 🔴 High | `app/api/*.py` | device_id 필터 누락, 인가 우회, 입력 검증 |
| 🔴 High | `app/services/gemini_service.py` | AI 응답 파싱 안전성, 예외 처리 |
| 🔴 High | `app/core/security.py` | 인증 로직 완전성, timing attack 방지 |
| 🟡 Mid | `app/services/inventory_service.py` | upsert 동시성, 데이터 정합성 |
| 🟡 Mid | `app/schemas/schemas.py` | Pydantic 검증 범위, Optional 필드 남용 |
| 🟡 Mid | `app/services/recipe_cache.py` | 캐시 무효화 누수, 메모리 사용량 |
| 🟢 Low | `app/main.py` | 미들웨어 순서, 라우터 등록 누락 |
| 🟢 Low | `requirements.txt` | 버전 고정, 취약 패키지 |

### 프론트엔드 (High → Low)
| 우선순위 | 파일/영역 | 확인 포인트 |
|----------|-----------|-------------|
| 🔴 High | `services/api.ts` | 에러 핸들링, 캐시 무효화 일관성 |
| 🔴 High | `services/http-client.ts` | 타임아웃, 재시도, 토큰 노출 |
| 🟡 Mid | `app/(tabs)/*.tsx` | 상태 관리, 메모리 누수 (cleanup), useFocusEffect 남용 |
| 🟡 Mid | `components/*.tsx` | Props 타입 안전성, 재렌더링 최적화 |
| 🟢 Low | `constants/Colors.ts` | 하드코딩 컬러 vs 토큰 일치 |

---

## Review Checklist

### 아키텍처
- [ ] 라우터-서비스-DB 계층 분리가 일관적인가?
- [ ] 순환 의존성이 없는가?
- [ ] 에러 처리 패턴이 통일되어 있는가? (HTTPException 형식, 에러 코드)
- [ ] 설정 값이 하드코딩되지 않고 `config.py`에서 관리되는가?

### 코드 품질
- [ ] 사용되지 않는 import, 변수, 함수가 없는가?
- [ ] 함수 길이가 50줄 이하인가? (초과 시 분할 검토)
- [ ] 매직 넘버/문자열이 상수로 추출되어 있는가?
- [ ] 로깅이 적절한 수준으로 적용되어 있는가? (DEBUG/INFO/WARNING/ERROR)
- [ ] 타입 힌트(Python) / TypeScript 타입이 정확한가?

### 잠재 버그
- [ ] 모든 DB 쿼리에 `.eq("device_id", device_id)` 필터가 있는가?
- [ ] Gemini 응답 `json.loads()` 호출이 try/except로 보호되는가?
- [ ] 경쟁 조건(race condition)이 발생할 수 있는 코드 패턴이 있는가?
- [ ] null/undefined 체크 누락이 없는가?
- [ ] API 응답에 민감 정보(API 키, 내부 에러 스택)가 노출되지 않는가?

### 컨벤션 준수
- [ ] 커밋 메시지 형식 (Conventional Commits)
- [ ] Import 순서 (stdlib → third-party → project)
- [ ] 네이밍 규칙 (스키마: `{Action}{Resource}Request` 등)

---

## Output Template

```markdown
# Code Review Report – YYYY-MM-DD

## Summary
- **검토 범위**: <파일 수> 파일, <라인 수> 라인
- **발견 항목**: 🔴 Critical: N / 🟡 Warning: N / 🟢 Info: N
- **추정 작업량**: S: N / M: N / L: N / XL: N

## Findings

### 🔴 Critical

#### CR-001: <제목>
- **파일**: `<경로>`
- **라인**: L<시작>–L<끝>
- **설명**: <문제 상세>
- **영향**: <데이터 손실/보안 위험/서비스 중단 등>
- **권장 조치**: <구체적 수정 방안>
- **작업량**: S / M / L / XL

### 🟡 Warning

#### CR-002: <제목>
- **파일**: `<경로>`
- **라인**: L<시작>–L<끝>
- **설명**: <문제 상세>
- **영향**: <기능 저하/UX 불일치 등>
- **권장 조치**: <구체적 수정 방안>
- **작업량**: S / M / L / XL

### 🟢 Info

#### CR-003: <제목>
- **파일**: `<경로>`
- **설명**: <개선 제안>
- **권장 조치**: <수정 방안>
- **작업량**: S / M / L / XL

## Cross-References
- 관련 에이전트 보고서 참조: Agent 06 (Security) CR-001

## Action Items
| # | 제목 | 위험도 | 작업량 | 담당 |
|---|------|--------|--------|------|
| CR-001 | ... | 🔴 | M | Codex |

## Appendix: Reviewed Files
| 파일 | 라인 수 | 주요 발견 |
|------|---------|-----------|
| `app/api/scans.py` | 150 | CR-001, CR-003 |
```

---

## Codex Handoff

Codex가 이 보고서를 받아 수행할 구체적 절차:

1. **보고서 읽기**: `.ai/reports/YYYY-MM-DD_code_review.md` 로드
2. **우선순위 정렬**: 🔴 → 🟡 → 🟢 순서, 작업량 S/M 먼저
3. **변경 실행** (항목당 1 커밋):
   ```
   a. 해당 파일 수정
   b. 관련 테스트 추가/수정 (🔴/🟡 필수)
   c. 테스트 실행: `cd prometheus-api && python -m pytest` / `cd prometheus-app && npm test`
   d. 커밋: `fix(api): CR-001 add device_id filter to scan query`
   ```
4. **변경 로그 작성**: `.ai/reports/YYYY-MM-DD_changelog.md`에 항목 추가
5. **PR 요약**: 모든 변경 완료 후 PR 요약 작성
   ```
   ## Code Review Fixes – YYYY-MM-DD
   - 🔴 Fixed N critical issues
   - 🟡 Fixed N warnings
   - 🟢 Improved N items
   - All tests passing ✅
   ```
