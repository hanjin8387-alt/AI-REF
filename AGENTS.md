# AGENTS.md

## Repository guardrails

- Treat tracked files in this checkout as the source of truth.
- Do not depend on `.codex` state for CI, tests, or runtime behavior.
- Keep standard CI independent of OpenAI-specific secrets.

## Canonical local validation

- Primary entrypoint: `bash scripts/validate-all.sh`
- Mode-specific runs:
  - `python scripts/validate_all.py --mode backend`
  - `python scripts/validate_all.py --mode frontend`
  - `python scripts/validate_all.py --mode docs --skip-install`
- Artifacts are generated under `artifacts/`.

## Drift guards

- `scripts/check_config_drift.py` enforces:
  - `GEMINI_MODEL` default parity across runtime + `.env.example` + README
  - secure-by-default legacy auth compatibility (`ALLOW_LEGACY_APP_TOKEN=false`)
- `scripts/validate_readme_commands.py` checks command/file drift in README shell blocks.

## Auth migration policy

- Primary public identifier: `X-App-ID`
- Legacy `X-App-Token` compatibility is explicit opt-in:
  - Backend: `ALLOW_LEGACY_APP_TOKEN=true` + `APP_TOKEN` required
  - Frontend: `EXPO_PUBLIC_ENABLE_LEGACY_APP_TOKEN=true` + `EXPO_PUBLIC_APP_TOKEN`
- Legacy usage must stay observable via structured warnings and counters.
