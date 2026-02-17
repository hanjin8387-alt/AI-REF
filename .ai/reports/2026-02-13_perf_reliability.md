# Performance & Reliability Report – 2026-02-13

## Summary
- **발견 항목**: 🔴 5 / 🟡 7 / 🟢 3

---

## Findings

### 🔴 Critical

#### PR-001: Gemini API 호출에 타임아웃·동시 호출 제한 없음
- **영역**: API 성능 / 에러 복구
- **파일**: `prometheus-api/app/services/gemini_service.py`
- **현재 상태**: `generate_content_async` 호출에 timeout 파라미터 없음. 동시 호출 수 제한(semaphore) 없음. `_generate_with_model_fallback` 메서드에서 모든 모델 후보를 순회하며 무한정 대기 가능.
- **영향**: Gemini 응답 지연 시 워커 스레드가 무한 점유 → 동시 업로드 10건이면 서버 hang 가능. Cloud Run 인스턴스 비용 증가.
- **권장 조치**:
  1. `asyncio.wait_for()`로 개별 호출에 30s 타임아웃 래핑
  2. `asyncio.Semaphore(3)` 으로 동시 Gemini 호출 상한 설정
  3. Settings에 `gemini_timeout_seconds`, `gemini_max_concurrent` 환경변수 추가
- **예상 개선**: p99 응답 시간 최대 30s 보장, 동시 요청 폭주 방지
- **작업량**: M

---

#### PR-002: 인메모리 RecipeCache 크기 제한 없음 (메모리 누출)
- **영역**: 캐시 효율
- **파일**: `prometheus-api/app/services/recipe_cache.py`
- **현재 상태**: `RecipeCache._recipe_store` / `_batch_store` dict에 엔트리 수 상한 없음. `_prune_locked()`는 만료된 항목만 정리하고, TTL 이전 적재량은 무제한 증가. 다수 device가 캐시를 쌓으면 프로세스 메모리 무한 증가.
- **영향**: Cloud Run 인스턴스 OOM Kill 또는 성능 저하. 장기 운영 시 메모리 누출.
- **권장 조치**:
  1. `MAX_CACHE_ENTRIES = 500` 상수 도입
  2. `_prune_locked()` 에서 최대 엔트리 초과 시 가장 오래된(LRU) 항목부터 제거
  3. Settings에 `recipe_cache_max_entries` 환경변수 추가
- **예상 개선**: 메모리 사용량 상한 ~50MB 이내 고정
- **작업량**: S

---

#### PR-003: 업로드 시 전체 이미지를 메모리로 읽기 + 동기 DB 쓰기 병목
- **영역**: API 성능
- **파일**: `prometheus-api/app/api/scans.py` (L287–L329)
- **현재 상태**: `await file.read()`로 최대 8MB를 한 번에 메모리 적재. 이후 Gemini 호출과 DB 업데이트가 **직렬(sequential)**로 실행됨. scan insert → Gemini 분석 → scan update → price_history insert가 총 4단계.
- **영향**: 8MB × 10 동시요청 = 80MB 메모리. Gemini 응답 대기(~3-5s) 동안 연결 점유. POST `/scans/upload` p95 추정 5s+.
- **권장 조치**:
  1. 스트리밍 읽기(`file.read(chunk_size)`) + 사이즈 체크를 chunk 단위로
  2. Gemini 호출 후 DB update와 price_history insert를 `asyncio.gather`로 병렬화
  3. 대형 이미지는 리사이즈 후 Gemini 전송 (1MB 이하로)
- **예상 개선**: p95 응답 시간 5s → 3s, 메모리 피크 50% 감소
- **작업량**: M

---

#### PR-004: stats/summary 엔드포인트 다중 전체 테이블 스캔
- **영역**: API 성능
- **파일**: `prometheus-api/app/api/stats.py` (L46–L172)
- **현재 상태**: `/stats/summary` 1회 호출 시 **4개 테이블**을 `select("*")`로 풀 스캔:
  - `cooking_history` (count + 전체 행 로드 → Python 루프 집계)
  - `inventory_logs` (전체 행 로드 → Python 카운트)
  - `inventory` (category만 필요하지만 `select("category")` 사용 — 이건 OK)
  - `shopping_items` (전체 행 로드)
- **영향**: 데이터 증가 시 O(N) Python 집계. 각 테이블 1000행이면 ~4000행 네트워크 전송 + JSON 파싱.
- **권장 조치**:
  1. `cooking_history`: `select("recipe_title", count="exact")` — 필요 컬럼만
  2. `inventory_logs`: `select("action, item_name", count="exact")` — `action` 기준 group/count는 DB RPC(집계 함수)로 이전
  3. `shopping_items`: `select("status", count="exact")` — status count만
  4. 가능하면 DB function(`get_stats_summary`)으로 집계를 한 번에 처리
- **예상 개선**: 네트워크 전송량 90% 감소, 응답 시간 50% 단축
- **작업량**: L

---

#### PR-005: 프론트엔드 http-client 재시도(retry) 미구현
- **영역**: 에러 복구
- **파일**: `prometheus-app/services/http-client.ts` (L176–L272)
- **현재 상태**: `request()` 메서드에 재시도 로직 없음. 네트워크 일시 장애 시 즉시 실패 → 오프라인 큐 enqueue 또는 에러 반환. mutation 재시도는 `retryPendingMutations`에서 수동으로만 가능.
- **영향**: 일시적 네트워크 끊김에서도 사용자에게 에러 표시. 재시도로 복구 가능한 요청까지 실패 처리.
- **권장 조치**:
  1. GET 요청: 지수 백오프(1s, 2s, 4s) 최대 3회 재시도
  2. POST/PUT/DELETE: 1회 즉시 재시도 후 실패 시 오프라인 큐
  3. 429 (rate-limit) 응답 시 `Retry-After` 헤더 존중
- **예상 개선**: 일시 장애 시 자동 복구율 80%+
- **작업량**: M

---

### 🟡 Warning

#### PR-006: `SELECT *` 광범위 사용
- **영역**: API 성능
- **파일**: `prometheus-api/app/api/scans.py` (L371), `recipes.py` (L131, L329), `stats.py` (L59, L95, L152), `inventory_service.py` (L68–L74)
- **현재 상태**: 7곳에서 `select("*")`로 불필요한 컬럼(JSONB 포함)까지 전송.
- **영향**: 네트워크 대역폭 낭비, Supabase → API 응답 지연.
- **권장 조치**: 각 쿼리에서 실제 사용 컬럼만 명시. 예: `recipes.py:131` → `select("name, quantity, unit, expiry_date, category")`.
- **예상 개선**: 쿼리 응답 크기 30–60% 감소
- **작업량**: S

---

#### PR-007: `bulk_upsert_inventory` 전체 인벤토리 풀로드
- **영역**: API 성능
- **파일**: `prometheus-api/app/services/inventory_service.py` (L68–L74)
- **현재 상태**: upsert 전 `select("*").eq("device_id", device_id)` 로 해당 디바이스의 **전체** 인벤토리 로드 후 Python dict에서 매칭. 인벤토리 200개 이상이면 비효율.
- **영향**: 항목이 많을수록 응답 지연 증가. O(N) 비교.
- **권장 조치**:
  1. `in_("name", [aggregated.keys()])` 필터로 관련 항목만 조회
  2. 또는 DB upsert의 `on_conflict` 절만으로 처리 (이미 L126 에서 사용 중이므로 기존 조회 불필요 여부 재검토)
- **예상 개선**: upsert 전 쿼리 데이터량 70% 감소
- **작업량**: S

---

#### PR-008: 오프라인 캐시(AsyncStorage) 용량 제한·정리 전략 없음
- **영역**: 캐시 효율
- **파일**: `prometheus-app/services/offline-cache.ts`
- **현재 상태**: `saveInventory`, `saveFavorites`, `saveShopping`이 데이터 크기 제한 없이 저장. `PENDING_MUTATIONS` 큐도 무한 증가 가능. AsyncStorage 기본 한도(Android ~6MB, iOS ~무제한) 초과 시 silent fail.
- **영향**: 앱 데이터 비대화, 저사양 기기 성능 저하.
- **권장 조치**:
  1. 각 캐시 키별 최대 크기(인벤토리 500항목, 즐겨찾기 100개 등)
  2. `PENDING_MUTATIONS` 큐 최대 50항목 + 7일 이상 된 항목 자동 정리
  3. `saveInventory` 등에서 truncation 로직 추가
- **예상 개선**: 앱 데이터 상한 ~2MB로 관리
- **작업량**: S

---

#### PR-009: DB 커넥션 장애 복구·재연결 로직 없음
- **영역**: 에러 복구
- **파일**: `prometheus-api/app/core/database.py`
- **현재 상태**: `@lru_cache()`로 Supabase 클라이언트를 영구 캐싱. 한 번 생성된 클라이언트 실패 시 재생성 불가. `finally: pass` 블록에 cleanup 없음.
- **영향**: Supabase 일시 중단 후 복구되어도 연결이 stale 상태로 남아 오류 지속 가능.
- **권장 조치**:
  1. health check 요청 시 클라이언트 ping 검증
  2. 연결 실패 시 `get_supabase_client.cache_clear()` 호출 후 재생성
  3. Retry decorator 적용 (최대 3회)
- **예상 개선**: Supabase 일시 장애 후 자동 복구
- **작업량**: S

---

#### PR-010: `get_recommendations` 엔드포인트 Gemini 실패 시 빈 배열 반환 (graceful degradation 미흡)
- **영역**: 에러 복구
- **파일**: `prometheus-api/app/api/recipes.py` (L156–L160)
- **현재 상태**: Gemini 호출 실패 시 `recipes_data = []` → 사용자에게 빈 추천 목록 표시. 오류 사실을 응답에 포함하지 않음.
- **영향**: 사용자가 오류인지 진짜 추천 없음인지 구분 불가.
- **권장 조치**:
  1. 응답에 `generation_failed: bool` 플래그 추가
  2. 만료된 캐시라도 stale 데이터를 fallback으로 반환 (stale-while-revalidate 패턴)
  3. 에러 메시지를 RecipeListResponse에 포함
- **예상 개선**: UX 개선, 장애 시 사용자 인지 가능
- **작업량**: S

---

#### PR-011: Dockerfile 미최적화 (멀티스테이지 빌드 미사용)
- **영역**: 인프라
- **파일**: `prometheus-api/Dockerfile`
- **현재 상태**: 단일 스테이지, `python:3.12-slim` 기반. pip 캐시 비활용. 빌드 레이어 캐싱 불리한 순서(requirements → code copy는 OK). 하지만 non-root 유저 미설정, 보안 리스크.
- **영향**: 이미지 크기 ~400MB+, 보안(root 실행).
- **권장 조치**:
  1. 멀티스테이지: builder → runtime
  2. `--no-install-recommends` + 불필요 패키지 제거
  3. `USER appuser` 추가 (non-root)
  4. `HEALTHCHECK` instruction 추가
- **예상 개선**: 이미지 크기 30–50% 감소, 보안 강화
- **작업량**: S

---

#### PR-012: `cooking_history` 테이블 인덱스 부족
- **영역**: 인프라
- **파일**: `prometheus-api/schema.sql`
- **현재 상태**: `idx_cooking_history_device`만 존재. `stats.py`에서 `gte("cooked_at", ...)` 필터 사용하지만 `(device_id, cooked_at DESC)` 복합 인덱스 없음.
- **영향**: 기간 필터 stats 조회 시 full table scan.
- **권장 조치**: `CREATE INDEX idx_cooking_history_device_cooked ON cooking_history(device_id, cooked_at DESC);`
- **예상 개선**: stats 쿼리 50%+ 빨라짐
- **작업량**: S

---

### 🟢 Info

#### PR-013: SectionList에 `getItemLayout` 미적용
- **영역**: 프론트 성능
- **파일**: `prometheus-app/app/(tabs)/inventory.tsx` (L409–L434)
- **현재 상태**: SectionList에 `getItemLayout` 미설정. 각 아이템 높이가 고정(`InventoryItemCard` 는 대략 84px)이므로 적용 가능.
- **영향**: 대량 리스트 스크롤 시 layout 계산 약간의 지터(jitter).
- **권장 조치**: `getItemLayout` prop 추가 (itemHeight=84+12(marginBottom))
- **예상 개선**: 스크롤 프레임 드롭 감소
- **작업량**: S

---

#### PR-014: RecipeCardStack `panResponder` 매 렌더마다 재생성
- **영역**: 프론트 성능
- **파일**: `prometheus-app/components/RecipeCardStack.tsx` (L62–L83)
- **현재 상태**: `PanResponder.create()`가 컴포넌트 본문에서 매 렌더마다 호출. `useRef` 또는 `useMemo`로 메모이즈되지 않음.
- **영향**: 렌더마다 PanResponder 재생성 → 미미한 CPU 낭비, 잠재적 제스처 플리커.
- **권장 조치**: `useRef` + `useMemo` 로 PanResponder 고정
- **예상 개선**: 불필요 객체 생성 제거
- **작업량**: S

---

#### PR-015: 헬스체크 엔드포인트 없음 (전용)
- **영역**: 모니터링
- **파일**: `prometheus-api/app/main.py` (L98–L106)
- **현재 상태**: `GET /` 가 status "running" 반환하지만 DB 연결/Gemini API 상태 미확인. Cloud Run liveness/readiness probe에 부적합.
- **영향**: DB 장애 시에도 인스턴스가 "healthy"로 유지 → 트래픽 수신 지속.
- **권장 조치**:
  1. `GET /health` 엔드포인트: DB ping + 기본 connectivity 확인
  2. `GET /ready`: 의존 서비스(Supabase) reachable 확인
  3. Cloud Run YAML에 `livenessProbe`, `readinessProbe` 설정
- **예상 개선**: 자동 장애 감지 및 인스턴스 교체
- **작업량**: S

---

## Performance Baseline

| 엔드포인트 | 추정 p95 | 목표 | 상태 |
|-----------|---------|------|------|
| POST /scans/upload | ~5s | ≤3s | 🟡 |
| GET /recipes/recommendations | ~4s (cache miss) | ≤3s | 🟡 |
| GET /stats/summary | ~1.5s (1K rows/table) | ≤0.5s | 🔴 |
| POST /inventory/add-from-scan | ~0.8s | ≤0.5s | 🟡 |
| GET /inventory | ~0.3s | ≤0.2s | 🟢 |
| GET /recipes/favorites | ~0.2s | ≤0.2s | 🟢 |

---

## Action Items

| # | 제목 | 위험도 | 작업량 | 영향 |
|---|------|--------|--------|------|
| PR-001 | Gemini 타임아웃 + 동시호출 제한 | 🔴 | M | 서버 hang 방지 |
| PR-002 | RecipeCache 메모리 상한 | 🔴 | S | OOM 방지 |
| PR-003 | 스캔 업로드 최적화 | 🔴 | M | 응답 속도 40% ↑ |
| PR-004 | stats 쿼리 최적화 | 🔴 | L | 응답 속도 50% ↑ |
| PR-005 | HTTP Client 자동 재시도 | 🔴 | M | 장애 복구 80% ↑ |
| PR-006 | SELECT * → 필요 컬럼만 | 🟡 | S | 대역폭 30–60% ↓ |
| PR-007 | bulk_upsert 쿼리 최적화 | 🟡 | S | upsert 지연 70% ↓ |
| PR-008 | 오프라인 캐시 용량 제한 | 🟡 | S | 앱 데이터 관리 |
| PR-009 | DB 재연결 로직 | 🟡 | S | 장애 자동 복구 |
| PR-010 | 추천 실패 graceful degradation | 🟡 | S | UX 개선 |
| PR-011 | Dockerfile 최적화 | 🟡 | S | 이미지 30% ↓ |
| PR-012 | cooking_history 인덱스 추가 | 🟡 | S | 쿼리 50% ↑ |
| PR-013 | SectionList getItemLayout | 🟢 | S | 스크롤 개선 |
| PR-014 | PanResponder 메모이즈 | 🟢 | S | 렌더 효율 |
| PR-015 | 헬스체크 엔드포인트 | 🟢 | S | 모니터링 강화 |

---

## Codex Task List

아래 각 항목은 1커밋 단위로 실행 가능합니다. 우선순위: 🔴 → 🟡 → 🟢

---

### Task 1 (PR-001): Gemini 타임아웃 + 동시호출 제한

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/app/services/gemini_service.py` |
| **함수** | `_generate_with_model_fallback()` |
| **수정 요지** | 1) 클래스 `__init__`에 `self._semaphore = asyncio.Semaphore(settings.gemini_max_concurrent)` 추가 (기본값 3). 2) `_generate_with_model_fallback` 내부에서 `async with self._semaphore:` 래핑. 3) `generate_content_async` 호출을 `asyncio.wait_for(..., timeout=settings.gemini_timeout_seconds)` 로 감싸기 (기본 30s). 4) `asyncio.TimeoutError` catch → 로깅 후 `HTTPException(504)` |
| **파일** | `prometheus-api/app/core/config.py` |
| **함수** | `Settings` |
| **수정 요지** | `gemini_timeout_seconds: int = 30`, `gemini_max_concurrent: int = 3` 필드 추가 |
| **커밋** | `perf(api): PR-001 add timeout and concurrency limit to gemini calls` |
| **테스트** | `cd prometheus-api && python -c "from app.services.gemini_service import GeminiService; print('import ok')"` |

---

### Task 2 (PR-002): RecipeCache 메모리 상한

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/app/services/recipe_cache.py` |
| **함수** | `RecipeCache.__init__()`, `RecipeCache._prune_locked()` |
| **수정 요지** | 1) `MAX_ENTRIES = 500` 상수 추가. 2) `_prune_locked()` 에서 `sum(len(b) for b in self._recipe_store.values()) > MAX_ENTRIES` 시, 가장 오래된 만료시간의 엔트리부터 삭제. 3) Settings에 `recipe_cache_max_entries: int = 500` 추가 |
| **파일** | `prometheus-api/app/core/config.py` |
| **함수** | `Settings` |
| **수정 요지** | `recipe_cache_max_entries: int = 500` 필드 추가 |
| **커밋** | `perf(cache): PR-002 add max entry limit to in-memory recipe cache` |
| **테스트** | `cd prometheus-api && python -c "from app.services.recipe_cache import RecipeCache; c = RecipeCache(); print('cache ok')"` |

---

### Task 3 (PR-003): 스캔 업로드 최적화

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/app/api/scans.py` |
| **함수** | `upload_scan()` |
| **수정 요지** | 1) L287 `await file.read()` → chunk 단위 읽기(64KB)로 변경, 사이즈 초과 시 즉시 중단. 2) L323–L340: scan update와 price_history insert를 `asyncio.gather`로 병렬 실행. 3) 대형 이미지(>1MB) 시 Pillow로 리사이즈 후 Gemini 전송 (requirements.txt에 Pillow 추가 검토) |
| **커밋** | `perf(api): PR-003 optimize scan upload with streaming read and parallel db writes` |
| **테스트** | `cd prometheus-api && python -c "from app.api.scans import upload_scan; print('import ok')"` |

---

### Task 4 (PR-004): stats 쿼리 최적화

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/app/api/stats.py` |
| **함수** | `get_stats_summary()` |
| **수정 요지** | 1) L57–L64: `select("*")` → `select("recipe_title", count="exact")`. 2) L93–L99: `select("*")` → `select("action, item_name")`. 3) L148–L155: `select("*")` → `select("status", count="exact")`. 4) (선택) Supabase DB function `get_stats_summary(p_device_id, p_period)` 생성하여 1회 RPC로 모든 집계 수행. |
| **파일** | `prometheus-api/schema.sql` |
| **함수** | (DDL) |
| **수정 요지** | `CREATE INDEX idx_cooking_history_device_cooked ON cooking_history(device_id, cooked_at DESC);` 추가 |
| **커밋** | `perf(api): PR-004 optimize stats queries with column selection and index` |
| **테스트** | `cd prometheus-api && python -c "from app.api.stats import get_stats_summary; print('import ok')"` |

---

### Task 5 (PR-005): HTTP Client 자동 재시도

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-app/services/http-client.ts` |
| **함수** | `HttpClient.request()` |
| **수정 요지** | 1) `request()` 메서드에 retry loop 추가: `maxRetries = 3` (GET), `maxRetries = 1` (mutation). 2) 지수 백오프: `delay = Math.min(1000 * 2^attempt, 8000)`. 3) retry 대상: network error, 5xx 응답, 429 (Retry-After 존중). 4) AbortError(timeout)는 retry하지 않음. |
| **커밋** | `feat(app): PR-005 add exponential backoff retry to http-client` |
| **테스트** | `cd prometheus-app && npx tsc --noEmit --pretty` |

---

### Task 6 (PR-006): SELECT * 제거

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/app/api/scans.py` L371 |
| **함수** | `get_scan_result()` |
| **수정 요지** | `select("*")` → `select("id, device_id, source_type, status, items, raw_text, error_message")` |
| **파일** | `prometheus-api/app/api/recipes.py` L131 |
| **함수** | `get_recommendations()` |
| **수정 요지** | `select("*")` → `select("name, quantity, unit, expiry_date, category")` |
| **파일** | `prometheus-api/app/api/recipes.py` L329 |
| **함수** | `complete_cooking()` |
| **수정 요지** | `select("*")` → `select("id, name, quantity, unit, expiry_date, category")` |
| **파일** | `prometheus-api/app/services/inventory_service.py` L68–L74 |
| **함수** | `bulk_upsert_inventory()` |
| **수정 요지** | `select("*")` → `select("id, name, quantity, unit, expiry_date, category")` |
| **커밋** | `perf(api): PR-006 replace SELECT * with explicit column selection` |
| **테스트** | `cd prometheus-api && python -c "from app.api.scans import router; from app.api.recipes import router; print('ok')"` |

---

### Task 7 (PR-007): bulk_upsert 쿼리 최적화

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/app/services/inventory_service.py` |
| **함수** | `bulk_upsert_inventory()` |
| **수정 요지** | L68–L74: `select("*").eq("device_id", device_id)` → `select("id, name, quantity, unit, expiry_date, category").eq("device_id", device_id).in_("name", list(aggregated.keys()))` — 관련 항목만 조회. |
| **커밋** | `perf(api): PR-007 filter bulk_upsert query to relevant items only` |
| **테스트** | `cd prometheus-api && python -c "from app.services.inventory_service import bulk_upsert_inventory; print('ok')"` |

---

### Task 8 (PR-008): 오프라인 캐시 용량 제한

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-app/services/offline-cache.ts` |
| **함수** | `OfflineCache.saveInventory()`, `saveFavorites()`, `saveShopping()`, `enqueueMutation()` |
| **수정 요지** | 1) 상수 `MAX_INVENTORY_ITEMS = 500`, `MAX_FAVORITES = 100`, `MAX_PENDING_MUTATIONS = 50`, `MUTATION_MAX_AGE_MS = 7 * 24 * 3600 * 1000` 추가. 2) 각 save 메서드에서 배열을 slice. 3) `enqueueMutation()` 에서 큐 사이즈 체크 + 오래된 항목 정리. |
| **커밋** | `perf(app): PR-008 add size limits and cleanup to offline cache` |
| **테스트** | `cd prometheus-app && npx tsc --noEmit --pretty` |

---

### Task 9 (PR-009): DB 재연결 로직

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/app/core/database.py` |
| **함수** | `get_supabase_client()`, `get_db()` |
| **수정 요지** | 1) `@lru_cache()` 대신 모듈 레벨 변수 `_client: Client | None = None`으로 관리. 2) `get_supabase_client()`에서 기존 client 상태 확인, 실패 시 재생성. 3) `get_db()`의 except 블록에서 `_client = None` 세팅하여 다음 요청 시 재생성 유도. |
| **커밋** | `fix(core): PR-009 add db client reconnection on failure` |
| **테스트** | `cd prometheus-api && python -c "from app.core.database import get_supabase_client; print('ok')"` |

---

### Task 10 (PR-010): 추천 실패 graceful degradation

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/app/api/recipes.py` |
| **함수** | `get_recommendations()` |
| **수정 요지** | 1) L156–L160: except 블록에서 `recipes_data = []` 뒤에 `generation_failed = True` 플래그. 2) 만료된 캐시(stale)를 fallback으로 반환 시도: `recipe_cache.get_batch(device_id, fingerprint, limit=limit, allow_stale=True)`. 3) `RecipeListResponse`에 `generation_failed: bool = False` 필드 추가. |
| **파일** | `prometheus-api/app/schemas/schemas.py` |
| **함수** | `RecipeListResponse` |
| **수정 요지** | `generation_failed: bool = False` 필드 추가 |
| **커밋** | `fix(api): PR-010 add graceful degradation for recipe generation failure` |
| **테스트** | `cd prometheus-api && python -c "from app.schemas.schemas import RecipeListResponse; print('ok')"` |

---

### Task 11 (PR-011): Dockerfile 최적화

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/Dockerfile` |
| **함수** | (전체) |
| **수정 요지** | 멀티스테이지: `FROM python:3.12-slim AS builder` → `FROM python:3.12-slim AS runtime`. non-root 유저 `appuser` 추가. `HEALTHCHECK CMD curl -f http://localhost:8080/health || exit 1` 추가. |
| **커밋** | `build(docker): PR-011 multi-stage build with non-root user and healthcheck` |
| **테스트** | `cd prometheus-api && docker build -t prometheus-api:test .` (로컬 Docker 환경 필요 시 생략 가능) |

---

### Task 12 (PR-012): cooking_history 인덱스 추가

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/schema.sql` |
| **함수** | (DDL) |
| **수정 요지** | 기존 인덱스 섹션(L160–L175 부근)에 추가: `CREATE INDEX IF NOT EXISTS idx_cooking_history_device_cooked ON cooking_history(device_id, cooked_at DESC);` |
| **커밋** | `perf(db): PR-012 add composite index on cooking_history(device_id, cooked_at)` |
| **테스트** | SQL 리뷰로 확인 (Supabase SQL Editor에서 실행) |

---

### Task 13 (PR-013): SectionList getItemLayout

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-app/app/(tabs)/inventory.tsx` |
| **함수** | `InventoryScreen()` 내 SectionList JSX |
| **수정 요지** | SectionList에 `getItemLayout` prop 추가: `getItemLayout={(_, index) => ({ length: 96, offset: 96 * index, index })}` (84px card + 12px margin) |
| **커밋** | `perf(app): PR-013 add getItemLayout to inventory SectionList` |
| **테스트** | `cd prometheus-app && npx tsc --noEmit --pretty` |

---

### Task 14 (PR-014): PanResponder 메모이즈

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-app/components/RecipeCardStack.tsx` |
| **함수** | `RecipeCardStack()` 내 `panResponder` |
| **수정 요지** | L62 `const panResponder = PanResponder.create(...)` → `const panResponder = useRef(PanResponder.create(...)).current;` 또는 `useMemo(() => PanResponder.create(...), [])` |
| **커밋** | `perf(app): PR-014 memoize PanResponder in RecipeCardStack` |
| **테스트** | `cd prometheus-app && npx tsc --noEmit --pretty` |

---

### Task 15 (PR-015): 헬스체크 엔드포인트 추가

| 항목 | 내용 |
|------|------|
| **파일** | `prometheus-api/app/main.py` |
| **함수** | 새 함수 `health()`, `ready()` |
| **수정 요지** | 1) `@app.get("/health")` — 단순 `{"status": "ok"}` 반환 (rate limit 없음). 2) `@app.get("/ready")` — Supabase `db.table("devices").select("id").limit(1)` ping 테스트 + 응답 시간 체크. 실패 시 503 반환. |
| **커밋** | `feat(api): PR-015 add /health and /ready endpoints` |
| **테스트** | `cd prometheus-api && python -c "from app.main import app; print([r.path for r in app.routes])"` |
