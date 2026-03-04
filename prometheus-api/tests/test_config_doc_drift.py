from __future__ import annotations

import re
from pathlib import Path

from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / "prometheus-api" / ".env.example"
README = REPO_ROOT / "README.md"


def _read_env_value(path: Path, key: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=(.*)$", re.MULTILINE)
    match = pattern.search(path.read_text(encoding="utf-8"))
    assert match is not None, f"{key} is missing from {path}"
    return match.group(1).strip()


def test_gemini_model_default_matches_env_example() -> None:
    runtime_default = str(Settings.model_fields["gemini_model"].default)
    env_default = _read_env_value(ENV_EXAMPLE, "GEMINI_MODEL")
    assert runtime_default == env_default


def test_readme_declares_canonical_gemini_model_default() -> None:
    readme = README.read_text(encoding="utf-8")
    env_default = _read_env_value(ENV_EXAMPLE, "GEMINI_MODEL")
    assert "GEMINI_MODEL" in readme
    assert env_default in readme
