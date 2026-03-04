#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional live integration smoke check.")
    parser.add_argument("--output", required=True, help="Path to JSON output report")
    args = parser.parse_args()

    run_live_smoke = os.environ.get("RUN_LIVE_SMOKE", "").strip().lower() in {"1", "true", "yes", "on"}
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not run_live_smoke:
        payload = {
            "status": "skipped",
            "reason": "RUN_LIVE_SMOKE is not enabled. Live smoke checks are optional and non-blocking by default.",
        }
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(payload["reason"])
        return 0

    api_url = os.environ.get("SMOKE_API_URL", "").strip()
    app_id = os.environ.get("SMOKE_APP_ID", "").strip()
    if not api_url or not app_id:
        payload = {
            "status": "failed",
            "reason": "RUN_LIVE_SMOKE is enabled but SMOKE_API_URL or SMOKE_APP_ID is missing.",
        }
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(payload["reason"])
        return 1

    health_url = f"{api_url.rstrip('/')}/health"
    request = urllib.request.Request(
        health_url,
        headers={
            "X-App-ID": app_id,
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            code = response.getcode()
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        payload = {
            "status": "failed",
            "reason": f"live smoke request failed: {exc}",
            "url": health_url,
        }
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(payload["reason"])
        return 1

    passed = 200 <= code < 300
    payload = {
        "status": "passed" if passed else "failed",
        "url": health_url,
        "http_status": code,
        "response_preview": body[:500],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"smoke status={payload['status']} http_status={code}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
