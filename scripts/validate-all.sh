#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY_SCRIPT="${REPO_ROOT}/scripts/validate_all.py"

if command -v python >/dev/null 2>&1; then
  python "${PY_SCRIPT}" "$@"
elif command -v python.exe >/dev/null 2>&1; then
  if command -v cygpath >/dev/null 2>&1; then
    PY_SCRIPT_WIN="$(cygpath -w "${PY_SCRIPT}")"
    python.exe "${PY_SCRIPT_WIN}" "$@"
  elif [[ "${PY_SCRIPT}" == /mnt/* ]]; then
    _path_no_prefix="${PY_SCRIPT#/mnt/}"
    _drive="${_path_no_prefix%%/*}"
    _rest="${_path_no_prefix#*/}"
    PY_SCRIPT_WIN="${_drive^^}:/${_rest}"
    python.exe "${PY_SCRIPT_WIN}" "$@"
  else
    python.exe "${PY_SCRIPT}" "$@"
  fi
elif command -v python3 >/dev/null 2>&1; then
  python3 "${PY_SCRIPT}" "$@"
elif command -v py >/dev/null 2>&1; then
  py -3 "${PY_SCRIPT}" "$@"
else
  echo "python interpreter not found in PATH" >&2
  exit 127
fi
