# Performance & Reliability Report – 2026-02-13

## Summary
- **발견 항목**: 🔴 Critical: 2 / 🟡 Warning: 4 / 🟢 Info: 2

---

## Findings

### 🔴 Critical

#### PR-001: Gemini API 호출에 명시적 타임아웃 없음
- **파일**: `prometheus-api/app/services/gemini_service.py`
- **현재 상태**: `google.generativeai` 기본 타임아웃(무한 or 매우 긴 시간)에 의존
- **영향**: Gemini 장애 시 요청이 무한 대기 → Cloud Run 인스턴스 고갈 → 전체 서비스 중단
- **권장 조치**: `asyncio.wait_for()` 또는 `GenerationConfig`의 timeout 옵션 적용 (이미지 분석 30초, 레시피 생성 45초)
- **작업량**: S

#### PR-002: 메모리 캐시(`RecipeCache`)에 최대 크기 제한 없음
- **파일**: `prometheus-api/app/services/recipe_cache.py`
- **현재 상태**: `_recipe_store` dict가 무제한 성장 가능. `_prune_locked()`는 TTL 만료 항목만 정리.
- **영향**: 다수 디바이스의 데이터가 누적되면 메모리 고갈
- **권장 조치**: 최대 디바이스 수(예: 100), 또는 LRU 제한(최대 1000 레시피) 적용
- **작업량**: S

### 🟡 Warning

#### PR-003: `inventory_service.bulk_upsert`가 전체 재고를 `SELECT *`로 조회
- **파일**: `prometheus-api/app/services/inventory_service.py` L89
- **현재 상태**: 디바이스의 모든 재고를 한 번에 조회 후 메모리에서 병합
- **영향**: 재고 수백 건 이상이면 불필요한 데이터 전송
- **권장 조치**: 입력 아이템 이름으로 IN 절 필터링
- **작업량**: S

#### PR-004: `/admin/check-expiry`가 모든 디바이스 재고를 한 번에 조회
- **파일**: `prometheus-api/app/api/admin.py` L52
- **현재 상태**: 전체 inventory에서 유통기한 임박 항목을 한 번에 SELECT
- **영향**: 디바이스/아이템 수 증가 시 쿼리 시간 증가
- **권장 조치**: 디바이스별 배치 처리 또는 커서 기반 페이징
- **작업량**: M

#### PR-005: 프론트엔드 FlatList 최적화 미적용
- **파일**: 탭 화면 전반
- **현재 상태**: `getItemLayout`, `windowSize`, `maxToRenderPerBatch` 미설정
- **영향**: 아이템 수 50+ 시 스크롤 프레임 드롭
- **권장 조치**: FlatList 최적화 props 적용
- **작업량**: S

#### PR-006: 헬스체크 엔드포인트 부재
- **파일**: `prometheus-api/app/main.py`
- **현재 상태**: `/` 엔드포인트가 정적 JSON만 반환. DB 연결 상태 미확인.
- **영향**: Cloud Run 프로브가 앱 상태를 정확히 판단 불가
- **권장 조치**: `/health` 엔드포인트 추가 (DB ping, Gemini API key 유효성 등)
- **작업량**: S

### 🟢 Info

#### PR-007: Dockerfile이 single-stage, 불필요한 빌드 도구 포함 가능
- `python:3.12-slim` 사용으로 양호하나, multi-stage로 최적화 가능
- **작업량**: S

#### PR-008: 오프라인 캐시(`offline-cache.ts`)에 용량 제한 없음
- AsyncStorage에 무한 저장. 극단적으로 큰 데이터 시 성능 저하 가능.
- **작업량**: S (문서화 수준)

---

## Performance Baseline (추정)
| 엔드포인트 | 추정 p95 | 목표 | 상태 |
|-----------|---------|------|------|
| POST /scans/upload | ~5-10s | ≤8s | 🟡 (Gemini 의존) |
| GET /recipes/recommendations | ~3-10s | ≤5s | 🟡 (캐시 miss 시 Gemini) |
| GET /inventory | ~200ms | ≤200ms | ✅ |
| POST /inventory/bulk | ~500ms | ≤500ms | ✅ |
| POST /admin/check-expiry | ~1-5s | ≤3s | 🟡 (디바이스 수 비례) |

## Action Items
| # | 제목 | 위험도 | 작업량 | 예상 영향 |
|---|------|--------|--------|----------|
| PR-001 | Gemini 타임아웃 추가 | 🔴 | S | 서비스 안정성 확보 |
| PR-002 | 캐시 크기 제한 | 🔴 | S | 메모리 고갈 방지 |
| PR-003 | bulk_upsert 쿼리 최적화 | 🟡 | S | 네트워크 -50% |
| PR-004 | check-expiry 배치 처리 | 🟡 | M | 스케일 대비 |
| PR-005 | FlatList 최적화 | 🟡 | S | 스크롤 FPS +20% |
| PR-006 | 헬스체크 엔드포인트 | 🟡 | S | 모니터링 강화 |
| PR-007 | Dockerfile 최적화 | 🟢 | S | 이미지 -20MB |
| PR-008 | 오프라인 캐시 문서화 | 🟢 | S | - |
