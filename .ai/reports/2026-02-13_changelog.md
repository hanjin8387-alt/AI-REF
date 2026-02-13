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
