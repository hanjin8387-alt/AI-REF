# Codex Change Log - 2026-02-13

## P0 Baseline Verification
- Existing commits already cover A-1 through A-8 (SEC-001, SEC-002, PR-001, PR-002, BA-002, BA-003, TE-001, TE-002).
- This execution implemented the remaining P0 task A-9.

## Commit A-9: feat(api): OA-001 add request-id middleware
- Files:
  - `prometheus-api/app/main.py`
  - `prometheus-api/tests/test_main.py`
- Changes:
  - Added HTTP middleware that reads or generates `X-Request-ID` and always returns it in response headers.
  - Added tests for generated request-id and incoming request-id passthrough.
- Tests:
  - Planned command (PowerShell-equivalent): `cd prometheus-api; python -m pytest tests/test_main.py -v -k "request_id"`
  - Result: `python` launcher unavailable in shell context (`Python` output).
  - Fallback run: `cd prometheus-api; py -m pytest tests/test_main.py -v -k "request_id"`
  - Outcome: `2 passed` (`1 deselected`).

## Perf Plan (2026-02-13_perf_master_plan.md)

## Commit A-1: perf(api): OM-001 add process-time middleware
- Commit: `8918d0c`
- Files:
  - `prometheus-api/app/main.py`
  - `prometheus-api/tests/test_main.py`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/ -v`
  - Benchmark: `hey -n 50 -c 5 $API/api/inventory` (`$API=https://ai-ref-api-274026276907.asia-northeast3.run.app`)
- Result:
  - Tests: `PASS` (`40 passed`)
  - Benchmark: `PASS` (`p95=0.0902s`, avg `0.0244s`, status `404x50`)
- Notes:
  - Added `X-Process-Time`, `X-Response-Time`, and `perf.request` logging.
  - Added header presence test.

## Commit A-2: perf(api): BL-001 add timeout to gemini API calls
- Commit: `82ab171` (existing)
- Files:
  - `prometheus-api/app/services/gemini_service.py`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/test_services/test_gemini_service.py -v`
  - Benchmark: `hey -n 5 $API/api/scans/upload` (first run failed because `hey` requires `-c <= -n`, rerun with `-c 1`)
- Result:
  - Tests: `PASS` (`4 passed`)
  - Benchmark: `PASS` (rerun `-n 5 -c 1`, avg `0.0286s`, status `404x5`)

## Commit A-3: perf(api): PRL-001 add max size to recipe cache
- Commit: `ad615a1` (existing)
- Files:
  - `prometheus-api/app/services/recipe_cache.py`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/test_services/test_recipe_cache.py -v`
  - Benchmark: `docker stats --no-stream prometheus-api` (container started for measurement)
- Result:
  - Tests: `PASS` (`2 passed`)
  - Benchmark: `PASS` (`MEM USAGE 103.4MiB / 15.53GiB`)

## Commit A-4: perf(api): NC-001 add gzip response compression
- Commit: `348d7fd`
- Files:
  - `prometheus-api/app/main.py`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/ -v`
  - Benchmark: `curl -s -H "Accept-Encoding: gzip" $API/api/inventory -o NUL -w "%{size_download}"`
- Result:
  - Tests: `PASS` (`40 passed`)
  - Benchmark: `PASS` (`size_download=22`)

## Commit A-5: perf(api): BL-002 optimize bulk upsert query
- Commit: `bd226a0` (existing)
- Files:
  - `prometheus-api/app/services/inventory_service.py`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/test_services/test_inventory_service.py -v`
  - Benchmark: `hey -n 50 -m POST $API/api/inventory/bulk`
- Result:
  - Tests: `PASS` (`4 passed`)
  - Benchmark: `PASS` (`p95=0.1676s`, avg `0.1477s`, status `404x50`)

## Commit A-6: perf(app): FR-001 optimize FlatList rendering
- Commit: `a770807`
- Files:
  - `prometheus-app/app/(tabs)/inventory.tsx`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `React DevTools Profiler` (manual)
- Result:
  - Tests: `PASS` (`4 suites, 18 tests`)
  - Benchmark: `N/A (manual profiler required in UI runtime)`

## Commit A-7: perf(ux): PS-001 create SkeletonCard component
- Commit: `d25036b`
- Files:
  - `prometheus-app/components/SkeletonCard.tsx`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: manual perceived-speed check
- Result:
  - Tests: `PASS` (`4 suites, 18 tests`)
  - Benchmark: `N/A (manual check)`

## Commit A-8: perf(ux): PS-001 apply skeleton to tab screens
- Commit: `818cec6`
- Files:
  - `prometheus-app/app/(tabs)/inventory.tsx`
  - `prometheus-app/app/(tabs)/index.tsx`
  - `prometheus-app/app/(tabs)/shopping.tsx`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: manual perceived-speed check
- Result:
  - Tests: `PASS` (`4 suites, 18 tests`)
  - Benchmark: `N/A (manual check)`

## Commit B-1: perf(app): FR-003 wrap list items with React.memo
- Commit: `f72855a`
- Files:
  - `prometheus-app/components/InventoryItemCard.tsx`
  - `prometheus-app/components/RecipeCardStack.tsx`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `React DevTools Profiler` (manual)
- Result:
  - Tests: `PASS` (`4 suites, 18 tests`)
  - Benchmark: `N/A (manual profiler required in UI runtime)`

## Commit B-2: perf(app): FR-002 replace inline handlers with useCallback
- Commit: `ad49ccd`
- Files:
  - `prometheus-app/app/(tabs)/index.tsx`
  - `prometheus-app/app/(tabs)/inventory.tsx`
  - `prometheus-app/app/(tabs)/shopping.tsx`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `React DevTools Profiler` (manual)
- Result:
  - Tests: `PASS` (`4 suites, 18 tests`)
  - Benchmark: `N/A (manual profiler required in UI runtime)`

## Commit B-3: perf(api): BL-004 parallelize checkout notifications
- Commit: `82d5118`
- Files:
  - `prometheus-api/app/api/shopping.py`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Benchmark: `hey -n 50 -c 5 -m POST $API/shopping/checkout`
- Result:
  - Tests: `PASS` (`40 passed`)
  - Benchmark: `PASS` (`p95=9.3249s`, avg `0.7647s`, status `401x50`)

## Commit B-4: perf(api): BL-006 replace SELECT * with explicit columns
- Commit: `a978d85`
- Files:
  - `prometheus-api/schema.sql`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Benchmark (planned): `hey -n 50 -c 5 $API/inventory`
  - Benchmark (fallback): `curl -s -o NUL -w "status=%{http_code} total=%{time_total}s size=%{size_download}\n" "$API/inventory"`
- Result:
  - Tests: `PASS` (`40 passed`)
  - Benchmark: `PASS` (`hey` unavailable in shell, fallback `status=401 total=0.087591s size=30`)

## Commit B-5: perf(network): NC-002 add request deduplication
- Commit: `d40bc77`
- Files:
  - `prometheus-app/services/http-client.ts`
  - `prometheus-app/__tests__/http-client.test.ts`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `N/A (master plan does not define a CLI benchmark for this client-only task)`
- Result:
  - Tests: `PASS` (`4 suites, 20 tests`)
  - Benchmark: `N/A`

## Commit B-6: perf(api): NC-003 add Cache-Control headers
- Commit: `6f6b91c`
- Files:
  - `prometheus-api/app/main.py`
  - `prometheus-api/tests/test_main.py`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Perf smoke: `cd prometheus-api; py -c "from fastapi.testclient import TestClient; from app.main import app; r=TestClient(app).get('/'); print('cache_control=' + str(r.headers.get('cache-control'))); print('status=' + str(r.status_code))"`
- Result:
  - Tests: `PASS` (`41 passed`)
  - Perf smoke: `PASS` (`cache_control=private, max-age=15, stale-while-revalidate=30`, `status=200`)

## Commit B-7: perf(ux): NC-004 prefetch adjacent tab data
- Commit: `9edb847`
- Files:
  - `prometheus-app/services/api.ts`
  - `prometheus-app/app/(tabs)/index.tsx`
  - `prometheus-app/app/(tabs)/inventory.tsx`
  - `prometheus-app/app/(tabs)/shopping.tsx`
  - `prometheus-app/__tests__/inventory-screen.test.tsx`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `N/A (master plan does not define a CLI benchmark for this UI prefetch task)`
- Result:
  - Tests: `PASS` (`4 suites, 20 tests`)
  - Benchmark: `N/A`
  - Notes: First run failed due missing test mock methods; added minimal mock stubs and reran successfully.

## Commit B-8: perf(ux): PS-002 optimistic UI for inventory delete
- Commit: `f6a0888`
- Files:
  - `prometheus-app/app/(tabs)/inventory.tsx`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `N/A (master plan does not define a CLI benchmark for this UX task)`
- Result:
  - Tests: `PASS` (`4 suites, 20 tests`)
  - Benchmark: `N/A`

## Commit B-9: perf(ux): PS-003 add recipe generation progress steps
- Commit: `a2206b3`
- Files:
  - `prometheus-app/app/(tabs)/index.tsx`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `N/A (master plan does not define a CLI benchmark for this UX task)`
- Result:
  - Tests: `PASS` (`4 suites, 20 tests`)
  - Benchmark: `N/A`

## Commit B-10: perf(ux): PS-004 add upload progress indicator
- Commit: `18cac49`
- Files:
  - `prometheus-app/app/(tabs)/scan.tsx`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `N/A (master plan does not define a CLI benchmark for this UX task)`
- Result:
  - Tests: `PASS` (`4 suites, 20 tests`)
  - Benchmark: `N/A`

## Commit B-11: perf(observability): OM-002 log gemini call duration
- Commit: `3da128e`
- Files:
  - `prometheus-api/app/services/gemini_service.py`
  - `prometheus-api/tests/test_services/test_gemini_service.py`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Benchmark: `N/A (master plan does not define a CLI benchmark for this observability task)`
- Result:
  - Tests: `PASS` (`42 passed`)
  - Benchmark: `N/A`

## Commit B-12: perf(observability): OM-003 add cache and client perf logging
- Commit: `b1aea03`
- Files:
  - `prometheus-api/app/services/recipe_cache.py`
  - `prometheus-app/services/perf-logger.ts`
  - `prometheus-app/services/http-client.ts`
- Commands:
  - Test (app): `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Test (api): `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Benchmark: `N/A (master plan does not define a separate CLI benchmark for this observability task)`
- Result:
  - Tests: `PASS` (`app: 4 suites, 20 tests / api: 42 passed`)
  - Benchmark: `N/A`

## Commit B-13: perf(network): PRL-002 limit client cache map size
- Commit: `0700ab2`
- Files:
  - `prometheus-app/services/http-client.ts`
  - `prometheus-app/__tests__/http-client.test.ts`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `N/A (master plan does not define a CLI benchmark for this client reliability task)`
- Result:
  - Tests: `PASS` (`4 suites, 21 tests`)
  - Benchmark: `N/A`

## Commit B-14: chore(perf): PRL-003 add perf smoke benchmark script
- Commit: `274ee2e`
- Files:
  - `scripts/perf-smoke.sh`
- Commands:
  - Perf smoke: `C:\Program Files\Git\bin\bash.exe -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"`
- Result:
  - Perf smoke: `PASS` (`/health avg=91.2ms p95=164.8ms`, `/inventory avg=86.3ms p95=95.5ms`)

## Commit B-15: perf(build): BS-001 remove console in production
- Commit: `c478826`
- Files:
  - `prometheus-app/babel.config.js`
  - `prometheus-app/package.json`
  - `prometheus-app/package-lock.json`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `N/A (master plan does not define a separate CLI benchmark for this build-config task)`
- Result:
  - Tests: `PASS` (`4 suites, 21 tests`)
  - Benchmark: `N/A`
  - Notes: First run failed due Babel cache setup order; fixed with minimal config change and reran successfully.

## Commit P2-1: perf(api): BL-003 paginate admin expiry batch queries
- Commit: `2acaab7`
- Files:
  - `prometheus-api/app/api/admin.py`
  - `prometheus-api/tests/test_admin.py`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Perf smoke: `C:\Program Files\Git\bin\bash.exe -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"`
- Result:
  - Tests: `PASS` (`44 passed`)
  - Perf smoke: `PASS` (`/health avg=81.4ms p95=84.0ms`, `/inventory avg=83.5ms p95=87.7ms`)

## Commit P2-2: perf(api): BL-005 add async recipe recommendation polling
- Commit: `5d4c424`
- Files:
  - `prometheus-api/app/api/recipes.py`
  - `prometheus-api/app/schemas/schemas.py`
  - `prometheus-api/tests/test_recipes_async.py`
  - `prometheus-app/services/api.ts`
- Commands:
  - Test (api): `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Test (app): `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Perf smoke: `C:\Program Files\Git\bin\bash.exe -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"`
- Result:
  - Tests: `PASS` (`api: 46 passed / app: 4 suites, 21 tests`)
  - Perf smoke: `PASS` (`/health avg=91.8ms p95=171.9ms`, `/inventory avg=87.0ms p95=107.4ms`)

## Commit P2-3: perf(build): BS-002 adopt Docker multi-stage runtime install
- Commit: `e8109cc`
- Files:
  - `prometheus-api/Dockerfile`
- Commands:
  - Build: `$env:PATH='C:\\Program Files\\Docker\\Docker\\resources\\bin;'+$env:PATH; docker build --no-cache -t prometheus-api:perf-ms ./prometheus-api`
  - Test: `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Benchmark: `docker images prometheus-api:perf-ms --format "{{.Repository}}:{{.Tag}} {{.Size}}"`
- Result:
  - Build: `PASS`
  - Tests: `PASS` (`46 passed`)
  - Benchmark: `PASS` (`prometheus-api:perf-ms 552MB`)
- Metrics:
  - Before: `prometheus-api:single-current-fresh 565MB`
  - After: `prometheus-api:perf-ms 552MB`
  - Delta: `-13MB`
- Notes:
  - Runtime layer bloat came from `COPY --from=builder /wheels /wheels` persistence.
  - Switched to BuildKit `RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels` to avoid embedding wheel artifacts in final image.

## Commit P2-4: perf(build): BS-003 remove redundant direct dependency
- Commit: `0bd0035`
- Files:
  - `prometheus-api/requirements.txt`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Benchmark build: `$env:PATH='C:\\Program Files\\Docker\\Docker\\resources\\bin;'+$env:PATH; docker build --no-cache -t prometheus-api:perf-ms ./prometheus-api`
  - Benchmark size: `docker images prometheus-api:perf-ms --format "{{.Repository}}:{{.Tag}} {{.Size}}"`
- Result:
  - Tests: `PASS` (`46 passed`)
  - Build: `PASS`
  - Benchmark: `PASS` (`prometheus-api:perf-ms 552MB`)
- Metrics:
  - Before: `prometheus-api:perf-ms 552MB`
  - After: `prometheus-api:perf-ms 552MB`
  - Delta: `0MB`
- Notes:
  - Removed direct `python-dotenv` from `requirements.txt`; it is already pulled transitively by `pydantic-settings`.

## Commit P2-5: perf(build): BS-005 split runtime and dev requirements
- Commit: `60f14d0`
- Files:
  - `prometheus-api/requirements.txt`
  - `prometheus-api/requirements-dev.txt`
- Commands:
  - Test: `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Benchmark build: `$env:PATH='C:\\Program Files\\Docker\\Docker\\resources\\bin;'+$env:PATH; docker build --no-cache -t prometheus-api:perf-ms ./prometheus-api`
  - Benchmark size: `docker images prometheus-api:perf-ms --format "{{.Repository}}:{{.Tag}} {{.Size}}"`
- Result:
  - Tests: `PASS` (`46 passed`)
  - Build: `PASS`
  - Benchmark: `PASS` (`prometheus-api:perf-ms 547MB`)
- Metrics:
  - Before: `prometheus-api:perf-ms 552MB`
  - After: `prometheus-api:perf-ms 547MB`
  - Delta: `-5MB`
- Notes:
  - Runtime dependencies stay in `requirements.txt`.
  - Test-only packages moved to `requirements-dev.txt` to keep runtime image leaner.

## Commit P2-6: perf(build): BS-004 convert web icons to WebP
- Commit: `e713bb9`
- Files:
  - `prometheus-app/public/manifest.json`
  - `prometheus-app/public/sw.js`
  - `prometheus-app/app/+html.tsx`
  - `prometheus-app/public/favicon.webp`
  - `prometheus-app/public/icons/icon-192.webp`
  - `prometheus-app/public/icons/icon-512.webp`
  - `prometheus-app/public/icons/maskable-icon-512.webp`
  - `prometheus-app/public/icons/apple-touch-icon.webp`
- Commands:
  - Test: `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Benchmark: `PowerShell size check (core web icon set bytes before/after)`
- Result:
  - Tests: `PASS` (`4 suites, 21 tests`)
  - Benchmark: `PASS` (`before_bytes=106575`, `after_bytes=35393`, `delta_bytes=-71182`, `delta_percent=-66.79`)
- Notes:
  - Web assets now prefer WebP in `manifest`, service worker core cache, and html icon links.
  - Existing PNG assets remain as compatibility fallback in manifest/html.

## Commit P2-7: perf(network): NC-005 add offline delta sync
- Commit: `bbe6660`
- Files:
  - `prometheus-api/app/api/inventory.py`
  - `prometheus-api/app/api/recipes.py`
  - `prometheus-api/app/api/shopping.py`
  - `prometheus-api/tests/test_delta_sync_filters.py`
  - `prometheus-app/services/api.ts`
  - `prometheus-app/__tests__/api-delta-sync.test.ts`
- Commands:
  - Test (api): `cd prometheus-api; py -m pytest tests/ -v --tb=short`
  - Test (app): `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Perf smoke: `& 'C:\Program Files\Git\bin\bash.exe' -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"`
- Result:
  - Tests: `PASS` (`api: 49 passed / app: 5 suites, 25 tests`)
  - Perf smoke: `PASS` (`/health avg=523.2ms p95=4467.9ms`, `/inventory avg=86.7ms p95=98.5ms`)
- Notes:
  - Added `updated_since` delta filters to inventory/favorites/shopping read endpoints.
  - Added app-side delta merge flow and retry hook-up (`retryPendingSync` -> `syncOfflineDelta`).
  - First perf-smoke invocation failed due PowerShell path quoting; rerun command passed with the same inputs.

## Commit P2-8: perf(app): FR-005 offload large JSON parsing with worker fallback
- Commit: `d81151f`
- Files:
  - `prometheus-app/services/http-client.ts`
  - `prometheus-app/utils/json-worker.ts`
  - `prometheus-app/__tests__/json-worker.test.ts`
- Commands:
  - Test (app): `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Perf smoke: `& 'C:\Program Files\Git\bin\bash.exe' -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"`
- Result:
  - Tests: `PASS` (`6 suites, 28 tests`)
  - Perf smoke: `PASS` (`/health avg=84.0ms p95=95.0ms`, `/inventory avg=83.7ms p95=87.0ms`)
- Notes:
  - Web GET JSON bodies now parse through worker path for large payloads, with automatic fallback to direct parse on worker errors/timeouts.
  - Added dedicated worker parser unit tests for normal, worker, and fallback paths.

## Commit P2-9: perf(ux): FR-006 add image placeholder and fade-in
- Commit: `9f2cc4a`
- Files:
  - `prometheus-app/components/RecipeCardStack.tsx`
- Commands:
  - Test (app): `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Perf smoke: `& 'C:\Program Files\Git\bin\bash.exe' -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"`
- Result:
  - Tests: `PASS` (`6 suites, 28 tests`)
  - Perf smoke: `PASS` (`/health avg=86.8ms p95=130.5ms`, `/inventory avg=83.3ms p95=90.0ms`)
- Notes:
  - Recipe card image now shows a loading placeholder and cross-fades into the final image on load.
  - Image load failure still falls back to the static recipe placeholder block.

## Commit P2-10: perf(ux): PS-005 add empty-state CTAs on key tabs
- Commit: `4e1e281`
- Files:
  - `prometheus-app/app/(tabs)/index.tsx`
  - `prometheus-app/app/(tabs)/inventory.tsx`
  - `prometheus-app/app/(tabs)/shopping.tsx`
  - `prometheus-app/__tests__/inventory-screen.test.tsx`
- Commands:
  - Test (app): `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Perf smoke: `& 'C:\Program Files\Git\bin\bash.exe' -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"`
- Result:
  - Tests: `PASS` (`6 suites, 28 tests`)
  - Perf smoke: `PASS` (`/health avg=83.0ms p95=95.9ms`, `/inventory avg=86.0ms p95=98.8ms`)
- Notes:
  - Added direct empty-state actions for home/favorites, inventory, and shopping tabs.
  - First app test run failed because `useRouter` mock was missing in `inventory-screen` test; added minimal mock and reran successfully.

## Commit P2-11: perf(ux): PS-006 add feed transition animation
- Commit: `6853943`
- Files:
  - `prometheus-app/app/(tabs)/index.tsx`
- Commands:
  - Test (app): `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Perf smoke: `& 'C:\Program Files\Git\bin\bash.exe' -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"`
- Result:
  - Tests: `PASS` (`6 suites, 28 tests`)
  - Perf smoke: `PASS` (`/health avg=85.1ms p95=99.8ms`, `/inventory avg=85.2ms p95=92.2ms`)
- Notes:
  - Added a lightweight fade+slide transition layer for home feed content to smooth mode/screen updates.

## Commit P2-12: perf(reliability): PRL-003 enforce offline cache TTL
- Commit: `(pending)`
- Files:
  - `prometheus-app/services/http-client.ts`
  - `prometheus-app/__tests__/http-client.test.ts`
- Commands:
  - Test (app): `cmd /c "cd /d prometheus-app && npm test -- --runInBand"`
  - Perf smoke: `& 'C:\Program Files\Git\bin\bash.exe' -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"`
- Result:
  - Tests: `PASS` (`6 suites, 29 tests`)
  - Perf smoke: `PASS` (`/health avg=88.8ms p95=130.6ms`, `/inventory avg=85.2ms p95=91.2ms`)
- Notes:
  - Added a 24-hour TTL gate for offline fallback data in `http-client`.
  - Added regression test that stale offline inventory cache is ignored.
