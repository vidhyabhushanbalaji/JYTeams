# Midlands DC Feed

Status: Draft · Owner: Dan Whitcombe · Last updated: 2026-11-13

Midlands DC in Kettering is our largest stock location: 210,000 records, 61 % of orders routed here,
and the source of most of the fast-moving SKUs that make an oversell expensive.

## What the feed is

| Property | Today | Contract target |
| :--- | :--- | :--- |
| Mechanism | SQL view polled by Orbit | REST endpoint, or view poll if the endpoint slips |
| Shape | Full snapshot | Delta, with a nightly full snapshot |
| Records | 210,000 | 210,000 (snapshot), ~400 average delta |
| Cadence | Every 15 minutes | Every 5 minutes |
| Generation time | 11 seconds | Under 5 seconds |
| Feed timestamp | `SNAPSHOT_AT`, UTC | Same, plus per-row `UPDATED_AT` |
| Owner at site | Dermot Shaw | Dermot Shaw |

## Fields and how we use them

| Field | Meaning | Used as |
| :--- | :--- | :--- |
| `SKU` | Product code | Join key to Atlas |
| `ON_HAND` | Physical units in the building | Base quantity |
| `ALLOCATED` | Committed to an open wave | Subtracted |
| `UNAVAILABLE` | Quarantine, damage, quality hold | Subtracted (ignored today) |
| `LOCATION_CODE` | Bin or zone | Not used; kept for investigation |
| `UPDATED_AT` | Last movement time | Delta selection, freshness proof |
| `SNAPSHOT_AT` | Snapshot generation time | Staleness check |

## Problems at this site

| Problem | Detail | Effect |
| :--- | :--- | :--- |
| Full snapshot only | 210,000 rows every 15 minutes, ~7 MB | Poll cost, and no cheaper option exists today |
| Snapshot during wave build | Between 12:30 and 13:10, `ALLOCATED` includes partially built waves | Availability dips by 3–6 % every day |
| No reservation concept | A wave allocation is the first we hear of a pick | Soft reservations are invisible here |
| `UNAVAILABLE` ignored | Mercury never subtracted quarantine | 240-unit incident in August |

The snapshot-during-wave problem is the reason the availability service stores the last three
snapshots and uses the median `ALLOCATED` when a snapshot lands inside a wave window. That is a
temporary mitigation; the delta feed removes the need for it.

## Wave and cut-off timings

| Time | Event | Effect on the feed |
| :--- | :--- | :--- |
| 06:00 | Shift start, first wave build | `ALLOCATED` rises sharply |
| 12:30 | Cut-off wave build | Largest allocation movement of the day |
| 13:10 | Wave complete | Figures settle |
| 15:00 | Last dispatch | `ON_HAND` drops as parcels leave |
| 22:00 | Site closes | No further movement until 06:00 |

## Change request needed

The DC-WMS team needs to expose `UPDATED_AT` per row reliably for a delta feed; the column exists
but is only updated by goods-in and pick confirmation, not by every adjustment. That work is 6 days
and is booked into the WMS release on 2027-01-22.

## Related

[Glasgow DC](./glasgow-dc.md) · [Feed contracts](../protocol/feed-contracts.md) ·
[Warehouse supervisor interview](../../current-state/interviews/warehouse-supervisor-interview.md)
