# 0004 — Poll Marketplace Inventory Every Five Minutes

Status: Accepted · Date: 2026-10-16 · Deciders: Tom Alder, Kelvin Adu, Dan Whitcombe

## Context

Marketplace stock is pushed every 30 minutes from a Mercury extract that can be 40 minutes old, so the
true age of an Amazon quantity is 30–70 minutes. Two Amazon warnings in 2026 came within four units of a
suspension, and trading suppresses stock before promotions as a workaround, 14 times in two months.

## Options

| Option | Freshness | Risk |
| :--- | :--- | :--- |
| A. Five-minute push from ATP | 5 min | API quota must be raised |
| B. Keep 30 minutes, reserve more conservatively | 30 min | Loses sales on every SKU |
| C. Push on every stock change | ~1 s | Rate limits would be exceeded within a minute |
| D. Sell only in marketplaces we can guarantee | 30 min | Cedes 34 % of volume |

## Decision

Push marketplace inventory **every five minutes from ATP**, with unreserved stock, and raise the API
quota (DEP-06) as a prerequisite rather than an optimisation.

## Why not push-on-change

It looks like the natural event-driven answer and it is unusable: the top 200 SKUs change thousands of
times an hour, and ChannelBridge already throttles at 220 calls a minute during promotions. Five minutes
is the fastest cadence the quotas allow at our SKU count.

## Consequences

| Easier | Harder |
| :--- | :--- |
| Marketplace age drops from 70 to 5 minutes | Quota becomes a launch dependency |
| Promotional suppression can stop | A marketplace oversell is still possible inside the window |
| One number for website and marketplaces | Push failures need their own alerting |
| Trading regains revenue currently suppressed | Buffer must remain until feeds prove themselves |

## The buffer stays

We keep a conservative marketplace buffer through hypercare. The five-minute push reduces the window;
it does not eliminate it, and Amazon does not distinguish between "our feed was late" and "we oversold".

## Related

[Marketplace stock display](../customer-testing/test-cases/marketplace-stock-display.md) ·
[Marketplaces](../current-state/channels/marketplaces.md) ·
[DEP-06](../programme/plan/dependencies.md)
