# Observability / Analytics Report – 2026-02-13

## Summary
- **발견 항목**: 🔴 Critical: 1 / 🟡 Warning: 4 / 🟢 Info: 2

---

## Current State
| 영역 | 상태 | 비고 |
|------|------|------|
| 구조화 로그 | ❌ | `logger.info("message")` 자유형, JSON 미사용 |
| 메트릭 수집 | ❌ | Prometheus/StatsD 클라이언트 없음 |
| 분산 트레이싱 | ❌ | OpenTelemetry 미도입 |
| 에러 리포팅 | ❌ | Sentry/Bugsnag 미연동 |
| 이벤트/퍼널 | ❌ | 사용자 행동 추적 없음 |
| 헬스체크 | ❌ | `/health` 엔드포인트 없음 |
| request_id | ❌ | 요청별 ID 미들웨어 없음 |

---

## Findings

### 🔴 Critical

#### OA-001: 요청 추적 ID(request_id) 미존재
- **파일**: `prometheus-api/app/main.py`
- **근거**: 미들웨어에 request_id 생성/전파 로직 없음. 에러 발생 시 특정 요청 추적 불가.
- **영향**: 프로덕션 디버깅 극도로 어려움
- **권장 조치**: 미들웨어에서 `X-Request-ID` 헤더 읽기/생성 → 로그에 포함 → 응답 헤더에 반환
- **위험도**: 🔴

### 🟡 Warning

#### OA-002: 로그에 device_id 컨텍스트 불일치
- **파일**: 라우터 전반
- **근거**: 일부 `logger.info()` 호출에 device_id 포함, 일부 누락
- **권장 조치**: 모든 로그에 `device_id=` 키워드 인자 필수화

#### OA-003: 외부 API 호출(Gemini, 바코드) 소요시간 미로깅
- **파일**: `gemini_service.py`, `scans.py` (바코드 API)
- **근거**: API 호출 전후 타이밍 비교 로직 없음
- **권장 조치**: `time.perf_counter()` 로 측정 → `logger.info("gemini_call", duration_ms=...)` 구조화

#### OA-004: 핵심 비즈니스 이벤트 로깅 부재
- **대상**: 스캔 완료, 요리 완료, 장보기 체크아웃, 유통기한 알림
- **근거**: 이벤트 레벨 로그가 존재하지 않아 퍼널 분석 불가
- **권장 조치**: 이벤트 스키마 정의 + 각 트리거 포인트에 `logger.info("event.<name>", ...)` 추가

#### OA-005: 프론트엔드 에러/크래시 리포팅 없음
- **파일**: `prometheus-app/` 전반
- **근거**: 글로벌 에러 바운더리 없음, 네이티브 크래시 리포팅 미연동
- **권장 조치**: `ErrorBoundary` 컴포넌트 및 expo-updates + Sentry 연동 검토

### 🟢 Info

#### OA-006: `LOG_LEVEL` 설정 존재하나 런타임 변경 불가
- **파일**: `config.py` — `log_level: str = "INFO"`
- 환경변수로 설정 가능하나 런타임 변경(hot-reload) 미지원

#### OA-007: SlowAPI 레이트리밋 초과 시 로깅 없음
- 429 응답만 반환, 누가 초과했는지 로그 미기록

---

## Event Schema Proposal
| 이벤트명 | 트리거 | 포함 데이터 | 분석 가치 |
|---------|--------|-----------|----------|
| `scan.completed` | 스캔 처리 완료 | device_id, source_type, item_count, duration_ms | 스캔 성공률, 처리 시간 |
| `scan.failed` | 스캔 처리 실패 | device_id, error_type, source_type | 실패 원인 분포 |
| `recipe.recommended` | 추천 응답 | device_id, recipe_count, cache_hit, duration_ms | 캐시 효율 |
| `cooking.completed` | 요리 완료 | device_id, recipe_id, servings, items_deducted | 사용 빈도 |
| `shopping.checkout` | 장보기 체크아웃 | device_id, item_count, added_to_inventory | 전환율 |
| `expiry.alert` | 유통기한 알림 발송 | device_id, item_count, days_to_expiry | 알림 효과 |
| `error.api` | API 에러 발생 | device_id, endpoint, status_code, error | 에러 분포 |

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|
| 1 | `main.py` | request_id 미들웨어 추가 | `pytest tests/ -v` | 응답 헤더에 X-Request-ID | 🔴 |
| 2 | 라우터 전반 | 로그에 device_id 필수 포함 | `pytest tests/ -v` | 모든 로그에 device_id | 🟡 |
| 3 | `gemini_service.py`, `scans.py` | 외부 API 소요시간 로깅 | `pytest tests/ -v` | duration_ms 로그 확인 | 🟡 |
| 4 | 라우터 전반 | 비즈니스 이벤트 로깅 추가 | `pytest tests/ -v` | 이벤트 로그 7종 | 🟡 |
| 5 | 프론트 전반 | ErrorBoundary 도입 | `npm test` | 미처리 에러 캡처 | 🟡 |

## Risk & Rollback
- 로깅 변경은 기능 무관, 롤백 리스크 최소
- request_id 미들웨어는 성능 영향 미미 (UUID 생성 < 1μs)
- 이벤트 로깅 과다 시 로그 볼륨 증가 → 로그 레벨/샘플링으로 제어
