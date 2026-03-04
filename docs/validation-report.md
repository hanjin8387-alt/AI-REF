# Validation Report

## Context

- Repository: `AI-REF`
- Validation timezone: `Asia/Seoul (UTC+09:00)`
- Primary full-run window:
  - start: `2026-03-04T22:48:46.110345+09:00`
  - end: `2026-03-04T22:49:21.168574+09:00`
- Source artifact: `artifacts/validation-summary.json`

## Commands actually run and outcomes

Top-level command:

1. `bash scripts/validate-all.sh`
   - exit code: `0`
   - outcome: `passed`

Sub-steps executed by the command (from `artifacts/validation-summary.json`):

1. `python -m pip install -r requirements.txt -r requirements-dev.txt` (cwd: `prometheus-api`)
   - step: `backend-install`
   - exit code: `0`
2. `python -m pytest -q tests --junitxml=.../artifacts/backend/junit.xml` (cwd: `prometheus-api`)
   - step: `backend-test`
   - exit code: `0`
   - result: `7 passed`
3. `npm.cmd ci` (cwd: `prometheus-app`)
   - step: `frontend-install`
   - exit code: `0`
4. `npm.cmd run typecheck` (cwd: `prometheus-app`)
   - step: `frontend-typecheck`
   - exit code: `0`
5. `npm.cmd run test:ci` (cwd: `prometheus-app`)
   - step: `frontend-test`
   - exit code: `0`
   - result: `2 files, 7 tests passed`
6. `python scripts/check_config_drift.py --output .../artifacts/docs/config-drift.json`
   - step: `docs-check-config-drift`
   - exit code: `0`
7. `python scripts/validate_readme_commands.py --output .../artifacts/docs/readme-command-check.json`
   - step: `docs-validate-readme-commands`
   - exit code: `0`
8. `python scripts/optional_integration_smoke.py --output .../artifacts/docs/optional-smoke.json`
   - step: `docs-optional-smoke`
   - exit code: `0`
   - status in report: `skipped`

## Machine-readable artifacts produced

- `artifacts/validation-summary.json`
- `artifacts/backend/junit.xml`
- `artifacts/frontend/junit.xml`
- `artifacts/docs/config-drift.json`
- `artifacts/docs/readme-command-check.json`
- `artifacts/docs/optional-smoke.json`

## Skipped checks and real reason

- Optional live integration smoke:
  - file: `artifacts/docs/optional-smoke.json`
  - status: `skipped`
  - reason: `RUN_LIVE_SMOKE is not enabled. Live smoke checks are optional and non-blocking by default.`

## CI artifact mapping (GitHub Actions)

Workflow: `.github/workflows/ci.yml`

- `backend-test-results`
  - includes backend JUnit + backend logs
- `frontend-test-results`
  - includes frontend JUnit + typecheck/test logs
- `docs-validation-results`
  - includes validation summary + drift/readme/smoke JSON logs

## Notes on non-green intermediate attempts

During hardening, intermediate validation runs were executed and failed fast for real issues (Windows bash/python resolution and README command-drift). Those issues were fixed, and validation was re-run to a full green result recorded above.
