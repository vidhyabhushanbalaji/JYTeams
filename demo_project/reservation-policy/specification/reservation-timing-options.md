# Reservation Timing Options

Status: Agreed · Owner: Sofia Mendes · Last updated: 2026-10-22

The decision everyone expected to be technical was actually commercial: at which moment does a unit
stop being available to everybody else? Four options were assessed between September and October
2026, and the steering group chose option B on 2026-10-22.

## The options

| Option | When stock is claimed | Protects stock | Customer experience | Cost |
| :--- | :--- | :--- | :--- | :--- |
| A | On "add to basket" | Most | Worst: abandoned baskets hold stock | High lost sales |
| B | On payment authorisation | Strongly | Good: a real order holds stock | None |
| C | On routing run (00:40) | Barely | Poor: oversell all day | None |
| D | On warehouse allocation | Nearly none | Poor plus late cancellations | None |

## Option A: claim at basket add

Measured over two weeks in September: **8,400 baskets a day** were abandoned with at least one item
in them. With a 30-minute hold, that would remove an average of **£411,000 of sellable stock value**
from the site at any moment, concentrated in the fast-moving SKUs where stock is tightest.

Rejected. It converts marketing-driven browsing into a stock outage.

## Option B: claim at payment authorisation

What we chose. The customer has committed money; the order exists; the promise is real. The cost is
a 30-minute window in which a payment may still fail, which is handled by expiry plus release.

The one weakness is the gap between authorisation and the reservation being written (about 2
seconds): a second customer can, in theory, quote the same unit in that window. The quote is not a
reservation, so the second customer's reservation fails cleanly rather than overselling, which is
acceptable.

## Option C: claim at the routing run

Today's behaviour, effectively. Routing runs at 00:40 and at peak every hour, so stock stays
unclaimed for up to 14 hours on a website order. This is the direct cause of most oversell and was
rejected without debate.

## Option D: claim at warehouse allocation

The most conservative option: nothing is claimed until a picker starts. It guarantees that we only
promise what a warehouse has accepted, but it means the website can sell the same unit many times
over before the wave is built. It has one attractive property, which is that a reservation can never
be wrong, and one unacceptable one, which is that the customer is told yes when the answer is no.

## What option B does not solve

| Problem | Why B does not fix it | Where it is handled |
| :--- | :--- | :--- |
| Stale feeds | A reservation against stale stock is still wrong | Stale guard, RSV-12 |
| Warehouse cannot find the unit | The claim is in our system, not the warehouse's | Allocation step, RSV-03 |
| Bulky lead times | The claim is right, the date is not | DPS and RSV-06 |
| Marketplace stock pools | Marketplaces reserve nothing | Five-minute push |

## What would change our mind

If oversell stays above 0.8 % for a month with fresh feeds and reservations live, the next lever is
option A restricted to the top 200 SKUs during promotions, which trading already does manually when
it suppresses stock. That would be a change request, not a silent tweak.

## Related

[ADR 0001](../../decisions/0001-reserve-stock-at-payment-authorisation.md) ·
[Policy workshop](./workshop-2026-10-16.md) · [Oversell prevention](../policy/oversell-prevention.md)
