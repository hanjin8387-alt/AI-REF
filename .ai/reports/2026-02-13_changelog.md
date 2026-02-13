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
