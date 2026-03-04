# Final Hardening Report

## Scope and outcome

This hardening pass focused on public/verifiable CI, config/docs drift elimination, legacy auth migration hardening, and deterministic validation evidence.

## What changed

### 1) Public CI + evidence

- Added GitHub Actions workflow: `.github/workflows/ci.yml`
  - `Backend Test`
  - `Frontend Typecheck + Test`
  - `Docs Drift + Validation Summary`
- CI standard path does not require OpenAI secrets.
- CI uploads machine-readable artifacts:
  - `backend-test-results` (`junit.xml`, backend logs)
  - `frontend-test-results` (`junit.xml`, frontend logs)
  - `docs-validation-results` (`validation-summary.json`, drift/readme/smoke reports)
- Added local CI-mirroring entrypoint:
  - `scripts/validate-all.sh`
  - Backed by `scripts/validate_all.py` with step-level logs and `validation-summary.json`.

### 2) Config/docs drift removal

- Canonicalized `GEMINI_MODEL` default to `gemini-2.5-flash` in:
  - `prometheus-api/app/core/config.py`
  - `prometheus-api/.env.example`
  - `README.md`
- Added drift guards:
  - `scripts/check_config_drift.py`
  - `scripts/validate_readme_commands.py`
  - Backend drift tests in `prometheus-api/tests/test_config_doc_drift.py`
- Updated README command blocks to reference real files/scripts and explicit working directories.

### 3) Legacy auth hardening (secure-by-default)

- Switched backend default to explicit opt-in compatibility:
  - `ALLOW_LEGACY_APP_TOKEN=false` by default.
- Kept `X-App-ID` as primary app identifier.
- Legacy `X-App-Token` path is explicit and observable:
  - Added `prometheus-api/app/core/legacy_auth_observability.py`
  - Structured warning logs + counters for legacy accepted/rejected outcomes.
  - Added admin metrics endpoint: `GET /admin/legacy-auth-metrics` (admin token required).
- Startup now fails if legacy compatibility is enabled but `APP_TOKEN` is missing.
- Added backend tests for migration behavior:
  - secure default rejects legacy-only requests
  - compatibility accepts legacy-only when explicitly enabled
  - compatibility rejects wrong/unconfigured legacy token
- Frontend now sends legacy token only when explicitly enabled:
  - `EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN=true` required.
  - Added frontend tests for this behavior.

### 4) Validation/test infrastructure added

- Backend test dependencies via `prometheus-api/requirements-dev.txt`.
- Added backend tests:
  - `prometheus-api/tests/test_auth_security.py`
  - `prometheus-api/tests/test_config_doc_drift.py`
- Added frontend tests:
  - `prometheus-app/tests/legacy-auth.test.ts`
  - `prometheus-app/tests/auth-headers.test.ts`
- Added frontend test/typecheck scripts in `prometheus-app/package.json`.

### 5) Repo guidance and hygiene

- Added `AGENTS.md` with canonical validation commands and migration guardrails.
- Added `artifacts/` to `.gitignore`.

## Why these changes were made

- CI visibility + artifact upload makes repo health publicly verifiable from GitHub Actions.
- Drift guards prevent recurrence of config/docs mismatches (including `GEMINI_MODEL`).
- Legacy auth compatibility is now explicit, temporary, and measurable for sunset tracking.
- Validation is deterministic, command-driven, and tied to real exit codes/logs.

## Independent review pass

- Ran an independent reviewer agent after implementation.
- No critical findings were reported.
- Medium findings were addressed:
  - test hermeticity improved (`conftest.py` chdir isolation from local `.env`)
  - CI docs job now runs canonical wrapper (`bash scripts/validate-all.sh ...`)
  - README command validator expanded to cover `python -m` and `uvicorn` checks
  - legacy usage counters exposed via admin endpoint for operational visibility

## Intentionally deferred

- Optional Codex GitHub automation workflow was intentionally omitted.
  - Reason: standard CI already provides correctness and artifact evidence without external AI secrets.
  - Keeping default CI minimal/portable avoids making OpenAI integration a hidden dependency.
- Live integration smoke against external services remains optional and gated.
  - Default CI keeps this step non-blocking to avoid flaky secret/service coupling.

## Remaining external dependencies

- Backend runtime still depends on external services/secrets for full app operation:
  - `SUPABASE_URL`, `SUPABASE_KEY`
  - `GEMINI_API_KEY`
- Optional live smoke requires:
  - `RUN_LIVE_SMOKE=true`
  - `SMOKE_API_URL`, `SMOKE_APP_ID`

## Optional Codex automation status

- Not added in this hardening pass.
- Standard CI remains fully functional and blocking without any OpenAI secret dependency.
