# Observability

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

What we can see, what we alert on, and what an engineer can reconstruct after an incident. The design
rule is that every alert links to an action and every metric has an owner.

## The four dashboards

| Dashboard | Answers | Owner |
| :--- | :--- | :--- |
| Availability | Is the number fresh and right? | Dan Whitcombe |
| Promise | Are we promising accurately? | Gavin Shore |
| Reservations | Are orders being reserved? | Nadia Kerr |
| Revenue impact | How many orders are affected? | Marcus Feld |

The fourth is the one executives look at, and it exists because "error rate 4 %" means nothing to a
sponsor at 08:00 on launch day.

## Key metrics

| Metric | Type | Alert threshold |
| :--- | :--- | :--- |
| Availability quote p95 | Latency | 250 ms for 5 min |
| Availability error rate | Error | 1 % for 5 min |
| Feed staleness per source | Gauge | 2 cycles, then 3 |
| Reservations per minute | Throughput | −50 % vs same hour last week |
| Reservation refusal rate | Ratio | 2 % |
| Promise fallback share | Ratio | 3 % for 30 min |
| Promise accuracy (rolling 24 h) | Gauge | Below 88 % |
| Consumer lag | Gauge | 30 s |
| Dead-letter depth | Gauge | Any new message |
| Oversells per hour | Counter | 5 |

The reservation throughput alert is unusual and deliberate: a silent stop produces no errors, and it
is the failure that would cause the most damage.

## Logging

| Field | Required | Note |
| :--- | :--- | :--- |
| `trace_id` | Yes | Propagated from the channel |
| `order_id` | Where relevant | Never the customer |
| `sku` | Where relevant | — |
| `source` | Yes for feeds | — |
| `reason_code` | Yes for releases | — |
| Postcode | District plus hash only | Privacy |

Logs are structured JSON, retained 30 days hot and 90 days cold. No log line contains a name, address
or email, and a test searches for them before each release.

## Tracing

| Span | Why |
| :--- | :--- |
| `order.received` | See where an order enters |
| `availability.quote` | Latency attribution |
| `reservation.write` | The critical path |
| `promise.calculate` | Which input was slow |
| `feed.batch` | Batch size and duration |

A single trace for one slow order shows whether the delay was the carrier, the cache, or the
reservation lock.

## Alerts

| Alert | Severity | Action |
| :--- | :--- | :--- |
| Source excluded | High | Stock feed runbook |
| Availability errors | High | ATP outage runbook |
| Consumer lag | High | Check worker, scale |
| Fallback share high | Medium | Check DPS and carriers |
| Oversell surge | Critical | Oversell runbook |
| Dead letter | Medium | Inspect, replay |

Every alert message contains the runbook link. An alert without a next step is noise, and noise gets
muted during exactly the week it is needed.

## What we deliberately do not alert on

| Not alerted | Why |
| :--- | :--- |
| Single missed feed cycle | Handled by the threshold |
| One fallback order | Normal |
| Support queue length | Marcus watches it directly |
| Marketplace push delay under 5 min | Inside cadence |

## Post-incident reconstruction

| Artefact | Retention | Use |
| :--- | :--- | :--- |
| Feed batches | 30 days | Replay to reproduce |
| Reservation events | 90 days | Timeline of claims |
| Promise records | 30 days | What was said and on what basis |
| Logs | 90 days | Trace-level detail |
| Dashboard snapshots | 1 year | The numbers at the time |

The promise record is what lets an incident review say "we promised Wednesday because Riverside was 41
minutes stale and inside its threshold", which is a fixable finding rather than an argument.

## Related

[Availability and SLOs](./availability-and-slos.md) · [Runbooks](../../launch-readiness/runbooks/runbook-index.md) ·
[Event flows](../event-flows.md)
