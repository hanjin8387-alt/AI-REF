#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class StepResult:
    name: str
    command: str
    cwd: str
    log_file: str
    started_at: str
    ended_at: str
    duration_seconds: float
    exit_code: int
    status: str


def _timestamp() -> str:
    return datetime.now().astimezone().isoformat()


def run_step(name: str, command: list[str], cwd: Path, log_file: Path) -> StepResult:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    started_at = _timestamp()
    started = datetime.now().astimezone()

    with log_file.open("w", encoding="utf-8") as fp:
        fp.write(f"$ {shlex.join(command)}\n")
        fp.write(f"cwd={cwd}\n\n")
        process = subprocess.run(
            command,
            cwd=str(cwd),
            stdout=fp,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

    ended = datetime.now().astimezone()
    duration = (ended - started).total_seconds()
    ended_at = _timestamp()
    status = "passed" if process.returncode == 0 else "failed"

    return StepResult(
        name=name,
        command=shlex.join(command),
        cwd=str(cwd),
        log_file=str(log_file.relative_to(REPO_ROOT)),
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration,
        exit_code=process.returncode,
        status=status,
    )


def skipped_step(name: str, cwd: Path, log_file: Path, reason: str) -> StepResult:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    started_at = _timestamp()
    log_file.write_text(reason + "\n", encoding="utf-8")
    return StepResult(
        name=name,
        command=reason,
        cwd=str(cwd),
        log_file=str(log_file.relative_to(REPO_ROOT)),
        started_at=started_at,
        ended_at=started_at,
        duration_seconds=0.0,
        exit_code=0,
        status="skipped",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run reproducible repository validation checks.")
    parser.add_argument(
        "--mode",
        choices=["all", "backend", "frontend", "docs"],
        default="all",
        help="Validation slice to run.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip dependency install steps and run checks only.",
    )
    parser.add_argument(
        "--artifact-dir",
        default=os.environ.get("VALIDATION_ARTIFACT_DIR", "artifacts"),
        help="Artifact directory relative to repo root or absolute path.",
    )
    return parser


def write_summary_and_exit(
    *,
    artifact_dir: Path,
    mode: str,
    started_at: str,
    started: datetime,
    steps: list[StepResult],
    exit_code: int,
) -> int:
    ended = datetime.now().astimezone()
    ended_at = _timestamp()
    summary = {
        "mode": mode,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": (ended - started).total_seconds(),
        "exit_code": exit_code,
        "status": "passed" if exit_code == 0 else "failed",
        "steps": [step.__dict__ for step in steps],
    }
    summary_path = artifact_dir / "validation-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Validation summary: {summary_path}")
    return exit_code


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    if not artifact_dir.is_absolute():
        artifact_dir = REPO_ROOT / artifact_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)

    started_at = _timestamp()
    started = datetime.now().astimezone()
    steps: list[StepResult] = []
    overall_exit_code = 0
    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

    def run(name: str, command: list[str], cwd: Path, log_path: Path) -> StepResult:
        result = run_step(name, command, cwd, log_path)
        steps.append(result)
        print(f"[{result.status.upper()}] {name} (exit={result.exit_code})")
        return result

    def mark_failure_if_needed(result: StepResult) -> None:
        nonlocal overall_exit_code
        if result.exit_code != 0:
            overall_exit_code = 1

    def skip(name: str, cwd: Path, log_path: Path, reason: str) -> None:
        result = skipped_step(name, cwd, log_path, reason)
        steps.append(result)
        print(f"[SKIPPED] {name}")

    if args.mode in {"all", "backend"}:
        backend_artifacts = artifact_dir / "backend"
        backend_artifacts.mkdir(parents=True, exist_ok=True)
        backend_ready = True

        if not args.skip_install:
            result = run(
                "backend-install",
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    "requirements.txt",
                    "-r",
                    "requirements-dev.txt",
                ],
                REPO_ROOT / "prometheus-api",
                backend_artifacts / "backend-install.log",
            )
            mark_failure_if_needed(result)
            backend_ready = result.exit_code == 0

        if backend_ready:
            result = run(
                "backend-lint",
                [sys.executable, "-m", "ruff", "check", "app", "tests"],
                REPO_ROOT / "prometheus-api",
                backend_artifacts / "backend-lint.log",
            )
            mark_failure_if_needed(result)

            result = run(
                "backend-hardening-check",
                [
                    sys.executable,
                    "scripts/check_backend_hardening.py",
                    "--output",
                    str((backend_artifacts / "hardening-check.json").resolve()),
                ],
                REPO_ROOT,
                backend_artifacts / "backend-hardening-check.log",
            )
            mark_failure_if_needed(result)

            result = run(
                "backend-test",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "tests",
                    "--cov=app",
                    f"--cov-report=xml:{str((backend_artifacts / 'coverage.xml').resolve())}",
                    f"--junitxml={str((backend_artifacts / 'junit.xml').resolve())}",
                ],
                REPO_ROOT / "prometheus-api",
                backend_artifacts / "backend-test.log",
            )
            mark_failure_if_needed(result)
        else:
            skip(
                "backend-lint",
                REPO_ROOT / "prometheus-api",
                backend_artifacts / "backend-lint.log",
                "Skipped because backend-install failed.",
            )
            skip(
                "backend-hardening-check",
                REPO_ROOT,
                backend_artifacts / "backend-hardening-check.log",
                "Skipped because backend-install failed.",
            )
            skip(
                "backend-test",
                REPO_ROOT / "prometheus-api",
                backend_artifacts / "backend-test.log",
                "Skipped because backend-install failed.",
            )

    if args.mode in {"all", "frontend"}:
        frontend_artifacts = artifact_dir / "frontend"
        frontend_artifacts.mkdir(parents=True, exist_ok=True)
        frontend_ready = True

        if not args.skip_install:
            result = run(
                "frontend-install",
                [npm_cmd, "ci"],
                REPO_ROOT / "prometheus-app",
                frontend_artifacts / "frontend-install.log",
            )
            mark_failure_if_needed(result)
            frontend_ready = result.exit_code == 0

        if frontend_ready:
            result = run(
                "frontend-typecheck",
                [npm_cmd, "run", "typecheck"],
                REPO_ROOT / "prometheus-app",
                frontend_artifacts / "frontend-typecheck.log",
            )
            mark_failure_if_needed(result)

            result = run(
                "frontend-test",
                [npm_cmd, "run", "test:ci"],
                REPO_ROOT / "prometheus-app",
                frontend_artifacts / "frontend-test.log",
            )
            mark_failure_if_needed(result)
        else:
            skip(
                "frontend-typecheck",
                REPO_ROOT / "prometheus-app",
                frontend_artifacts / "frontend-typecheck.log",
                "Skipped because frontend-install failed.",
            )
            skip(
                "frontend-test",
                REPO_ROOT / "prometheus-app",
                frontend_artifacts / "frontend-test.log",
                "Skipped because frontend-install failed.",
            )

    if args.mode in {"all", "docs"}:
        docs_artifacts = artifact_dir / "docs"
        docs_artifacts.mkdir(parents=True, exist_ok=True)

        docs_steps = [
            (
                "docs-check-config-drift",
                [
                    sys.executable,
                    "scripts/check_config_drift.py",
                    "--output",
                    str((docs_artifacts / "config-drift.json").resolve()),
                ],
                docs_artifacts / "check-config-drift.log",
            ),
            (
                "docs-validate-readme-commands",
                [
                    sys.executable,
                    "scripts/validate_readme_commands.py",
                    "--output",
                    str((docs_artifacts / "readme-command-check.json").resolve()),
                ],
                docs_artifacts / "validate-readme-commands.log",
            ),
            (
                "docs-optional-smoke",
                [
                    sys.executable,
                    "scripts/optional_integration_smoke.py",
                    "--output",
                    str((docs_artifacts / "optional-smoke.json").resolve()),
                ],
                docs_artifacts / "optional-smoke.log",
            ),
        ]

        for name, command, log_path in docs_steps:
            result = run(name, command, REPO_ROOT, log_path)
            mark_failure_if_needed(result)

    return write_summary_and_exit(
        artifact_dir=artifact_dir,
        mode=args.mode,
        started_at=started_at,
        started=started,
        steps=steps,
        exit_code=overall_exit_code,
    )


if __name__ == "__main__":
    raise SystemExit(main())
