# 0001 — Reserve Stock at Payment Authorisation

Status: Accepted · Date: 2026-10-22 · Deciders: Sofia Mendes, Tom Alder, Priya Raman

## Context

Stock is currently claimed when a warehouse builds a pick wave, which can be 14 hours after a website
order. That gap is the direct cause of most of our **2.1 % oversell rate**, and of the 300 order lines
cancelled every day for want of stock.

Four moments were available: basket add, payment authorisation, routing run, and warehouse allocation.
Each protects stock differently and each costs the customer something different.

## Options

| Option | Protects stock | Costs |
| :--- | :--- | :--- |
| A. At basket add | Most | 8,400 abandoned baskets a day would hold stock; measured at £411,000 of sellable value tied up |
| B. At payment authorisation | Strongly | A 30-minute window where payment may still fail |
| C. At routing run (today) | Barely | Oversell all day; rejected outright |
| D. At warehouse allocation | Almost none | Sell the same unit repeatedly until a wave is built |

## Decision

Reserve at **payment authorisation**, for 30 minutes, extended to 60 on capture confirmation.

## Why not basket add

It was the popular option in the workshop until the abandoned-basket data was put on the screen.
Removing £411,000 of stock value from sale on a normal Tuesday, concentrated in the fastest-moving
SKUs, is a worse commercial outcome than a 2.1 % oversell.

## Consequences

| Easier | Harder |
| :--- | :--- |
| Oversell becomes a reservation problem, not a stock problem | Expiry handling becomes critical; a bug leaves stock locked |
| A customer with a confirmed payment holds the unit | Payment failure and timeout paths need real testing |
| Marketplaces can be fed the same number | A late capture may find the unit gone and must re-check |
| Policy is expressible as a rule table | Wholesale needs a different rule (RSV-16), which complicates the worker |

The last row is the main cost: the reservation worker serves two commercial models, and the wholesale
exception is written into the code rather than emerging from the configuration.

## What would change this

If oversell stays above 0.8 % for a month with fresh feeds, the next step is option A restricted to the
top 200 SKUs during promotions, which trading already does manually. That would be a new record, not an
edit to this one.

## Related

[Reservation timing options](../reservation-policy/specification/reservation-timing-options.md) ·
[Reservation rules](../reservation-policy/policy/reservation-rules.md) ·
[Oversell prevention](../reservation-policy/policy/oversell-prevention.md)
