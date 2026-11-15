# Test Cases — Oversell Scenarios

Status: Draft · Owner: Aisha Bello · Last updated: 2026-11-13

Every way a unit can be sold twice, and the test that proves each is prevented. This is the most
important test file in the programme: oversell is the failure the platform exists to remove, and it
is also the one most likely to reappear through a well-meaning change.

## The cases

| ID | Given | When | Then |
| :--- | :--- | :--- | :--- |
| OS-01 | 1 unit, 2 simultaneous reservations | Both requests processed | Exactly one succeeds, one gets `ATP_INSUFFICIENT_STOCK` (AC-04) |
| OS-02 | 5 units, 10 concurrent requests | All processed | Exactly 5 succeed |
| OS-03 | Reservation expires | 31 minutes pass | Unit available again, reason `RESERVATION_EXPIRED` |
| OS-04 | Payment capture fails | Provider webhook | Reservation released, reason `PAYMENT_FAILED` |
| OS-05 | Order cancelled at 20 minutes | Cancel event | Released immediately, not at expiry |
| OS-06 | Feed shows 0 after reservation | Next cycle | Reservation stands until expiry; availability shows -1 nowhere |
| OS-07 | Feed shows 0 before reservation | Quote requested | No reservation; `ATP_STOCK_STALE` or insufficient |
| OS-08 | Unit in quarantine | Quote requested | Not available (AC-03) |
| OS-09 | Unit allocated to a wave | Quote requested | Not available; allocated ≠ available |
| OS-10 | Store reservation for a unit a store cannot find | Store cancels pick | Released, customer told, no phantom availability |
| OS-11 | Two warehouses claim the same transfer | Quote requested | One location wins, no double count |
| OS-12 | Reservation held during a warehouse hold | Hold applied | Existing reservation kept, no new ones |
| OS-13 | Discontinued SKU mid-basket | Checkout | Line refused, reason `SKU_DISCONTINUED` |
| OS-14 | Reservation expires exactly at wave build | Both events at once | No double claim (10-second offset) |
| OS-15 | Marketplace sells during a full resync | Push cycle | Reservation stands; quantity corrected on next push |

## How the race tests run

| Property | Value |
| :--- | :--- |
| Iterations | 200 per scenario |
| Concurrency | 25 workers per SKU |
| Seed | Fixed, reported on failure |
| Runtime | 4 minutes |
| Environment | CI and UAT |

A race test that passes 199 times out of 200 has failed. The report includes the seed so the exact
interleaving can be replayed, which is the only way to fix a genuine concurrency bug.

## The offset (OS-14)

Expiry runs 10 seconds after the wave window rather than during it. That offset exists because a UAT
rehearsal produced seven double-claims in a single second when both jobs ran together. The test pins
the behaviour: change the offset and this test fails.

## What is not tested here

Execution-level database isolation. The tests assert behaviour (one winner, clear error) rather than
the isolation level that produces it, because the isolation level can change with a dependency
upgrade and the behaviour cannot.

## Results as of 2026-11-13

| Case | Status | Note |
| :--- | :--- | :--- |
| OS-01 to OS-09 | Passing | UAT rehearsal environment |
| OS-10 | Failing | Store cancel path not implemented yet |
| OS-11 | Passing | With the one-location rule |
| OS-12 | Passing | Manual hold verified by Marcus |
| OS-13 | Passing | — |
| OS-14 | Passing | Offset verified |
| OS-15 | Not run | Needs the marketplace sandbox in UAT |

One failure across fifteen at this stage is a reasonable place to be, and OS-10 is blocked on the
store task API rather than on the platform.

## Related

[Oversell prevention](../../reservation-policy/policy/oversell-prevention.md) ·
[Reservation lifecycle](../../reservation-policy/policy/reservation-lifecycle.md) ·
[Failure scenarios](./failure-scenarios.md)
