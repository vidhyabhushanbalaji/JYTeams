# Availability and SLOs

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Service level objectives for four services, with the error budget policy that decides when we stop
adding features and fix reliability instead.

## SLOs

| Service | Availability SLO | Latency SLO | Window |
| :--- | :--- | :--- | :--- |
| ATP service | 99.95 % | p95 180 ms | 28 days |
| Delivery promise | 99.9 % | p95 250 ms | 28 days |
| Reservation worker | 99.9 % * | p95 120 ms | 28 days |
| Feed ingestor | 99.5 % per source | cycle ≤ 8 s | 28 days |
| Integration hub | 99.9 % | event ≤ 2 s p95 | 28 days |

\* Measured as successful reservation attempts, not process uptime: a running worker that rejects
orders is not available.

## What the numbers permit

| SLO | Allowed downtime per 28 days | Roughly |
| :--- | :--- | :--- |
| 99.95 % | 20 minutes | One incident |
| 99.9 % | 40 minutes | One or two incidents |
| 99.5 % | 3 h 22 min | Three to four feed outages |

A 99.95 % target on ATP is deliberate: a storefront without availability cannot promise, and the whole
programme is a promise.

## Error budget policy

| Budget spent | Consequence |
| :--- | :--- |
| Under 50 % | Normal feature work |
| 50–75 % | Reliability items take priority in planning |
| 75–100 % | No new features until the budget recovers |
| Over 100 % | Post-incident review with the sponsor; launch decisions consider it |

This is a policy with teeth: in a two-person platform team, the only way to protect reliability is to
make it outrank features formally.

## Dependencies and their impact

| Dependency | Failure | Effect on our SLOs |
| :--- | :--- | :--- |
| Postgres | Down | ATP and worker down; SLO breached |
| Redis | Down | Slower, not wrong; latency SLO at risk |
| Kafka | Down | Reservations stop; polling fallback limits damage |
| A warehouse feed | Down | One source excluded; SLO unaffected |
| A carrier | Down | Promise fallback; SLO unaffected |

Note that a warehouse outage does not breach our SLO: excluding a source is the designed behaviour,
which is why the stale-stock metric is reported separately.

## Measurement

| SLO | Measured by |
| :--- | :--- |
| Availability | Successful responses ÷ total, excluding health checks |
| Latency | Server-side p95, cache hits included |
| Reservation success | Successful ÷ attempted |
| Feed freshness | Batches on time ÷ expected cycles |

Client-side latency is not used for SLOs because it includes the customer's network, but it is tracked
for the fallback-share metric.

## Reporting

| Cadence | Audience | Content |
| :--- | :--- | :--- |
| Daily | Operations | SLO status, budget remaining |
| Weekly | Programme | Any breach and its cause |
| Monthly | Steering | Budget trend, reliability work |

## Related

[Performance targets](./performance-targets.md) · [Observability](./observability.md) ·
[Hypercare plan](../../launch-readiness/hypercare/hypercare-plan.md)
