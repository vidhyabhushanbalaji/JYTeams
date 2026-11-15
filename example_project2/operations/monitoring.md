# Monitoring

Two dashboards and six alerts cover the whole system. If you are looking at anything else, you
are probably debugging rather than operating.

## Golden Signals

| Signal | Metric | Healthy |
| :--- | :--- | :--- |
| Latency | `meridian_http_request_duration_seconds` p95 | < 400 ms (reads) |
| Traffic | `meridian_http_requests_total` | Baseline ± 40% |
| Errors | `meridian_http_errors_total` ratio | < 0.5% |
| Saturation | `meridian_worker_queue_depth` | < 20 |

## Dashboards

**Meridian / Overview** — request rate, error ratio, p95 latency by route, queue depth, model
spend per hour.

**Meridian / Jobs** — imports running, stage durations, `description_status = failed` count,
placement suggestion latency, search `folders_visited` histogram.

## Alerts

| Alert | Condition | Severity | Runbook |
| :--- | :--- | :--- | :--- |
| `ApiErrorRateHigh` | 5xx ratio > 1% for 5 min | page | [Incident response](./runbooks/incident-response.md) |
| `ApiLatencyHigh` | p95 > 1 s for 10 min | page | [Incident response](./runbooks/incident-response.md) |
| `PostgresReplicationLag` | lag > 30 s for 5 min | page | [Database failover](./runbooks/database-failover.md) |
| `CertificateExpiringSoon` | < 14 days to expiry | ticket | [Certificate rotation](./runbooks/certificate-rotation.md) |
| `ModelSpendSpike` | hourly spend > 3× 7-day median | ticket | Below |
| `QueueDepthHigh` | > 100 for 15 min | ticket | Below |

## Investigating a Queue Backlog

1. Confirm the worker is alive: `meridian jobs list --status running`.
2. Look at `meridian_model_calls_total` — a plateau means calls are failing, not slow.
3. Check for one giant import: sort running jobs by `total_nodes`.
4. Scale workers before scaling `MERIDIAN_SUMMARY_CONCURRENCY`; the latter only multiplies cost.

## Model Spend

Spend is driven by folder count, not file count, so a deeply nested tree is more expensive per
document. Track `meridian_model_tokens_total` per project and compare against the budget in
[Service level objectives](./service-level-objectives.md).

## Logs

Structured JSON on stdout, one line per request or job transition. Always include `request_id`
and `job_id`. Retention is 14 days in the log platform; anything older lives in object storage.

## Related
- [Service level objectives](./service-level-objectives.md)
- [Backups and restore](./backups.md)
