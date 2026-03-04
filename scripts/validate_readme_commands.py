#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"


@dataclass
class Check:
    command: str
    passed: bool
    detail: str


def _extract_shell_blocks(readme_text: str) -> list[str]:
    pattern = re.compile(r"```(?:bash|sh)\n(.*?)```", re.DOTALL)
    return [match.group(1) for match in pattern.finditer(readme_text)]


def _load_package_scripts(package_json_path: Path) -> set[str]:
    if not package_json_path.exists():
        return set()
    payload = json.loads(package_json_path.read_text(encoding="utf-8"))
    scripts = payload.get("scripts", {})
    if not isinstance(scripts, dict):
        return set()
    return set(scripts.keys())


def _check_line(command: str, cwd: Path) -> tuple[list[Check], Path]:
    checks: list[Check] = []
    parts = shlex.split(command, posix=True)
    if not parts:
        return checks, cwd

    while parts and "=" in parts[0] and not parts[0].startswith("-"):
        key, _, value = parts[0].partition("=")
        if key and value:
            parts = parts[1:]
            continue
        break

    if not parts:
        return checks, cwd

    cmd = parts[0]
    if cmd == "cd" and len(parts) >= 2:
        target = (cwd / parts[1]).resolve()
        passed = target.exists() and target.is_dir()
        checks.append(Check(command=command, passed=passed, detail=f"directory={target}"))
        if passed:
            cwd = target
        return checks, cwd

    if cmd in {"bash", "sh"} and len(parts) >= 2:
        script_path = (cwd / parts[1]).resolve()
        checks.append(Check(command=command, passed=script_path.exists(), detail=f"script={script_path}"))
        return checks, cwd

    if cmd in {"npm", "pnpm", "yarn"} and len(parts) >= 3 and parts[1] == "run":
        script_name = parts[2]
        scripts = _load_package_scripts(cwd / "package.json")
        checks.append(
            Check(
                command=command,
                passed=script_name in scripts,
                detail=f"script={script_name}, package_json={cwd / 'package.json'}",
            )
        )
        return checks, cwd

    if cmd == "copy" and len(parts) >= 2:
        source_path = (cwd / parts[1]).resolve()
        checks.append(Check(command=command, passed=source_path.exists(), detail=f"source={source_path}"))
        return checks, cwd

    if cmd in {"python", "python3", "py"} and "-m" in parts:
        module_index = parts.index("-m") + 1
        if module_index < len(parts):
            module_name = parts[module_index]
            if module_name == "pytest":
                tests_dir = (cwd / "tests").resolve()
                checks.append(Check(command=command, passed=tests_dir.exists(), detail=f"tests_dir={tests_dir}"))
        return checks, cwd

    if cmd == "uvicorn" and len(parts) >= 2:
        target = parts[1].split(":", maxsplit=1)[0]
        module_parts = target.split(".")
        module_path = (cwd / Path(*module_parts)).with_suffix(".py").resolve()
        checks.append(Check(command=command, passed=module_path.exists(), detail=f"module={module_path}"))
        return checks, cwd

    if cmd.startswith("./") or cmd.startswith("../"):
        target = (cwd / cmd).resolve()
        checks.append(Check(command=command, passed=target.exists(), detail=f"path={target}"))
        return checks, cwd

    return checks, cwd


def run_checks() -> list[Check]:
    readme_text = README_PATH.read_text(encoding="utf-8")
    blocks = _extract_shell_blocks(readme_text)
    checks: list[Check] = []

    for block in blocks:
        cwd = REPO_ROOT
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            line_checks, cwd = _check_line(line, cwd)
            checks.extend(line_checks)

    # Ensure README documents the canonical local validation entrypoint.
    checks.append(
        Check(
            command="README contains scripts/validate-all.sh",
            passed="scripts/validate-all.sh" in readme_text,
            detail="local CI-mirroring validation command must be documented",
        )
    )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate README command/file drift.")
    parser.add_argument("--output", required=True, help="Path to JSON output report")
    args = parser.parse_args()

    checks = run_checks()
    status = "passed" if all(check.passed for check in checks) else "failed"
    payload = {"status": status, "checks": [check.__dict__ for check in checks]}

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for check in checks:
        print(f"[{'PASS' if check.passed else 'FAIL'}] {check.command}: {check.detail}")

    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
