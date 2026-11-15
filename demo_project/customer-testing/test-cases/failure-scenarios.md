# Test Cases — Failure Scenarios

Status: Draft · Owner: Aisha Bello · Last updated: 2026-11-13

What the platform does when something breaks. These are the cases that decide whether an incident is
a bad afternoon or a bad week, and they are tested by breaking things deliberately.

## The cases

| ID | Failure | Expected behaviour |
| :--- | :--- | :--- |
| FS-01 | One warehouse feed stops | That warehouse excluded after threshold; others serve; fallback shown |
| FS-02 | All feeds stop | No date; fallback copy; reservations refused `ATP_STOCK_STALE` |
| FS-03 | DPS down | Availability still returns; promise replaced by fallback (AC-13) |
| FS-04 | Redis unavailable | Availability served from database with higher latency; no wrong answers |
| FS-05 | Kafka broker lost | Producers retry; events buffered; no duplicate reservations on recovery |
| FS-06 | Carrier API down | Serviceability cached; bookings queued, not lost |
| FS-07 | Mercury stops emitting order events | Reservation worker falls back to polling; alert raised |
| FS-08 | Database failover | Writes fail for ≤ 30 s; retried; no duplicate reservations |
| FS-09 | Partial reservation failure (line 2 of 3) | Whole reservation rolled back unless partial requested |
| FS-10 | Clock skew between services | Promises remain monotonic; skew alert at 2 s |
| FS-11 | Warehouse hold applied during peak | New reservations stop; existing kept; site recovers within 60 s |
| FS-12 | Full rollback to previous promise source | Complete within 45 minutes (AC-21) |

## What "expected behaviour" means for each

| Case | The thing that must not happen |
| :--- | :--- |
| FS-01 | The site stays up while selling stock that does not exist |
| FS-02 | A date is invented to keep the page looking normal |
| FS-04 | Stale cache served as fresh without the degraded flag |
| FS-05 | Duplicate reservations after broker recovery |
| FS-07 | Reservations silently stop without an alert |
| FS-09 | Half an order reserved and half not, with no record |
| FS-12 | Partial rollback leaving two promise sources live |

## How failure is injected

| Failure | Method |
| :--- | :--- |
| Feed stop | Simulator `pause` mode |
| Feed malformed | Simulator `truncate` and `no_quarantine` |
| Service down | Kill the pod in the UAT cluster |
| Redis down | Disable the cache endpoint |
| Kafka loss | Broker scaling to zero in the test cluster |
| Carrier down | Mock at the gateway |
| Clock skew | Container clock offset |
| Database failover | Managed failover, invasive and scheduled |

Every injection is logged in the test record with its start and end time, so the resulting behaviour
can be matched to the graph afterwards.

## Results as of 2026-11-13

| Case | Status | Note |
| :--- | :--- | :--- |
| FS-01, FS-02 | Passing | Verified in the October rehearsal |
| FS-03 | Passing | Fallback wording pending legal (DEP-08) |
| FS-04 | Passing | Latency rises to 900 ms p95, acceptable |
| FS-05 | Not run | Kafka cluster not yet in UAT |
| FS-06 | Passing | Booking queue verified for 20 minutes |
| FS-07 | Failing | Polling fallback not implemented |
| FS-08 | Not run | Scheduled for the March rehearsal |
| FS-09, FS-10 | Passing | — |
| FS-11 | Passing | Timed at 41 s |
| FS-12 | Not run | Blocked on the rollback rehearsal |

FS-07 matters more than it looks: without a polling fallback, an event-bus outage means no
reservations at all, and the site keeps selling against stale availability until the stale threshold
catches it.

## Related

[Failure and retry](../../stock-feeds/reliability/failure-and-retry.md) ·
[Rollback plan](../../launch-readiness/rollback/rollback-plan.md) ·
[Runbooks](../../launch-readiness/runbooks/runbook-index.md)
