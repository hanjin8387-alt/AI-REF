#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
REQUEST_COUNT="${REQUEST_COUNT:-20}"
P95_BUDGET_MS="${P95_BUDGET_MS:-500}"
APP_TOKEN="${APP_TOKEN:-}"
DEVICE_ID="${DEVICE_ID:-perf-smoke-device}"

if ! command -v curl >/dev/null 2>&1; then
  echo "[perf-smoke] curl is required" >&2
  exit 1
fi

measure_endpoint() {
  local path="$1"
  local tmp
  tmp="$(mktemp)"

  echo "[perf-smoke] endpoint=${path} requests=${REQUEST_COUNT}"

  for i in $(seq 1 "$REQUEST_COUNT"); do
    local output
    output="$(
      curl -sS -o /dev/null \
        -w "%{http_code} %{time_total}" \
        -H "X-Device-ID: ${DEVICE_ID}" \
        ${APP_TOKEN:+-H "X-App-Token: ${APP_TOKEN}"} \
        "${API_URL}${path}"
    )"

    local code="${output%% *}"
    local time_total="${output##* }"

    if [[ "$code" == "000" ]] || [[ "$code" -ge 500 ]]; then
      echo "[perf-smoke] request failed endpoint=${path} status=${code}" >&2
      rm -f "$tmp"
      exit 1
    fi

    echo "$time_total" >> "$tmp"
  done

  local avg
  avg="$(awk '{sum += $1} END { if (NR == 0) { print 0 } else { printf "%.6f", sum / NR } }' "$tmp")"

  local rank
  rank="$(awk -v n="$REQUEST_COUNT" 'BEGIN { r = int((n * 95 + 99) / 100); if (r < 1) r = 1; print r }')"

  local p95
  p95="$(sort -n "$tmp" | awk -v target="$rank" 'NR == target { printf "%.6f", $1; exit }')"

  local avg_ms
  avg_ms="$(awk -v s="$avg" 'BEGIN { printf "%.1f", s * 1000 }')"
  local p95_ms
  p95_ms="$(awk -v s="$p95" 'BEGIN { printf "%.1f", s * 1000 }')"

  echo "[perf-smoke] endpoint=${path} avg_ms=${avg_ms} p95_ms=${p95_ms}"

  local over_budget
  over_budget="$(awk -v value="$p95_ms" -v budget="$P95_BUDGET_MS" 'BEGIN { if (value > budget) print 1; else print 0 }')"
  if [[ "$over_budget" == "1" ]]; then
    echo "[perf-smoke] budget exceeded endpoint=${path} p95_ms=${p95_ms} budget_ms=${P95_BUDGET_MS}" >&2
    rm -f "$tmp"
    exit 1
  fi

  rm -f "$tmp"
}

measure_endpoint "/health"
measure_endpoint "/inventory"

echo "[perf-smoke] completed"

