# Release Performance Comparison Memo (OM-004)

Date: 2026-02-13

## Scope

Compare representative perf smoke measurements across this optimization cycle to capture release-level trend.

## Snapshot Comparison

| Snapshot | /health avg (ms) | /health p95 (ms) | /inventory avg (ms) | /inventory p95 (ms) | Note |
|---|---:|---:|---:|---:|---|
| Early P2 sample (BL-003) | 81.4 | 84.0 | 83.5 | 87.7 | From change_log P2-1 |
| NC-005 run | 523.2 | 4467.9 | 86.7 | 98.5 | Outlier spike on /health |
| Latest run (PRL-004) | 82.9 | 86.7 | 86.2 | 98.2 | Stable, within smoke budget |

## Interpretation

- `/inventory` remained consistently under 100 ms p95 in all sampled runs.
- `/health` shows one transient outlier during NC-005 smoke run, then returned to normal range.
- No persistent p95 regression observed in latest measurements.

## Release Gate Recommendation

- Keep smoke gate at `P95_BUDGET_MS=5000` for coarse protection.
- Add a tighter informational threshold for `/inventory` p95 (`<= 150 ms`) to catch early drift.
- Continue logging each task's before/after in `.ai/reports/2026-02-13_codex_change_log.md`.
