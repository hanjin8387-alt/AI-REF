# Performance Budget (2026-02-13)

This document captures the current working performance budget and the latest measured smoke metrics.

## Budget Targets

| Metric | Warning | Budget Ceiling | Current Sample | Status |
|---|---:|---:|---:|---|
| API p95 (general) | 300 ms | 500 ms | `/inventory` p95 91.2 ms | OK |
| API p95 (scan/upload) | 10,000 ms | 15,000 ms | N/A in latest smoke | Unknown |
| API p95 (recipe recommendation) | 8,000 ms | 12,000 ms | N/A in latest smoke | Unknown |
| Memory RSS | 384 MB | 512 MB | N/A in latest smoke | Unknown |
| JS bundle (prod) | 6 MB | 8 MB | N/A in latest smoke | Unknown |
| Docker image | 250 MB | 300 MB | `prometheus-api:perf-ms` 547 MB | Over |

## Latest Perf Smoke Snapshot

Command:

```bash
'C:\Program Files\Git\bin\bash.exe' -lc "cd '/c/Users/HJSA/Desktop/개발/AI REF' && API_URL='https://ai-ref-api-274026276907.asia-northeast3.run.app' REQUEST_COUNT=10 P95_BUDGET_MS=5000 ./scripts/perf-smoke.sh"
```

Observed values:

- `/health`: avg 88.8 ms, p95 130.6 ms
- `/inventory`: avg 85.2 ms, p95 91.2 ms

## Guardrail Notes

- Keep p95 under budget during each performance task commit.
- Record before/after values in `.ai/reports/2026-02-13_codex_change_log.md`.
- If a task regresses and cannot be recovered within two minimal fixes, stop and document blockers.
