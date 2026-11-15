# Service Level Objectives

These are the targets the team is measured against. They are deliberately modest; the error
budget is what makes shipping possible.

## Objectives

| Service | SLI | Objective | Window |
| :--- | :--- | :--- | :--- |
| API reads | Non-5xx responses | 99.9% | 28 days |
| API reads | p95 latency < 500 ms | 95% of minutes | 28 days |
| Import | Succeeds within 3× estimated duration | 99% of jobs | 28 days |
| Placement | Suggestion returned < 30 s | 99% of requests | 28 days |
| Search | Result returned < 10 s | 95% of requests | 28 days |
| Storage | Blob readable on first attempt | 99.95% | 28 days |

## Measured Baselines

| Workload | Typical | p95 |
| :--- | :--- | :--- |
| Import, 50 files / 12 folders | 74 s | 112 s |
| Import, 400 files / 60 folders | 9 min | 14 min |
| Placement | 11 s | 24 s |
| Search, 100 folders | 3.1 s | 6.8 s |
| Search with fallback sweep | 7.4 s | 11.2 s |

## Error Budget

99.9% over 28 days leaves roughly 40 minutes of allowed unavailability. Policy:

- Above 50% remaining: ship freely.
- Below 50% remaining: no risky migrations, reviews get a second pair of eyes.
- Exhausted: change freeze except for fixes to the cause; the incident review owns the exit.

## What Breaks the Budget Fastest

1. **Model provider outage** — imports stall, search still works because it degrades per-folder.
2. **Postgres primary loss** — everything fails; recovery time is the whole budget.
3. **Runaway import** — a single tenant importing continuously starves others' workers.

The third is why imports are limited per tenant — see [Rate limits](../api/rate-limits.md).

## Not Covered by These Objectives

- Latency of the browser client's own rendering.
- Time spent waiting for a human to approve a deployment.
- Cost per import, which is tracked against a budget rather than an objective.

## Review Cadence

Objectives are reviewed monthly against `meridian_slo_*` metrics. If an objective has not been
breached in two quarters, tighten it; if it was breached twice, write a decision record
explaining the new number instead of quietly missing it.
