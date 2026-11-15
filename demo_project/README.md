# Project Truestock

Status: In delivery · Owner: Priya Raman · Last updated: 2026-11-13

Harbour & Heath sells through five channels, ships from four warehouses and 184 stores, and relies on
three carrier partners plus its own fleet. Today each of those keeps its own idea of what is in stock,
so customers see an "in stock" flag that can be 14 hours old and get a delivery estimate that nobody
can keep. **Truestock is the programme that gives every customer one honest answer: this item is
available, and it will arrive on this date.**

## The problem in numbers

| Measure | Today | Target |
| :--- | :--- | :--- |
| Orders cancelled for want of stock (oversell) | 2.1 % | ≤ 0.4 % |
| Delivery promises kept on the day | 71 % | 92 % |
| Age of the stock figure a customer sees | 30 min – 14 h | ~6 min |
| Store collection cancelled after ordering | 18 % | ≤ 8 % |
| Monthly cost of stock and promise failures | £113,000 | ≤ £25,000 |

## What is being built

Two capabilities and the machinery behind them:

- An **availability service** that computes one sellable number per SKU per warehouse from five stock
  feeds, minus quarantine and minus live reservations.
- A **delivery promise service** that turns that number, a carrier's serviceability and a cut-off time
  into a date the customer can rely on.
- A **reservation policy** that decides when a unit stops being available to everyone else, and what
  happens when the order never completes.

Mercury keeps the orders and routing. Horizon keeps the ledger. Atlas keeps the product data. For the
first time, none of them decides what is in stock.

## Timeline

| Milestone | Date |
| :--- | :--- |
| Discovery and current state | Sep–Nov 2026 |
| Reservation policy signed | 2026-12-04 |
| Feed contracts signed | 2027-01-15 |
| Build complete | 2027-03-19 |
| UAT and customer beta | Apr 2027 |
| Go/no-go | 2027-05-11 |
| Website live | 2027-05-18 |
| All channels live | 2027-06-08 |

## How this documentation is organised

| Area | Read this | Why |
| :--- | :--- | :--- |
| How orders reach warehouses today | [Current state](./current-state/README.md) | The baseline everything is measured against |
| When stock is reserved | [Reservation policy](./reservation-policy/README.md) | The rules the platform implements |
| Warehouse and store stock feeds | [Stock feeds](./stock-feeds/README.md) | Where the number comes from |
| Delivery dates | [Delivery promise](./delivery-promise/README.md) | The customer-facing half |
| Testing, beta and acceptance | [Customer testing](./customer-testing/README.md) | What proves it works |
| Cutover, rollback, hypercare | [Launch readiness](./launch-readiness/README.md) | How it goes live safely |
| How the platform is built | [Architecture](./architecture/README.md) | Services, data, SLOs |
| Why it looks like this | [Decisions](./decisions/README.md) | Ten records with rejected options |
| Vocabulary and field definitions | [Reference](./reference/glossary.md) | Terms, data dictionary, APIs |

## Who is who

| Role | Name |
| :--- | :--- |
| Sponsor | Rachel Okonjo, Chief Customer Officer |
| Programme lead | Priya Raman |
| Product owner | Tom Alder |
| Head of fulfilment (policy owner) | Sofia Mendes |
| Integration lead | Dan Whitcombe |
| QA lead | Aisha Bello |
| Platform engineering lead | Nadia Kerr |
| Customer operations | Marcus Feld |

## The three rules this programme runs on

1. **A date must be defensible.** If it cannot be built from fresh stock, a cut-off and a carrier's
   serviceability, we show a range and say we will confirm, rather than guessing.
2. **Every release has a reason.** Reservations are released with one of eight reason codes, because a
   warehouse needs to know why stock reappeared.
3. **Nothing silent.** Feed failures, reservation stops and promise drops all alert; the alternative is
   discovering them from a customer complaint.

## Status of the documentation

| Section | State |
| :--- | :--- |
| Programme, current state | Agreed and signed off |
| Reservation policy | In review: two rules open (RSV-06, RSV-11) |
| Stock feeds, delivery promise | Drafts, contracts not yet signed |
| Customer testing, launch | Draft plans, nothing executed until 2027 |
| Architecture, decisions, reference | Draft, updating weekly |

Two policy rules are deliberately unresolved. They are written up with their options rather than
silently decided, because both change what the build must do.

## Related

[Risk register](./programme/governance/risk-register.md) · [Latest status](./programme/status/2026-11-13-status.md) ·
[Glossary](./reference/glossary.md)
