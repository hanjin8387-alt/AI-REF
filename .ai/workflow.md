# PROMETHEUS – 리뷰/개선 1회 사이클 워크플로우

> **버전**: 1.0 · **최종 수정**: 2026-02-13  
> 이 문서는 리뷰 → 설계 → Codex 구현 → 테스트 → 회귀점검 → 정리의 **1회 사이클** 절차, 각 단계별 산출물, 완료 조건(Definition of Done)을 정의한다.

---

## 전체 흐름 요약

```
Phase 1: 리뷰 (Scan & Review)
    ↓
Phase 2: 설계 (Design & Plan)
    ↓
Phase 3: Codex 구현 (Implementation)
    ↓
Phase 4: 테스트 (Verification)
    ↓
Phase 5: 회귀점검 (Regression Check)
    ↓
Phase 6: 정리 (Wrap-up)
```

---

## Phase 1: 리뷰 (Scan & Review)

### 절차
1. **저장소 스캔**: 변경된 파일 또는 전체 코드베이스를 대상으로 각 에이전트 실행
2. **에이전트 보고서 생성**: 6개 에이전트가 각각 독립적으로 보고서 작성
3. **보고서 통합**: 모든 발견 사항을 위험도별로 분류

### 산출물
| 산출물 | 경로 |
|--------|------|
| Code Review 보고서 | `.ai/reports/YYYY-MM-DD_code_review.md` |
| UI/UX 보고서 | `.ai/reports/YYYY-MM-DD_uiux.md` |
| Test Engineering 보고서 | `.ai/reports/YYYY-MM-DD_test_engineering.md` |
| Feature Discovery 보고서 | `.ai/reports/YYYY-MM-DD_feature_discovery.md` |
| Perf & Reliability 보고서 | `.ai/reports/YYYY-MM-DD_perf_reliability.md` |
| Security & Privacy 보고서 | `.ai/reports/YYYY-MM-DD_security_privacy.md` |

### 완료 조건 (DoD)
- [ ] 6개 에이전트 보고서가 모두 생성됨
- [ ] 모든 🔴 Critical 항목이 식별·태그됨
- [ ] 보고서 간 중복 발견 사항이 교차참조됨

---

## Phase 2: 설계 (Design & Plan)

### 절차
1. 🔴 Critical 항목 우선 → 해결 방안 설계
2. 🟡 Warning 항목 중 Quick-win(S/M) 선별
3. 각 변경에 대해 **구현 계획서** 작성

### 산출물
| 산출물 | 경로 |
|--------|------|
| 구현 계획서 | `.ai/reports/YYYY-MM-DD_implementation_plan.md` |
| 백로그 갱신 | `.ai/reports/backlog.md` (누적) |

### 구현 계획서 포함 항목
```markdown
## 변경 #N: <제목>

- **위험도**: 🔴 / 🟡 / 🟢
- **영향 파일**: 파일 경로 리스트
- **변경 내용**: 구체적 수정 사항
- **테스트 계획**: 어떤 테스트를 추가/수정할지
- **롤백 계획**: 문제 발생 시 복구 방안
- **예상 작업량**: S / M / L / XL
```

### 완료 조건 (DoD)
- [ ] 모든 🔴 항목에 대해 구현 계획 수립
- [ ] 각 계획에 테스트 전략과 롤백 계획 포함
- [ ] 인간 리뷰어가 🔴 항목 계획을 승인

---

## Phase 3: Codex 구현 (Implementation)

### 절차
1. 구현 계획서의 변경을 **위험도 높은 순서**로 실행
2. 변경 1건 = 커밋 1개 (Conventional Commits)
3. 각 커밋 후 로컬 테스트 수행

### Codex 작업 지시 형식
```
1. <파일 경로>에서 <구체적 변경> 수행
2. <관련 테스트 파일>에 테스트 추가/수정
3. `pytest` / `npm test` 실행하여 통과 확인
4. 커밋: `<type>(<scope>): <description>`
5. CHANGELOG에 변경 사항 추가
```

### 산출물
| 산출물 | 설명 |
|--------|------|
| 커밋 로그 | Conventional Commits 형식 |
| 변경 로그 | `.ai/reports/YYYY-MM-DD_changelog.md` |

### 완료 조건 (DoD)
- [ ] 계획된 모든 변경이 개별 커밋으로 반영됨
- [ ] 각 커밋의 로컬 테스트가 통과함
- [ ] 변경 로그가 작성됨

---

## Phase 4: 테스트 (Verification)

### 절차
1. **단위 테스트**: `pytest` (백엔드), `jest` (프론트엔드)
2. **통합 테스트**: API 엔드포인트 E2E 호출
3. **수동 검증**: UI 변경 시 화면 캡처 및 비교

### 산출물
| 산출물 | 경로 |
|--------|------|
| 테스트 결과 보고서 | `.ai/reports/YYYY-MM-DD_test_results.md` |

### 완료 조건 (DoD)
- [ ] 전체 테스트 스위트 통과 (exit code 0)
- [ ] 신규 코드의 테스트 커버리지 ≥ 80%
- [ ] 🔴 변경에 대해 통합 테스트 통과

---

## Phase 5: 회귀점검 (Regression Check)

### 절차
1. 변경 전 후 **동일 기능 셋** 비교 테스트
2. 기존 기능이 깨지지 않았는지 확인
3. 성능 수치 비교 (해당 시)

### 검증 체크리스트
- [ ] 재료 스캔 → 재고 저장 플로우 정상 동작
- [ ] 레시피 추천 → 요리 완료 플로우 정상 동작
- [ ] 장보기 → 재고 반영 플로우 정상 동작
- [ ] 유통기한 알림 플로우 정상 동작
- [ ] 오프라인 모드 동작 확인
- [ ] API Rate Limiting 정상 동작

### 완료 조건 (DoD)
- [ ] 핵심 비즈니스 플로우 4개 모두 정상
- [ ] 기존 테스트 스위트 전체 통과
- [ ] 성능 지표에 유의미한 하락 없음

---

## Phase 6: 정리 (Wrap-up)

### 절차
1. PR 요약 작성
2. 백로그 갱신: 잔여 항목 정리
3. 보고서 아카이브

### 산출물
| 산출물 | 경로 |
|--------|------|
| PR 요약 | `.ai/reports/YYYY-MM-DD_pr_summary.md` |
| 갱신된 백로그 | `.ai/reports/backlog.md` |

### PR 요약 템플릿
```markdown
## PR Summary – YYYY-MM-DD

### 변경 요약
- 총 N개 변경, M개 커밋

### 변경 목록
| # | 제목 | 위험도 | 파일 | 상태 |
|---|------|--------|------|------|
| 1 | ... | 🔴 | ... | ✅ 완료 |

### 테스트 결과
- 단위: X passed / Y total
- 통합: X passed / Y total

### 잔여 항목 (백로그 이관)
- ...
```

### 완료 조건 (DoD)
- [ ] PR 요약이 작성되고 리뷰어가 확인함
- [ ] 백로그가 갱신됨
- [ ] 모든 보고서가 `.ai/reports/`에 아카이브됨
