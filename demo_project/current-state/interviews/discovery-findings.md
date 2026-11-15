# Discovery Findings

Status: Agreed · Owner: Priya Raman · Last updated: 2026-11-06

47 interviews across channels, warehouses, stores, contact centre, finance and technology, plus
four weeks of order and call data. This is the summary that closed M1; the full notes are in the
files beside it.

## Five findings

### 1. Stock is a number copied between six systems, and nobody owns it

There are six stock quantities for the same SKU: Mercury, Horizon, each warehouse system, each
marketplace, and the store file. They are reconciled nightly by a person, and the process works
only because the differences are small enough to absorb.

**Evidence:** the morning gap between Mercury and Horizon is 0.4–1.8 %; 14 manual adjustment jobs a
day; 2.1 % oversell.

### 2. The promise is made by whoever is talking to the customer

The website shows a flag, the confirmation email shows a range, the contact centre says "three to
five days", and the carrier says something else again. Four promises, one order.

**Evidence:** 31 % of stock-related calls quote our own promise back at us; promise accuracy 71 %.

### 3. Warehouse reality arrives late, and by then it is history

Allocation happens at wave build (12:30), not at order time. Between those two points the system
believes stock is available when it is physically committed.

**Evidence:** supervisor interviews at three sites; 190 phantom-stock incidents a day.

### 4. The failures are individually correct

Every failure we investigated was a sequence of steps that each did what it was told. The pallet in
quarantine, the Amazon pending order, the dead-letter order: no single step was wrong, and no single
person could see the whole path.

**Evidence:** F-04, F-05 and the August quarantine incident.

### 5. Nobody trusts the number, so everybody buffers it

Trading suppresses stock before promotions. The website hides anything below five units. Stores
keep a shelf buffer. Each buffer is rational, and together they hide 6–9 % of sellable stock.

**Evidence:** 14 promotional suppressions in two months; the five-unit product-page buffer.

## What surprised us

| Surprise | Why it matters |
| :--- | :--- |
| The warehouse 15:00 cut-off is really 12:30 | Every promise built on 15:00 over-promises by 2.5 hours |
| Store stock is 91 % accurate, not 80 % | Better than feared, but concentrated in scanner-less stores |
| Bulky goods are the worst segment at 58 % | The smallest volume is the largest reputational risk |
| Wholesale is the most manual and the least complained about | Trade customers absorb partial fulfilment; consumers do not |
| Orbit's dead-letter folder has 3,100 unread messages | Silent failure is the norm, not the exception |

## What we deliberately are not fixing

- Mercury's routing rules, beyond giving routing better availability data.
- The Horizon ledger design and the daily reconciliation gap.
- Wholesale backorder allocation and price list consolidation.
- Store stock accuracy, beyond the hourly feed and the device rollout.

Each of these is real and none of them is required to keep the promise we are making in May.

## How the findings became the plan

| Finding | Response |
| :--- | :--- |
| 1 | Central availability service with a reservation ledger |
| 2 | One promise service, one date, used by every channel |
| 3 | Reservation at payment, not at wave build |
| 4 | Event stream with dead-letter alerting and a reason code on every change |
| 5 | Remove the buffers only after feeds prove themselves; policy decides when |

## Related

[Channel operations interview](./channel-operations-interview.md) ·
[Known failures](../order-flow/known-failures.md) ·
[Reservation policy](../../reservation-policy/README.md)
