# Store Stock Network

Status: In review · Owner: Elena Vasquez · Last updated: 2026-11-13

184 stores holding about 22 % of stock by value, published as one nightly CSV. This is the largest
file, the least frequent feed and the only one where the data is wrong often enough to change the
promise we make.

## The file

| Property | Today | Target from 2027-02 (CR-007) |
| :--- | :--- | :--- |
| Format | CSV over SFTP | CSV over SFTP |
| Size | 41,000 lines, ~41 MB | Same |
| Cadence | Nightly at 23:30 | Hourly at :10 |
| Records | One row per store per SKU | Same |
| Transfer time | 3 min | 3 min |
| Load time in Mercury | 9 min | 4 min (new ingestor) |
| Stale threshold | 90 min | 90 min |

## Columns

| Column | Meaning | Use |
| :--- | :--- | :--- |
| `STORE_ID` | Store code, e.g. `HH-0142` | Join key |
| `SKU` | Product code | Join key |
| `QTY` | Quantity on hand | Base quantity |
| `LAST_COUNTED_AT` | When a human last verified it | Confidence signal |
| `DISCONTINUED` | Store has stopped ranging the SKU | Exclude (ISSUE-025) |
| `DAMAGED` | Written-off units still on the shelf | Subtracted |

## Why accuracy is 91 %

The audit of 1,240 store counts found four causes, and only one of them is a systems problem:

| Cause | Share | Fix |
| :--- | :--- | :--- |
| Case-level goods-in, single-unit sales | 41 % | Handheld scanners (2,400 devices in 2027) |
| Theft and damage not written off | 28 % | Daily damage sweep, plus the `DAMAGED` column |
| Transfers recorded one-sided | 22 % | Transfer confirmation task in StoreStock |
| Returns shelved without an entry | 9 % | Returns scan step |

The hourly feed makes errors **visible sooner**, not smaller. That distinction matters for the
launch plan: collection promise accuracy is expected to improve from 68 % to 79 % on the hourly
feed alone, and to 88 % only after the scanners land in Q3 2027.

## Data quality traps

| Trap | Detail | Handling |
| :--- | :--- | :--- |
| Discontinued SKUs | 6,400 rows for products stores no longer range | Excluded (ISSUE-025) |
| `LAST_COUNTED_AT` older than 90 days | 31 % of rows | Flagged; collection promise suppressed for those rows |
| Duplicate store codes | 2 codes used by closed stores | Ignored, estate list is authoritative |
| Zero-quantity rows | 62 % of the file | Kept; needed to know a store does not have it |

The third row is smaller than it looks: closed stores keep sending until someone stops them, and two
did for eleven months in 2025.

## Why hourly, not real time

Stores do not have a real-time integration and StorePOS writes locally. Hourly is the fastest the
current estate can support, and CR-007 was approved on that basis with an 11-day estimate. Real
time would need every store online continuously, which the estate is not.

## Effect on the promise

| Promise | Today | Hourly feed |
| :--- | :--- | :--- |
| Collection availability | Nightly, 9 % wrong | Hourly, 9 % wrong but discovered sooner |
| Collection cancellation within 1 hour | 22 % of failures | 70 % of failures |
| Delivery from store stock | Not offered | Offered for scanner-equipped stores from June |

## Related

[Store channel](../../current-state/channels/stores.md) · [Store collection](../../reservation-policy/edge-cases/store-collection.md) ·
[Delta and snapshot](../protocol/delta-and-snapshot.md)
