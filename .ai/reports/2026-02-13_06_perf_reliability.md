# Performance / Reliability Report – 2026-02-13 (Feature Enhancement Cycle)

## Summary
- **발견 항목**: 🔴 Critical: 2 / 🟡 Warning: 5 / 🟢 Info: 2

---

## Performance Baseline (추정)
| 엔드포인트 | 추정 p95 | 목표 | 상태 |
|-----------|---------|------|------|
| POST /scans/upload | 5-10s | ≤8s | 🟡 (Gemini 의존) |
| GET /recipes/recommendations | 3-10s | ≤5s | 🟡 (캐시 miss 시 Gemini) |
| GET /inventory | ~200ms | ≤200ms | ✅ |
| POST /inventory/bulk | ~500ms | ≤500ms | ✅ |
| POST /admin/check-expiry | 1-5s | ≤3s | 🟡 (디바이스 수 비례) |
| POST /shopping/checkout | ~500ms | ≤500ms | ✅ |

---

## Findings

### 🔴 Critical

#### PR-001: Gemini API 호출에 명시적 타임아웃 없음
- **파일**: `prometheus-api/app/services/gemini_service.py`
- **근거**: `generate_content_async()` 호출에 timeout 파라미터 미설정. `google.generativeai` 기본 타임아웃(매우 긴 값)에 의존.
- **영향**: Gemini 장애 시 요청이 수분간 행 → Cloud Run 인스턴스 고갈 → 전체 서비스 중단
- **권장 조치**: `asyncio.wait_for(coro, timeout=30)` 래핑. 이미지 분석(30s)/레시피 생성(45s) 분리.
- **위험도**: 🔴

#### PR-002: 메모리 캐시(`RecipeCache`)에 최대 크기 제한 없음
- **파일**: `prometheus-api/app/services/recipe_cache.py`
- **근거**: `_recipe_store` dict 무제한 성장. `_prune_locked()`는 TTL 만료만 정리.
- **영향**: 디바이스 증가 → 메모리 사용 무한 증가 → OOM
- **권장 조치**: `max_devices=100` 제한 + LRU 퇴출
- **위험도**: 🔴

### 🟡 Warning

#### PR-003: `inventory_service.bulk_upsert`가 `SELECT *`로 전체 재고 조회
- **파일**: `inventory_service.py` L89
- **권장 조치**: 입력 아이템 이름으로 IN 절 필터링 + 컬럼 지정

#### PR-004: `/admin/check-expiry`가 모든 디바이스 재고를 한 번에 조회
- **파일**: `admin.py` L52
- **권장 조치**: 디바이스별 배치 처리 또는 커서 기반 페이징

#### PR-005: 프론트엔드 FlatList 최적화 미적용
- **파일**: 탭 화면 전반
- **근거**: `getItemLayout`, `windowSize`, `maxToRenderPerBatch` 미설정
- **권장 조치**: FlatList 최적화 props 적용 (아이템 높이 고정 시 `getItemLayout` 활용)

#### PR-006: 헬스체크 엔드포인트 부재
- **파일**: `main.py`
- **권장 조치**: `/health` 엔드포인트 추가 (DB ping, 기본 상태)

#### PR-007: 오프라인 큐(`offline-cache.ts`) 충돌 해소 전략 없음
- **파일**: `offline-cache.ts`, `http-client.ts`
- **근거**: pending mutations 재전송 시 서버 데이터와 충돌 가능 (예: 이미 삭제된 아이템 수정)
- **권장 조치**: 서버 4xx 응답 시 해당 mutation 폐기 + 사용자 알림

### 🟢 Info

#### PR-008: Dockerfile single-stage (최적화 여지)
- `python:3.12-slim` 양호. multi-stage로 추가 최적화 가능.

#### PR-009: `http-client.ts` 인메모리 캐시에 TTL만, max size 없음
- 클라이언트 수명이 짧으므로 리스크 낮음.

---

## Task List
| # | 파일 | 변경요지 | 테스트 커맨드 | 수용기준 | 위험도 |
|---|------|---------|-------------|---------|--------|
| 1 | `gemini_service.py` | 타임아웃 래핑 추가 | `pytest tests/test_services/test_gemini_service.py -v` | 30초 타임아웃 동작 | 🔴 |
| 2 | `recipe_cache.py` | max_devices 크기 제한 | `pytest tests/test_services/test_recipe_cache.py -v` | 100 디바이스 초과 시 LRU | 🔴 |
| 3 | `inventory_service.py` | bulk_upsert 쿼리 최적화 | `pytest tests/test_services/test_inventory_service.py -v` | IN 절 + 컬럼 지정 | 🟡 |
| 4 | `admin.py` | check-expiry 배치 처리 | `pytest tests/test_admin.py -v` | 페이징 적용 | 🟡 |
| 5 | 탭 화면 | FlatList 최적화 props | `npm test` | getItemLayout 적용 | 🟡 |
| 6 | `main.py` | /health 엔드포인트 | `pytest tests/test_main.py -v` | DB ping 응답 | 🟡 |
| 7 | `http-client.ts` | 오프라인 큐 충돌 해소 | `npm test` | 4xx 시 mutation 폐기 | 🟡 |

## Risk & Rollback
- PR-001: 타임아웃 추가는 안전. 너무 짧으면 정상 요청 실패 → 환경변수로 설정 가능하게.
- PR-002: LRU 퇴출 시 캐시 miss 증가 → Gemini 재호출. 사용자 영향 미미.
- PR-007: mutation 폐기는 데이터 손실 가능 → 사용자 알림 필수.
