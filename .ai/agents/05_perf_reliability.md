# Agent 05: Performance & Reliability

> **에이전트 역할**: 성능·안정성·모니터링 개선  
> **결과 파일**: `.ai/reports/YYYY-MM-DD_perf_reliability.md`

---

## Mission

PROMETHEUS의 응답 속도, 리소스 효율, 장애 대응력을 점검하고 병목 제거 및 안정성 강화 방안을 제시한다.

## Scope

- 백엔드 API 응답 시간, DB 쿼리 효율, 캐시 전략
- 프론트엔드 렌더링 성능, 오프라인 캐시 관리
- 에러 복구 메커니즘, 모니터링/로깅

## Non-Goals

- 기능 버그 → Agent 01 · UI/UX → Agent 02 · 보안 → Agent 06

---

## Inputs

### 백엔드
| 우선순위 | 파일 | 확인 포인트 |
|----------|------|------------|
| 🔴 | `api/scans.py` | 업로드 크기, Gemini 타임아웃, 동시 요청 |
| 🔴 | `api/recipes.py` | 추천 응답 시간, 캐시 HIT률 |
| 🔴 | `services/gemini_service.py` | 타임아웃, 재시도, 동시 호출 제한 |
| 🟡 | `services/inventory_service.py` | bulk_upsert 대량 데이터 |
| 🟡 | `services/recipe_cache.py` | 메모리 크기 제한, TTL |
| 🟡 | `api/stats.py` | 대량 로그 집계 |
| 🟡 | `core/database.py` | 커넥션 풀, 재연결 |

### 프론트엔드
| 우선순위 | 파일 | 확인 포인트 |
|----------|------|------------|
| 🔴 | `services/http-client.ts` | 타임아웃, 재시도, 동시 요청 제한 |
| 🟡 | `app/(tabs)/inventory.tsx` | FlatList 최적화 |
| 🟡 | `services/offline-cache.ts` | 용량 제한, 정리 전략 |
| 🟢 | `components/*.tsx` | React.memo, 불필요한 리렌더 |

### 인프라
| 우선순위 | 파일 | 확인 포인트 |
|----------|------|------------|
| 🟡 | `Dockerfile` | 이미지 최적화, 멀티스테이지 |
| 🟡 | `schema.sql` | 인덱스 적정성 |

---

## Review Checklist

### API 성능
- [ ] N+1 쿼리 패턴 없는가?
- [ ] `SELECT *` 대신 필요 컬럼만 조회하는가?
- [ ] 대량 응답에 페이지네이션 적용되어 있는가?
- [ ] Gemini 호출에 타임아웃 설정되어 있는가?

### 캐시 효율
- [ ] 서버 캐시 TTL 적절한가?
- [ ] 메모리 캐시 최대 크기 제한되어 있는가?
- [ ] 오프라인 캐시에 용량 제한/정리 있는가?

### 에러 복구
- [ ] 외부 서비스 장애 시 graceful degradation 되는가?
- [ ] 재시도에 지수 백오프 적용되는가?
- [ ] DB 커넥션 실패 시 재연결 되는가?

### 프론트 성능
- [ ] FlatList에 `getItemLayout` 최적화 적용되어 있는가?
- [ ] 불필요한 리렌더 없는가?

### 모니터링
- [ ] 핵심 메트릭 추적 가능한가?
- [ ] 헬스체크 엔드포인트 있는가?

---

## Output Template

```markdown
# Performance & Reliability Report – YYYY-MM-DD

## Summary
- **발견 항목**: 🔴 N / 🟡 N / 🟢 N

## Findings

### 🔴 Critical
#### PR-001: <제목>
- **영역**: API 성능 / 캐시 / 에러 복구 / 프론트 성능
- **파일**: `<경로>`
- **현재 상태**: <수치/문제>
- **영향**: <지연/누수/중단 등>
- **권장 조치**: <수정 방안>
- **예상 개선**: <수치 예측>
- **작업량**: S / M / L / XL

### 🟡 Warning · 🟢 Info (동일 형식)

## Performance Baseline
| 엔드포인트 | 추정 p95 | 목표 | 상태 |
|-----------|---------|------|------|
| POST /scans/upload | ~5s | ≤3s | 🟡 |

## Action Items
| # | 제목 | 위험도 | 작업량 | 영향 |
|---|------|--------|--------|------|
```

---

## Codex Handoff

1. **보고서 읽기** → 우선순위 정렬 (🔴→🟡→🟢)
2. **변경 실행** (항목당 1 커밋):
   - 코드 수정 + 테스트 + 커밋: `perf(api): PR-001 add timeout to gemini calls`
3. **성능 검증**: 벤치마크 비교 (가능 시)
4. **PR 요약** 작성
