# Observability / Metrics Report – 2026-02-13

## Current State
| 영역 | 상태 | 비고 |
|------|------|------|
| 응답 시간 미들웨어 | ❌ | 요청 소요시간 로그/헤더 없음 |
| 외부 API duration 로그 | ❌ | Gemini/바코드 호출 시간 미기록 |
| request_id 미들웨어 | ❌ | 요청 추적 불가 |
| APM (Sentry/OTel) | ❌ | 도구 미도입 |
| 클라이언트 성능 이벤트 | ❌ | 화면 로딩/인터랙션 시간 미수집 |
| 릴리즈 비교 | ❌ | 배포 전후 지표 비교 메커니즘 없음 |
| 로그 수준 | 🟡 | `logger.info/error` 존재하나 성능 컨텍스트 없음 |

## Perf Event Schema (제안)

### 서버 사이드
| 이벤트 | 트리거 | 포함 데이터 | 분석 가치 |
|--------|--------|-----------|----------|
| `perf.request` | 모든 요청 완료 | method, path, status, duration_ms, device_id, request_id | p95/p99 추적 |
| `perf.gemini_call` | Gemini API 완료 | model, operation, duration_ms, tokens, success | 외부 의존 모니터링 |
| `perf.cache_operation` | RecipeCache hit/miss | device_id, cache_hit, operation, duration_ms | 캐시 효율 |
| `perf.db_query` | DB 쿼리 완료 | table, operation, duration_ms, row_count | 쿼리 최적화 추적 |
| `perf.upload` | 파일 업로드 완료 | file_size, duration_ms, content_type | 업로드 파이프라인 |

### 클라이언트 사이드
| 이벤트 | 트리거 | 포함 데이터 | 분석 가치 |
|--------|--------|-----------|----------|
| `perf.screen_load` | 화면 마운트 → 데이터 완료 | screen_name, duration_ms, cache_hit | TTI 추적 |
| `perf.interaction` | 사용자 액션 → 완료 | action, screen, duration_ms | 인터랙션 레이턴시 |
| `perf.api_call` | API 호출 완료 | endpoint, status, duration_ms, size, cache_hit | 네트워크 효율 |
| `perf.app_start` | 앱 시작 → 첫 화면 | duration_ms, js_bundle_size | 콜드 스타트 |
| `perf.scroll_fps` | 리스트 스크롤 | screen, avg_fps, dropped_frames | 렌더 성능 |

## Findings

### 🔴 Critical

#### OM-001: 응답 시간 미들웨어 없음 → 서버 성능 블라인드
- **파일**: `main.py`
- **유형**: 관측성
- **근거**: 요청 처리 시간을 기록하는 미들웨어가 없어 병목 식별 불가
- **권장 조치**: `ProcessTimeMiddleware` 추가 → `X-Process-Time` 헤더 + `logger.info("perf.request", ...)`
- **예상 영향**: 모든 요청의 p95/p99 추적 가능

### 🟡 Warning

#### OM-002: Gemini 호출 duration 미로깅
- **파일**: `gemini_service.py`
- **권장 조치**: `time.perf_counter()` before/after + 로그

#### OM-003: 클라이언트 성능 이벤트 수집 없음
- **파일**: `prometheus-app/` 전반
- **권장 조치**: 유틸리티 함수 `logPerfEvent(name, data)` 생성 → 핵심 화면에 적용

#### OM-004: 릴리즈 간 성능 비교 불가
- **근거**: 배포 버전별 성능 데이터 저장 없음
- **권장 조치**: 배포 시 스모크 벤치 결과를 `.ai/reports/perf_history.md`에 누적 기록

### 🟢 Info

#### OM-005: 캐시 hit/miss 로그 없음
- `recipe_cache.py`에 캐시 상태 로그 추가 시 히트율 추적 가능

## Task List
| # | 파일 | 변경요지 | 벤치 커맨드 | 테스트 커맨드 | 수용기준 | 예상 영향 | 위험도 |
|---|------|---------|-----------|-------------|---------|----------|--------|
| 1 | `main.py` | ProcessTimeMiddleware | `hey -n 50 $API/inventory` | `pytest tests/ -v` | X-Process-Time 헤더 | 관측 +100% | 🔴 |
| 2 | `gemini_service.py` | duration 로깅 | `hey -n 5 $API/scans/upload` | `pytest tests/ -v` | 로그에 duration_ms | 외부 추적 | 🟡 |
| 3 | `recipe_cache.py` | hit/miss 로그 | `hey -n 20 $API/recipes` | `pytest tests/ -v` | 로그에 cache_hit | 히트율 추적 | 🟡 |
| 4 | `services/perf-logger.ts` (신규) | 클라이언트 perf 유틸 | 수동 | `npm test` | logPerfEvent 함수 | 클라이언트 추적 | 🟡 |

## Risk & Rollback
- 로깅 추가는 기능 무관. 로그 볼륨 증가 → LOG_LEVEL로 제어.
- ProcessTimeMiddleware 오버헤드 < 1μs. 무시 가능.
