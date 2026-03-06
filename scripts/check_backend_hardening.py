#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "prometheus-api" / "app"


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


def _matching_files(pattern: str) -> list[str]:
    regex = re.compile(pattern)
    matches: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if regex.search(text):
            matches.append(str(path.relative_to(REPO_ROOT)))
    return matches


def run_checks() -> list[Check]:
    checks: list[Check] = []

    schemas_hub_imports = _matching_files(r"schemas\.schemas")
    checks.append(
        Check(
            name="no_internal_schemas_hub_imports",
            passed=not schemas_hub_imports,
            detail=", ".join(schemas_hub_imports) if schemas_hub_imports else "ok",
        )
    )

    legacy_idempotency_helpers = _matching_files(r"\b(load_idempotent_response|save_idempotent_response)\b")
    checks.append(
        Check(
            name="no_legacy_idempotency_helpers",
            passed=not legacy_idempotency_helpers,
            detail=", ".join(legacy_idempotency_helpers) if legacy_idempotency_helpers else "ok",
        )
    )

    legacy_memory_metrics = _matching_files(r"_MEMORY_COUNTERS")
    checks.append(
        Check(
            name="no_in_memory_legacy_metrics_source",
            passed=not legacy_memory_metrics,
            detail=", ".join(legacy_memory_metrics) if legacy_memory_metrics else "ok",
        )
    )

    strip_lower = _matching_files(r"strip\(\)\.lower\(\)")
    checks.append(
        Check(
            name="no_strip_lower_shortcuts_in_app",
            passed=not strip_lower,
            detail=", ".join(strip_lower) if strip_lower else "ok",
        )
    )

    expected_idempotent_files = [
        "prometheus-api/app/api/admin.py",
        "prometheus-api/app/api/backups.py",
        "prometheus-api/app/api/device_auth.py",
        "prometheus-api/app/api/inventory.py",
        "prometheus-api/app/api/notifications.py",
        "prometheus-api/app/api/recipes.py",
        "prometheus-api/app/api/scans.py",
        "prometheus-api/app/api/shopping_mutations.py",
    ]
    missing = []
    for rel_path in expected_idempotent_files:
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        if "execute_idempotent_mutation" not in text:
            missing.append(rel_path)
    checks.append(
        Check(
            name="major_mutation_routes_use_canonical_idempotency_helper",
            passed=not missing,
            detail=", ".join(missing) if missing else "ok",
        )
    )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate backend hardening boundaries.")
    parser.add_argument("--output", required=True, help="Path to JSON output report")
    args = parser.parse_args()

    checks = run_checks()
    payload = {
        "checks": [check.__dict__ for check in checks],
        "status": "passed" if all(check.passed for check in checks) else "failed",
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for check in checks:
        print(f"[{'PASS' if check.passed else 'FAIL'}] {check.name}: {check.detail}")

    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
