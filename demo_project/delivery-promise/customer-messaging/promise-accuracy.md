# Promise Accuracy

Status: Agreed · Owner: Gavin Shore · Last updated: 2026-11-13

The one number that says whether the programme worked. Promise accuracy is the share of orders
delivered on the date we gave, measured per service and reported weekly.

## Definition

An order is **accurate** when the parcel is delivered on the promised day. With a one-day tolerance,
noted separately, because carrier problems are sometimes outside our control.

| Metric | Definition | Target |
| :--- | :--- | :--- |
| Strict accuracy | Delivered on the promised day | 92 % by 2027 Q4 |
| Tolerant accuracy | Delivered within ±1 day | 96 % |
| Early delivery | Delivered before the promised day | Reported, not penalised |
| Fallback rate | Orders with no date | ≤ 1 % |
| Wrong-promise rate | Date changed after purchase | ≤ 3 % |

Early delivery is not a failure: a customer told Thursday who receives Wednesday is pleased, although
it does make the warehouse look unpredictable. It is reported so that a systematic early pattern can
be found, usually a cut-off that is too conservative.

## Baseline (October 2026)

| Service | Orders | Strict | Tolerant | Note |
| :--- | :--- | :--- | :--- | :--- |
| Next Day | 3,910/day | 84.1 % | 92.8 % | Most measured, most reliable |
| Standard | 1,660/day | 79.2 % | 90.1 % | Two-day service drifts to three |
| Locker | 830/day | 91.3 % | 96.0 % | Most predictable |
| Bulky | 410/day | 57.6 % | 74.3 % | Slot unavailable inside the promise |
| Collection | 1,100/day | 68.2 % | — | "Ready" measured separately |
| **Overall** | **7,910/day** | **71.0 %** | **85.6 %** | Weighted |

Collection accuracy means "ready when we said", which is why it has no tolerance column: an item is
ready or it is not.

## How it is measured

| Step | Source |
| :--- | :--- |
| Promised date | Reserved from the order record at purchase |
| Actual delivery | Carrier tracking events, or store collection scan |
| Match | Day comparison in UK time, not UTC |
| Attribution | Service, warehouse, carrier, postcode district |

The promised date is captured **at the moment of purchase** and never recomputed, so a later change
to the algorithm cannot retrospectively improve the score. Comparisons against a re-run calculation
are kept separately as a "would-be" metric for product decisions.

## Diagnostics

| Dimension | Why it is sliced this way |
| :--- | :--- |
| Warehouse | A feed problem shows up as a warehouse-specific miss |
| Carrier | A capacity problem shows up as a carrier-specific miss |
| Service | Bulky and standard behave differently |
| Day of week | Monday orders are worse; Sunday collections do not exist |
| Postcode district | Reveals serviceability errors |
| Hour of order | Reveals cut-off errors |

The hour-of-order slice is how the 12:30 cut-off issue was found: every order between 12:30 and 15:00
was promised next-day and missed, a clean 2.5-hour band of failure.

## Reporting rhythm

| When | What | Audience |
| :--- | :--- | :--- |
| Daily | Yesterday's accuracy by service | Operations |
| Weekly | Seven-day rolling, by warehouse and carrier | Programme, carriers |
| Monthly | Full scorecard with actions | Steering group |
| Post-launch | Daily for four weeks of hypercare | Everyone |

## The 92 % target

Set by the steering group in September 2026, against a 71 % baseline and a 96 % aspiration for
parcels alone. It is deliberately not 96 % overall, because bulky goods and collection cannot reach
that on the current carrier network, and a target nobody believes is worse than a demanding one.

## Related

[Service levels](../calculation/service-levels.md) · [Carrier performance](../carriers/carrier-performance.md) ·
[UAT exit criteria](../../customer-testing/uat/entry-and-exit-criteria.md)
