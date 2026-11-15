# 0008 — Retain Mercury as the Order System

Status: Accepted · Date: 2026-09-18 · Deciders: Priya Raman, Iain McCrae, Ben Osei

## Context

Mercury is 11 years old, runs on one SQL Server instance, has no real-time stock API and is supported by
two contractors after the vendor disappeared. It was the obvious thing to replace, and replacing it would
have doubled the programme.

## Options

| Option | Time | Risk | Cost |
| :--- | :--- | :--- | :--- |
| A. Keep Mercury, add events | 9 months | Contained | £1.41 m |
| B. Replace Mercury with a new OMS | 24+ months | Very high | £4–6 m |
| C. Replace routing only | 12 months | High | £2.2 m |
| D. Keep Mercury, patch the stock procedure | 3 months | Fails the goal | £0.4 m |

## Decision

Keep Mercury as the **order and routing system** for this release. It gains one outbound event
(`order.placed`) and the ability to ask ATP for availability. It stops being the system of record for
availability.

## Why not replace it

Not because Mercury is good, but because replacing it and fixing the promise in one programme would
deliver neither on time. Option B's estimate assumes a stable order model, and Mercury's routing rules
are undocumented folklore that would have to be reverse-engineered before it could be replaced.

## Consequences

| Easier | Harder |
| :--- | :--- |
| Launch in May 2027 | Two systems hold stock-related data |
| Order capture and routing unchanged | Mercury's stored procedures stay untested |
| Rollback can restore the old behaviour | Reconciliation between three numbers is permanent |
| Budget stays credible | Routing improvements are limited to better inputs |

## The cost we accepted

The daily Mercury-to-Horizon gap of 0.4–1.8 % remains, and finance will keep reconciling it by hand. That
cost is £0 in engineering and about 45 minutes a day in finance, and it was accepted explicitly rather
than overlooked.

## Revisit

After peak, if the platform team has capacity, the routing rules are the next candidate: they are the
part of Mercury with the clearest business case for replacement, and they would be replaced behind the
same ATP interface.

## Related

[Mercury OMS](../current-state/systems/mercury-oms.md) ·
[Reconciliation](../stock-feeds/reliability/reconciliation.md) ·
[Horizon ERP](../current-state/systems/horizon-erp.md)
