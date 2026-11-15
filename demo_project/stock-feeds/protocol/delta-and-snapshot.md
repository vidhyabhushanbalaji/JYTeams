# Delta and Snapshot

Status: Agreed · Owner: Nadia Kerr · Last updated: 2026-11-06

Every feed is one of two shapes, and each has a failure mode the other does not. This document says
which sources use which, how a delta is proven complete, and what happens when a delta lies.

## The two shapes

| Shape | What it contains | Strength | Failure mode |
| :--- | :--- | :--- | :--- |
| Snapshot | Every record, every cycle | Self-correcting | Costly and slow; a partial snapshot looks complete |
| Delta | Only records changed since a cursor | Cheap and fast | A missed change is lost until the next full snapshot |

## What each source sends

| Source | Today | Target | Correction mechanism |
| :--- | :--- | :--- | :--- |
| Midlands DC | Snapshot | Delta + nightly snapshot | Nightly snapshot at 01:00 |
| Glasgow DC | Snapshot | Delta + nightly snapshot | Nightly snapshot at 01:10 |
| Northgate | Delta | Delta | Weekly full snapshot, Sunday 02:30 |
| Riverside | Delta | Delta | Nightly full snapshot at 01:00 |
| Stores | Snapshot | Snapshot | It is the correction |

## Proving a delta is complete

A delta is trusted only when it arrives with a cursor and a count:

| Field | Required | Purpose |
| :--- | :--- | :--- |
| `cursor_from` | Yes | Where the source believes we were |
| `cursor_to` | Yes | Where it believes we are now |
| `record_count` | Yes | Number of records in the batch |
| `batch_timestamp` | Yes | Source clock |

If `cursor_from` does not match our stored cursor, the delta is **rejected** and a full snapshot is
requested. This is the single most important rule in the feed protocol: applying a delta from an
unknown starting point produces a stock figure that is wrong in an unbounded way, and no amount of
downstream cleverness recovers it.

## How often cursors drift

| Source | Drift events in October | Cause |
| :--- | :--- | :--- |
| Northgate | 3 | API timeout mid-page |
| Riverside | 7 | Delivery-run lock during a delta |
| Midlands | 0 | Snapshot only |

A drift costs one full snapshot: 11 minutes for Riverside, 6 seconds for Northgate. That is cheap,
which is why the rule is absolute rather than "try to reconcile".

## Snapshot completeness

A snapshot has its own lie: a truncated response that parses correctly. Three checks guard against
it:

1. `record_count` must match the number of rows parsed.
2. The record count must be within 5 % of the previous snapshot (a 40 % drop is a truncation, not a
   stock movement).
3. A snapshot must contain at least one row for each of the top 500 SKUs, unless the SKU is marked
   discontinued.

The second check caught a truncated Midlands snapshot in UAT that would otherwise have removed
168,000 records from availability for 15 minutes.

## Midnight rule

A full snapshot received between 23:00 and 01:00 is applied in full but flagged `overnight=true`,
because that is when batch jobs run and the risk of a partial snapshot is highest. The flag does not
change behaviour; it exists so an incident review can tell whether a discrepancy came from an
overnight snapshot.

## Related

[Feed contracts](./feed-contracts.md) · [Reconciliation](../reliability/reconciliation.md) ·
[Stock record data dictionary](../../reference/data-dictionary/stock-record.md)
