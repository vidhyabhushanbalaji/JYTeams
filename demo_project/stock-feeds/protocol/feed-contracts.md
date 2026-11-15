# Feed Contracts

Status: Draft · Owner: Dan Whitcombe · Last updated: 2026-11-13

A feed contract is the agreement between us and a warehouse: what they send, how often, in what
shape, and what happens when it is late or wrong. There are five, one per source, and M3 requires
all five signed by 2027-01-15.

## What every contract must contain

| Clause | Detail | Why |
| :--- | :--- | :--- |
| Shape | Delta or snapshot, with field list and types | Prevents a "small change" becoming a rewrite |
| Cadence | Minimum update frequency, measured on feed timestamp | The promise depends on it |
| Paging | Page size, ordering stability, resume cursor | Large estates cannot be fetched in one call |
| Freshness field | A timestamp per record and per batch | Staleness must be provable |
| Quarantine semantics | Explicit, named fields | The August incident |
| Failure behaviour | What the source does when it cannot serve | Avoids silent gaps |
| Notice | 30 days for a breaking change | UAT and launch depend on stability |
| Test access | Sandbox or replay fixture | No warehouse in the test path |
| Support | Named contact and hours | Escalation during hypercare |

## The five contracts

| Source | Shape | Cadence | Signed | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Midlands DC | Snapshot → delta | 15 → 5 min | Draft | Delta needs a WMS change (6 days) |
| Glasgow DC | Snapshot → delta | 15 → 5 min | Draft | Requires WMS 8.4.2 upgrade |
| Northgate | Delta | 15 → 5 min | Draft | Contract variation requested |
| Riverside | Delta | 15 → 10 min | Not drafted | Vendor change request needed |
| Store network | Snapshot | 24 h → 60 min | Not drafted | CR-007 approved, work booked |

## Required fields

| Field | Type | Mandatory | Meaning |
| :--- | :--- | :--- | :--- |
| `sku` | string | Yes | Our SKU code, not theirs |
| `location_id` | string | Yes | Canonical location key |
| `on_hand` | integer | Yes | Physical units |
| `allocated` | integer | Yes | Committed to picks |
| `quarantine` | integer | Yes (0 allowed) | Not sellable |
| `condition` | enum | No | `new` or `open_box` |
| `updated_at` | ISO 8601 | Yes | Per record |
| `batch_id` | string | Yes | Groups a poll |
| `batch_timestamp` | ISO 8601 | Yes | When the source began the batch |
| `sequence` | integer | Yes | Monotonic per source |

If a source cannot provide `quarantine`, the contract must state how it is represented, and the
availability service will treat the missing field as zero with a logged warning. Silence is the one
thing not allowed.

## Service levels

| Level | Target | Consequence of breach |
| :--- | :--- | :--- |
| Feed availability | 99.5 % of cycles delivered | Warehouse excluded from promise after the stale threshold |
| Batch latency | Inside the cadence | Availability degrades |
| Record accuracy | 99.5 % against a sample | Monthly review, remediation plan |
| Schema stability | No breaking change without 30 days notice | Change request |

## What is not in the contract

A guarantee that the warehouse's own number is right. We can measure timeliness and completeness;
we cannot audit a shelf from a contract, and pretending otherwise would make the contract
unenforceable. Accuracy is measured by cycle counts and reported monthly.

## Sign-off

Each contract is signed by the site or vendor operations lead and by Dan Whitcombe. Sofia Mendes
accepts the cadence and quarantine clauses, because those are the two that change what we can
promise to a customer.

## Related

[Polling and cadence](./polling-and-cadence.md) · [Delta and snapshot](./delta-and-snapshot.md) ·
[Latency budget](../reliability/latency-budget.md)
