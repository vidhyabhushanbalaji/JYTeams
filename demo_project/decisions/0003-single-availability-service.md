# 0003 — One Availability Service

Status: Accepted · Date: 2026-09-24 · Deciders: Nadia Kerr, Dan Whitcombe, Sofia Mendes

## Context

The availability calculation existed in four places: Mercury's stored procedure, the marketplace
extract, the store stock report and a spreadsheet used by the fulfilment team. They disagreed by
between 0.4 % and 3 %, and the disagreement was reconciled manually every morning.

A UAT rehearsal made the cost obvious: two implementations omitted the quarantine term, and 61 orders
were taken against stock that could not be sold.

## Options

| Option | Consistency | Latency | Cost |
| :--- | :--- | :--- | :--- |
| A. One service, one formula | Guaranteed | 40–180 ms | New service |
| B. Shared library in each consumer | Guaranteed logic, different data | 0 ms | Cheap, but drift in versions |
| C. Fix Mercury's procedure | Within Mercury only | 300–900 ms | Does not help marketplaces |
| D. Document the formula and test each implementation | No guarantee | — | Permanent test burden |

## Decision

Compute availability in **one service (ATP)**, expose it through quote and read operations, and remove
every other implementation, including the marketplace extract.

## Why not a shared library

Option B was attractive: same code, no network hop. It fails on data, not logic. Each consumer would
hold its own view of stock, reservations and quarantine, and they would drift as surely as the current
spreadsheets did. The formula is the easy part; the inputs are the argument.

## Consequences

| Easier | Harder |
| :--- | :--- |
| One place to fix a calculation | A network hop on every consumer's path |
| One test suite for the whole domain | Mercury must accept a number it does not own |
| Quarantine handled once (INC-005) | ATP becomes a single point of failure, so it needs 99.95 % |
| Marketplaces and website agree by construction | Cache invalidation becomes critical |

## The single-point-of-failure trade

Consolidating availability means ATP failing stops everything promising. That is why its SLO is the
tightest in the platform and why the fallback path exists: a platform without a promise is survivable,
a platform with three contradictory numbers is not.

## Related

[ATP service contract](../reservation-policy/specification/atp-service-contract.md) ·
[ATP service](../architecture/services/atp-service.md) ·
[Oversell prevention](../reservation-policy/policy/oversell-prevention.md)
