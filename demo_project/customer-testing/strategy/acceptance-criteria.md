# Acceptance Criteria

Status: Draft · Owner: Aisha Bello · Last updated: 2026-11-13

The twenty-two criteria that decide whether the platform is accepted. Each has a number, a
measurement method and a link to the rule it proves. Four are not yet measurable because they depend
on open policy decisions.

## Stock and availability

| ID | Criterion | Target | Measured by | Rule |
| :--- | :--- | :--- | :--- | :--- |
| AC-01 | Availability reflects a feed change within one cycle | ≤ 6 min p95 | Timestamp diff, 500 samples | Feed contract |
| AC-02 | Stale feed removes the warehouse from availability | 100 % of cases | Fault injection, 20 runs | RSV-12 |
| AC-03 | Quarantine is never sellable | 100 % | Simulated feeds, 5 sources | RSV-13 |
| AC-04 | Two concurrent reservations for one unit never both succeed | 0 failures | Race scenario, 200 runs | RSV-01 |
| AC-05 | A reservation expires and returns stock | ≤ 61 s after TTL | Timed test, 50 runs | RSV-01 |
| AC-06 | Release carries a valid reason code | 100 % | Event validation | RSV-17 |
| AC-07 | Split shipments each carry their own reservation | 100 % | 12 scripted baskets | Split rules |
| AC-08 | Partial availability offers the right options | 100 % | 20 scripted baskets | RSV-20 |

## Promise

| ID | Criterion | Target | Measured by | Rule |
| :--- | :--- | :--- | :--- | :--- |
| AC-09 | Product page date equals checkout date | 100 % | 60 product journeys | Messaging rules |
| AC-10 | Promise uses the warehouse promise cut-off, not the carrier cut-off | 100 % | Hour-of-day boundary tests | Cut-off table |
| AC-11 | Bank holiday buffer applied | 100 % | Calendar tests, 8 dates | RSV-19 |
| AC-12 | Bulky beyond the 14-day horizon shows a week | 100 % | 10 journeys | Messaging rules |
| AC-13 | Fallback shown instead of a date when DPS is down | 100 % | Fault injection | ADR 0010 |
| AC-14 | Promise accuracy in beta | ≥ 88 % tolerant | Beta orders | Promise metric |

## Channels and stores

| ID | Criterion | Target | Measured by | Rule |
| :--- | :--- | :--- | :--- | :--- |
| AC-15 | Marketplace inventory pushed within 5 minutes | ≤ 5 min p95 | ChannelBridge logs | ADR 0004 |
| AC-16 | Collection reservation created and picked within 30 minutes | ≥ 90 % | 40 store tests | RSV-07 |
| AC-17 | Uncollected reservation released with a reason | 100 % | 10 timed tests | RSV-10 |
| AC-18 | Store stock above 90 minutes old stops collection promises | 100 % | Fault injection | Stale table |

## Operations

| ID | Criterion | Target | Measured by | Rule |
| :--- | :--- | :--- | :--- | :--- |
| AC-19 | Sustained 25 order events per second | No errors, p95 ≤ 400 ms | Load test | Load profile |
| AC-20 | Burst 90 events per second for 60 s | No data loss | Load test | Load profile |
| AC-21 | Rollback completes within 45 minutes | 100 % | Rehearsal, 2 runs | Rollback plan |
| AC-22 | Manual warehouse hold takes effect within 60 seconds | ≤ 60 s | 10 timed tests | RSV-18 |

## The four not yet measurable

| ID | Blocker | What changes |
| :--- | :--- | :--- |
| AC-07 (partial) | RSV-06 decides bulky reservation timing | Split rules for bulky |
| AC-12 | RSV-06 | Horizon and messaging for bulky |
| AC-14 | Beta date depends on DPIA | Timeline only, not the target |
| AC-17 | RSV-11 decides the hold length | Test duration |

These four are why the criteria document is v0.9 rather than v1.0. They become measurable the week
after the 2026-12-03 steering decision, and none of them is a reason to delay build.

## How a criterion passes

A criterion passes when the measurement is attached to the UAT record and signed by the criterion
owner. "Passed in conversation" is not a pass, and the sign-off document lists every measurement
reference rather than a summary score.

## Related

[UAT exit criteria](../uat/entry-and-exit-criteria.md) · [Test cases](../test-cases/) ·
[Load profile](../non-functional/load-profile.md)
