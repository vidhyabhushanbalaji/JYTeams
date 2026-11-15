# Feed Simulator

Status: Agreed · Owner: Aisha Bello · Last updated: 2026-11-06

Testing a stock platform needs five stock sources that misbehave on demand. The simulator is a small
service that replays recorded feeds, injects faults, and stands in for any source that has no
sandbox.

## What it does

| Mode | Purpose |
| :--- | :--- |
| `replay` | Replays a captured batch file at the original cadence |
| `inject` | Mutates a batch: drops rows, delays the timestamp, corrupts a page |
| `script` | Follows a scenario file, used by automated tests |
| `soak` | Generates synthetic changes at a target rate for load tests |

## Replay fixtures

Captured batches live in the test environment, not in this repository:

| Fixture | Source | Size | Captured |
| :--- | :--- | :--- | :--- |
| `midlands-2026-10-28` | Midlands DC | 210,000 rows | 2026-10-28 |
| `glasgow-2026-10-28` | Glasgow DC | 96,000 rows | 2026-10-28 |
| `northgate-2026-11-04` | Northgate | 2,410 rows delta | 2026-11-04 |
| `riverside-2026-11-04` | Riverside | 1,180 rows delta | 2026-11-04 |
| `stores-2026-11-01` | Store network | 41,000 rows | 2026-11-01 |

Fixtures are masked: SKU codes are real, quantities are scaled by a fixed factor, and no customer or
order data is included.

## Fault injection

| Fault | What it does | Used to test |
| :--- | :--- | :--- |
| `drop_page` | Omits one page of a delta | Cursor mismatch rejection |
| `truncate` | Delivers 60 % of a snapshot | Snapshot completeness check |
| `stale_clock` | Backdates `batch_timestamp` | Stale-stock guard |
| `no_quarantine` | Sends zero for the quarantine field | Availability calculation |
| `duplicate_batch` | Replays the same batch twice | Idempotency |
| `slow_response` | Adds 4 s per page | Poll timeout and backpressure |
| `maintenance` | Rejects all requests for N minutes | Declared maintenance handling |

## Scenario file

```yaml
scenario: reservation-race
duration_seconds: 30
sources:
  midlands-dc:
    mode: replay
    fixture: midlands-2026-10-28
    faults: []
steps:
  - at: 0
    action: quote
    sku: HH-GDP-4410
    quantity: 1
  - at: 1
    action: reserve
    order: TEST-1001
    expect: success
  - at: 2
    action: reserve
    order: TEST-1002
    expect: insufficient_stock
```

The race scenario runs 200 times in CI and is the test that proves the reservation is atomic under
concurrency.

## What the simulator is not

It is not a mock of the services. The platform runs for real against simulated feeds, so a test that
passes exercises the ingestor, the computation and the reservation path, not a stub. It is also not
available in production: no environment outside UAT and local developer machines may enable it.

## Related

[Test data](../../customer-testing/strategy/test-data.md) · [Replay harness](../../customer-testing/strategy/environments.md) ·
[Failure and retry](../reliability/failure-and-retry.md)
