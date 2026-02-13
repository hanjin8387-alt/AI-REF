# 2026-02-13 Changelog

## A-6 — chore(test): TE-SETUP-001 initialize pytest infrastructure with mock fixtures
- Code changes:
  - Added backend pytest infrastructure files: `prometheus-api/pytest.ini`, `prometheus-api/.env.test`, `prometheus-api/tests/__init__.py`, `prometheus-api/tests/conftest.py`.
  - Added minimal collection smoke test: `prometheus-api/tests/test_smoke.py`.
  - Added test dependencies in `prometheus-api/requirements.txt` (`pytest`, `pytest-asyncio`).
- Test command:
  - `cd prometheus-api && python -m pytest --co -q` (environment fallback: `py -m pytest --co -q`)
- Test result:
  - `1 test collected`, exit code `0`.
  - First run failed with `no tests collected`; fixed by adding a minimal smoke test and reran successfully.

## A-7 — test(api): TE-001 add security module unit tests
- Code changes:
  - Added `prometheus-api/tests/test_security.py`.
  - Covered `require_app_token` (valid/invalid/missing), `get_device_id` (valid/short/long/whitelist), and `_require_admin_token` behavior.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_security.py -v` (environment fallback: `py -m pytest tests/test_security.py -v`)
- Test result:
  - `10 passed`, exit code `0`.

## A-1 — security(api): SEC-001 use timing-safe comparison for admin token
- Code changes:
  - Updated `prometheus-api/app/api/admin.py` to use `secrets.compare_digest` in `_require_admin_token`.
  - Added `prometheus-api/tests/test_admin.py` to verify timing-safe comparison call and admin token failure cases.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_admin.py -v` (environment fallback: `py -m pytest tests/test_admin.py -v`)
- Test result:
  - `3 passed`, exit code `0`.

## A-2 — security(infra): SEC-002 run container as non-root user
- Code changes:
  - Updated `prometheus-api/Dockerfile`:
    - Added non-root user creation (`appuser`) and ownership update for `/app`.
    - Added `USER appuser` before runtime instruction.
  - Added `prometheus-api/.dockerignore` with `.env`, `__pycache__/`, `.git`, `*.pyc`.
- Test command:
  - `docker build -t prometheus-api . && docker run --rm prometheus-api whoami`
  - Environment execution used absolute binary path: `C:\Program Files\Docker\Docker\resources\bin\docker.exe`.
- Test result:
  - First run failed due `docker-credential-desktop` not in PATH.
  - Minimal fix applied: Docker `resources\bin` appended to PATH for the session.
  - Rerun succeeded and container user output was `appuser`.

## A-3 — perf(api): PR-001 add explicit timeout to gemini API calls
- Code changes:
  - Updated `prometheus-api/app/services/gemini_service.py`:
    - Added module constant `GEMINI_TIMEOUT_SECONDS = 30`.
    - Wrapped `generate_content_async(...)` with `asyncio.wait_for(..., timeout=GEMINI_TIMEOUT_SECONDS)`.
  - Added `prometheus-api/tests/test_services/test_gemini_service.py` for timeout behavior.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_services/test_gemini_service.py -v` (environment fallback: `py -m pytest ...`)
- Test result:
  - `2 passed`, exit code `0`.
  - First run had one coroutine cleanup warning in timeout test; minimal test fix applied and rerun passed without that warning.

## A-4 — perf(api): PR-002 add max size limit to in-memory recipe cache
- Code changes:
  - Updated `prometheus-api/app/services/recipe_cache.py`:
    - Added `max_devices=100` constructor parameter (with minimum guard).
    - Added per-device update timestamp tracking.
    - Added max-size pruning in `_prune_locked()` to evict oldest devices when limit is exceeded.
    - Ensured timestamp cleanup on expiry/invalidate paths.
  - Added `prometheus-api/tests/test_services/test_recipe_cache.py` for size-limit and minimum-size behavior.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_services/test_recipe_cache.py -v` (environment fallback: `py -m pytest ...`)
- Test result:
  - `2 passed`, exit code `0`.

## A-5 — security(api): CR-002 stream-validate upload size before full read
- Code changes:
  - Updated `prometheus-api/app/api/scans.py`:
    - Replaced whole-file `await file.read()` flow with chunk-based reads.
    - Added running byte-size validation during stream read.
    - Kept early `413` rejection before full in-memory assembly when size exceeds limit.
  - Added `prometheus-api/tests/test_scans.py` with upload-size limit test.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_scans.py -v -k "test_upload_size"` (environment fallback: `py -m pytest ...`)
- Test result:
  - `1 passed`, exit code `0`.

## B-1 — refactor(api): CR-003 extract shared storage category utilities
- Code changes:
  - Added `prometheus-api/app/services/storage_utils.py`:
    - `normalize_storage_category()`
    - `guess_storage_from_name()`
    - `STORAGE_CATEGORIES`
  - Updated `prometheus-api/app/api/scans.py` to use shared utility functions.
  - Updated `prometheus-api/app/api/inventory.py` to use shared `normalize_storage_category()`.
  - Removed duplicated storage normalization/guessing logic from API modules.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_services/test_storage_utils.py -v` (environment fallback: `py -m pytest ...`)
- Test result:
  - `3 passed`, exit code `0`.

## B-2 — SEC-007 .dockerignore generation
- Status:
  - Skipped by plan rule because `.dockerignore` was already created and committed in `A-2`.

## B-3 — feat(api): PR-006 add /health endpoint with DB connectivity check
- Code changes:
  - Updated `prometheus-api/app/main.py`:
    - Added `GET /health` endpoint.
    - Added DB ping via `get_db` dependency (`devices` table lightweight query).
    - Returns `200` + `{status: ok, database: ok}` on success.
    - Returns `503` + degraded payload when DB ping fails.
  - Added `prometheus-api/tests/test_main.py` health endpoint test.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_main.py -v -k "health"` (environment fallback: `py -m pytest ...`)
- Test result:
  - `1 passed`, exit code `0`.

## B-4 — perf(api): PR-003 optimize bulk_upsert inventory query
- Code changes:
  - Updated `prometheus-api/app/services/inventory_service.py`:
    - Changed inventory reads from `.select("*")` to `.select("id,name,quantity,unit,expiry_date,category")`.
    - Added name-scoped `IN` filtering for existing-row lookup based on input item names.
    - Applied explicit column selection to refreshed rows as well.
  - Added `prometheus-api/tests/test_services/test_inventory_service.py`.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_services/test_inventory_service.py -v` (environment fallback: `py -m pytest ...`)
- Test result:
  - `2 passed`, exit code `0`.

## B-5 — fix(api): CR-007 promote gemini model fallback log to warning
- Status:
  - Already satisfied before this step: fallback log in `prometheus-api/app/services/gemini_service.py` is already `logger.warning(...)`.
- Verification test:
  - `cd prometheus-api && python -m pytest tests/test_services/test_gemini_service.py -v` (environment fallback: `py -m pytest ...`)
  - Result: `2 passed`, exit code `0`.
- Action:
  - No additional code change required.

## B-6 — chore(test): TE-SETUP-002 initialize jest infrastructure
- Code changes:
  - Added `prometheus-app/jest.config.js`.
  - Added `prometheus-app/__tests__/setup.ts`.
  - Updated `prometheus-app/package.json`:
    - Added `test` script.
    - Added dev dependencies: `jest`, `jest-expo`, `@testing-library/react-native`.
  - Updated `prometheus-app/package-lock.json` via `npm install`.
- Test command:
  - `cd prometheus-app && npm test -- --passWithNoTests` (execution used `npm.cmd` due PowerShell execution policy)
- Test result:
  - `No tests found, exiting with code 0`.

## B-7 — test(api): TE-002 add gemini service unit tests with mocked API
- Code changes:
  - Expanded `prometheus-api/tests/test_services/test_gemini_service.py`:
    - Added mocked response parsing test for valid JSON.
    - Added invalid JSON fallback test (`[]` result).
    - Kept timeout-related behavior tests.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_services/test_gemini_service.py -v` (environment fallback: `py -m pytest ...`)
- Test result:
  - `4 passed`, exit code `0`.

## B-8 — test(api): TE-003 add inventory service unit tests
- Code changes:
  - Expanded `prometheus-api/tests/test_services/test_inventory_service.py`:
    - Added empty-input guard test.
    - Added earliest-expiry merge behavior test for duplicate item names.
    - Kept query-shape and quantity-merge tests.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_services/test_inventory_service.py -v` (environment fallback: `py -m pytest ...`)
- Test result:
  - `4 passed`, exit code `0`.

## B-9 — test(api): TE-004 add scans endpoint integration tests
- Code changes:
  - Expanded `prometheus-api/tests/test_scans.py`:
    - Upload size limit (`413`) test.
    - Successful upload and result retrieval flow test.
    - Non-image upload rejection (`415`) test.
    - Gemini failure path with FAILED status update (`502`) test.
- Test command:
  - `cd prometheus-api && python -m pytest tests/test_scans.py -v` (environment fallback: `py -m pytest ...`)
- Test result:
  - `4 passed`, exit code `0`.

## B-10 ??fix(app): UX-001 add accessibility labels to interactive elements
- Code changes:
  - Updated app tab screens to add contextual `accessibilityLabel` on all touchable controls:
    - `prometheus-app/app/(tabs)/index.tsx`
    - `prometheus-app/app/(tabs)/scan.tsx`
    - `prometheus-app/app/(tabs)/inventory.tsx`
    - `prometheus-app/app/(tabs)/shopping.tsx`
    - `prometheus-app/app/(tabs)/history.tsx`
    - `prometheus-app/app/(tabs)/alerts.tsx`
  - Updated shared components for accessibility consistency:
    - `prometheus-app/components/RoundButton.tsx` (added `accessibilityLabel` prop and default behavior)
    - `prometheus-app/components/RecipeCardStack.tsx` (added accessibility metadata for top swipe card)
  - Verified via JSX AST scan that touchable elements in `prometheus-app/components` and `prometheus-app/app/(tabs)` have `accessibilityLabel`.
- Test command:
  - `cd prometheus-app && npm test` (execution used `npm.cmd test` in PowerShell)
- Test result:
  - `1 passed`, exit code `0`.

## B-11 ??fix(app): UX-005 unify delete confirmation dialogs
- Code changes:
  - Added shared delete-confirm utility: `prometheus-app/utils/confirmDelete.ts`.
    - Unified confirm title/message/buttons for native (`Alert.alert`) and web (`confirm`) paths.
  - Updated `prometheus-app/app/(tabs)/inventory.tsx` to use `confirmDeleteItem(...)` for item deletion confirmation.
  - Updated `prometheus-app/app/(tabs)/shopping.tsx` to use `confirmDeleteItem(...)` for item deletion confirmation.
- Test command:
  - `cd prometheus-app && npm test` (execution used `npm.cmd test` in PowerShell)
- Test result:
  - `1 passed`, exit code `0`.

## B-12 ??perf(api): CR-004 replace SELECT * with explicit column selection
- Code changes:
  - Added centralized select-column constants: `prometheus-api/app/core/db_columns.py`.
  - Replaced `select("*")` / `select("*", count=...)` with explicit columns in backend APIs:
    - `prometheus-api/app/api/recipes.py`
    - `prometheus-api/app/api/inventory.py`
    - `prometheus-api/app/api/scans.py`
    - `prometheus-api/app/api/notifications.py`
    - `prometheus-api/app/api/stats.py`
    - `prometheus-api/app/api/shopping.py`
    - `prometheus-api/app/api/auth.py`
  - Preserved count queries while narrowing selected fields to required columns.
- Test command:
  - `cd prometheus-api && python -m pytest -v` (environment fallback: `py -m pytest -v`)
- Test result:
  - First run failed due Python launcher invocation (`python -m pytest -v` not executable in this shell context).
  - Reran with fallback command `py -m pytest -v`.
  - `32 passed`, exit code `0`.

## B-13 ??refactor(api): CR-006 standardize error messages to English
- Code changes:
  - Standardized backend `HTTPException.detail` messages to English in API modules:
    - `prometheus-api/app/api/inventory.py`
    - `prometheus-api/app/api/auth.py`
    - `prometheus-api/app/api/recipes.py`
    - `prometheus-api/app/api/scans.py`
    - `prometheus-api/app/api/shopping.py`
  - Updated front-end server-error localization mapping to support new English backend details:
    - `prometheus-app/services/http-client.ts` (`localizeServerError` direct mappings expanded)
  - Fixed corrupted string literals in `prometheus-api/app/api/shopping.py` while standardizing messages (compile-safe string normalization).
  - Updated scan size-limit test assertion for English detail message:
    - `prometheus-api/tests/test_scans.py`
- Test command:
  - `cd prometheus-api && python -m pytest -v` (environment fallback: `py -m pytest -v`)
- Test result:
  - First fallback run failed: `tests/test_scans.py::test_upload_size_limit_exceeded_returns_413` expected old Korean message.
  - Minimal fix applied: updated assertion to English detail.
  - Rerun passed: `32 passed`, exit code `0`.

## B-14 ??perf(app): PR-005 optimize FlatList rendering performance
- Code changes:
  - Updated `prometheus-app/app/(tabs)/history.tsx`:
    - Added `getItemLayout` estimate for history cards.
    - Added virtualization props: `initialNumToRender`, `maxToRenderPerBatch`, `windowSize`, `updateCellsBatchingPeriod`, `removeClippedSubviews`.
  - Updated `prometheus-app/app/(tabs)/inventory.tsx`:
    - Added list virtualization props for `SectionList`: `initialNumToRender`, `maxToRenderPerBatch`, `windowSize`, `updateCellsBatchingPeriod`, `removeClippedSubviews`.
- Test command:
  - `cd prometheus-app && npm test` (execution used `npm.cmd test` in PowerShell)
- Test result:
  - `1 passed`, exit code `0`.
