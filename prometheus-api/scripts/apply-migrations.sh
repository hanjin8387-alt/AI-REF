#!/usr/bin/env bash
set -euo pipefail

DB_URL="${DATABASE_URL:-}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./migrations}"

if [[ -z "${DB_URL}" ]]; then
  echo "[migrate] DATABASE_URL is required" >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "[migrate] psql is required" >&2
  exit 1
fi

if [[ ! -d "${MIGRATIONS_DIR}" ]]; then
  echo "[migrate] migrations directory not found: ${MIGRATIONS_DIR}" >&2
  exit 1
fi

echo "[migrate] applying migrations from ${MIGRATIONS_DIR}"
for file in "${MIGRATIONS_DIR}"/*.sql; do
  echo "[migrate] applying ${file}"
  psql "${DB_URL}" -v ON_ERROR_STOP=1 -f "${file}"
done

echo "[migrate] done"
