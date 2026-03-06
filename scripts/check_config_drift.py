#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def _extract_regex_value(path: Path, pattern: str, group: int = 1) -> str | None:
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        return None
    return match.group(group).strip()


def run_checks() -> list[Check]:
    config_path = REPO_ROOT / "prometheus-api" / "app" / "core" / "config.py"
    env_path = REPO_ROOT / "prometheus-api" / ".env.example"
    readme_path = REPO_ROOT / "README.md"
    app_config_path = REPO_ROOT / "prometheus-app" / "app.config.js"
    app_json_path = REPO_ROOT / "prometheus-app" / "app.json"
    runtime_config_path = REPO_ROOT / "prometheus-app" / "services" / "config" / "runtime.ts"

    runtime_gemini = _extract_regex_value(config_path, r'gemini_model:\s*str\s*=\s*"([^"]+)"')
    env_gemini = _extract_regex_value(env_path, r"^GEMINI_MODEL=(.+)$")
    readme = readme_path.read_text(encoding="utf-8")
    app_config = app_config_path.read_text(encoding="utf-8")
    app_json = app_json_path.read_text(encoding="utf-8")
    runtime_config = runtime_config_path.read_text(encoding="utf-8")

    runtime_legacy = _extract_regex_value(config_path, r"allow_legacy_app_token:\s*bool\s*=\s*(True|False)")
    env_legacy = _extract_regex_value(env_path, r"^ALLOW_LEGACY_APP_TOKEN=(.+)$")

    checks: list[Check] = []
    checks.append(
        Check(
            name="gemini_model_runtime_env_match",
            passed=bool(runtime_gemini and env_gemini and runtime_gemini == env_gemini),
            detail=f"runtime={runtime_gemini!r}, env_example={env_gemini!r}",
        )
    )
    checks.append(
        Check(
            name="readme_declares_gemini_default",
            passed=bool(env_gemini and "GEMINI_MODEL" in readme and env_gemini in readme),
            detail=f"readme_mentions_gemini={'GEMINI_MODEL' in readme}, expected_default={env_gemini!r}",
        )
    )
    checks.append(
        Check(
            name="legacy_compat_default_disabled_runtime_env",
            passed=bool(runtime_legacy and env_legacy and runtime_legacy.lower() == "false" and env_legacy.lower() == "false"),
            detail=f"runtime={runtime_legacy!r}, env_example={env_legacy!r}",
        )
    )
    checks.append(
        Check(
            name="readme_declares_legacy_opt_in",
            passed="ALLOW_LEGACY_APP_TOKEN=false" in readme,
            detail="README must include the explicit legacy compatibility opt-in switch",
        )
    )
    checks.append(
        Check(
            name="expo_extra_does_not_embed_legacy_token",
            passed="legacyAppToken" not in app_config and "legacyAppToken" not in app_json,
            detail="Expo config must not embed legacy app token into public extra config",
        )
    )
    checks.append(
        Check(
            name="runtime_config_does_not_read_legacy_token_from_expo_extra",
            passed="extra.legacyAppToken" not in runtime_config,
            detail="Runtime config must read deprecated legacy token from env opt-in only",
        )
    )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate config/documentation drift guards.")
    parser.add_argument("--output", required=True, help="Path to JSON output report")
    args = parser.parse_args()

    checks = run_checks()
    payload = {
        "checks": [check.__dict__ for check in checks],
        "status": "passed" if all(c.passed for c in checks) else "failed",
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for check in checks:
        print(f"[{'PASS' if check.passed else 'FAIL'}] {check.name}: {check.detail}")

    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
