# Horizon ERP

Status: Agreed · Owner: Ben Osei · Last updated: 2026-11-03

Horizon is the finance and stock ledger system: it holds the accounting value of stock, purchase
orders, goods-in records and the monthly close. It runs as a managed SaaS instance and is the only
system finance will accept as the truth for stock value.

## What it holds

| Area | Detail |
| :--- | :--- |
| Stock ledger | Value and quantity by SKU, location and cost layer |
| Purchase orders | Raised by buying, received at warehouses |
| Goods-in | Booked by warehouse teams, three-way matched |
| Costing | Weighted average, recalculated nightly |
| Month-end | Close on working day 4, with a hard lock |

## Stock movements it expects

| Movement | Source | Timing |
| :--- | :--- | :--- |
| Goods-in | Warehouse goods-in system | Real time to Horizon via Orbit |
| Sale | Mercury dispatch | Nightly batch at 01:00 |
| Return | Mercury returns record | Nightly batch |
| Adjustment | Mercury adjustment | Nightly batch |
| Transfer | Store or warehouse transfer | Nightly batch |
| Write-off | Warehouse damage record | Weekly batch |

## Why there is a disagreement every morning

Mercury's stock number and Horizon's stock number differ by between 0.4 % and 1.8 % on any given
morning. The gap is the day's movements that Horizon has not posted yet, plus adjustments that were
made in Mercury without a matching Horizon document. Finance tolerates it because the month-end
reconciliation clears it; operations does not, because the website is fed from Mercury.

Truestock makes this visible rather than worse: the availability service reads feed data and
reservations, and it does not read Horizon at all. The reconciliation document in
[stock feeds](../../stock-feeds/reliability/reconciliation.md) explains how the three numbers are
kept explicable.

## Constraints

| Constraint | Effect |
| :--- | :--- |
| No real-time stock API exposed | Horizon cannot be an availability source |
| Nightly posting only | A same-day correction never reaches Horizon before 01:00 |
| Cost layers recomputed nightly | Mid-day margin reporting is approximate by design |
| Month-end lock | No stock movement can post on working days 4–6 |

## What changes under Truestock

Nothing in Horizon for this release. One thing is agreed for after peak: reservations will be
posted to Horizon as a memorandum quantity so finance can see committed-but-not-dispatched stock
without changing the ledger. That work is deliberately out of scope for 18 May.

## Related

[Mercury OMS](./mercury-oms.md) · [Reconciliation](../../stock-feeds/reliability/reconciliation.md) ·
[DEP-05 in dependencies](../../programme/plan/dependencies.md)
