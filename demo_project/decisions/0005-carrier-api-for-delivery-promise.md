# 0005 — Carrier APIs for the Delivery Date

Status: Accepted · Date: 2026-09-30 · Deciders: Gavin Shore, Nadia Kerr, Tom Alder

## Context

Delivery dates are currently computed from a table of lead times maintained by hand: postcode band,
service, plus a day. It is wrong for 29 % of orders, and it cannot represent slot availability, Saturday
exclusions or capacity, all of which the carriers actually know.

## Options

| Option | Accuracy | Cost | Dependency |
| :--- | :--- | :--- | :--- |
| A. Carrier APIs at promise time | Highest | Calls per quote | Carrier availability |
| B. Cache the carrier's zone and service tables | Medium | Cheap | Weekly file updates |
| C. Better hand-maintained table | Low | Cheap | Somebody's time |
| D. Ask the carrier at booking only | Low for the customer | Cheap | Too late |

## Decision

Use **carrier APIs for serviceability and lead time**, cached per postcode for 24 hours, and treat a
carrier's absence as a reason to fall back rather than to guess.

## Why not a static table

Option B was the compromise and it fails on the two cases that matter most: Saturday postcode exclusions
and Northline slot capacity. Both change daily, and both produce a wrong date rather than a vague one.
A table cannot be accurate and cheap at the same time in a network with three carriers and 1.9 % of
postcodes excluded from bulky.

## Consequences

| Easier | Harder |
| :--- | :--- |
| Dates reflect real carrier capability | Carrier outage degrades the date |
| Saturday and bulky rules encoded once | Three integrations to maintain |
| Capacity-aware promises become possible | Cache invalidation on serviceability changes |
| Postcode-level accuracy measurable | A carrier's sandbox is not production |

## What this enables

Bulky slot awareness is the largest prize: 96 rebookings a day at £46 each, and a 58 % promise accuracy
on the segment. The API decision makes slot-aware promises possible, although implementing them depends
on RSV-06.

## Related

[Delivery date logic](../delivery-promise/calculation/delivery-date-logic.md) ·
[Parcelway](../delivery-promise/carriers/parcelway.md) ·
[Northline Freight](../delivery-promise/carriers/northline-freight.md)
