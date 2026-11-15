# Delivery Promise Service

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Turns availability into a date. It holds the calendar, the cut-offs, the carrier rules and the buffer
policy, and it stores every date it has ever promised.

## Responsibilities

| Does | Does not |
| :--- | :--- |
| Compute a date per shipment | Know stock counts |
| Call carrier serviceability, cached | Book deliveries |
| Apply calendar and buffers | Edit orders |
| Store the promise with its inputs | Change a promise after issue |

## Calculation order

1. Serviceability for the postcode (cached 24 h per full postcode).
2. Eligible services by size, weight and product restrictions.
3. Warehouse cut-off for the chosen service.
4. Lead time in working days from the calendar.
5. Horizon check for bulky (14 days).
6. Buffer for bank holiday weeks.
7. Round to a day in the customer's timezone.

The full logic, with worked examples, is in
[delivery date logic](../../delivery-promise/calculation/delivery-date-logic.md).

## Inputs and their failure modes

| Input | Source | Failure behaviour |
| :--- | :--- | :--- |
| Serviceability | Carrier API, Redis cache | Cached district answer, then fallback |
| Cut-off | Configuration | Alert; no date if missing |
| Calendar | Calendar table, cached 24 h | Fail closed if older than 24 h |
| Stock age | ATP response | Included in the stored promise |
| Restrictions | Atlas, cached 1 h | Conservative: treat as restricted |

"Fail closed" means no date. A date computed without a calendar is a date that promises delivery on
Christmas Day.

## Stored promise

| Field | Why stored |
| :--- | :--- |
| `promised_date` | Accuracy is measured against what was said |
| `assumed_stock_age_seconds` | Traces a wrong promise to the figure behind it |
| `fallback_used` and reason | Counts the fallback rate |
| `service` | Accuracy by service |
| `supersedes_id` | Date changes are new records, not edits |

## Caching

| Item | TTL | Why |
| :--- | :--- | :--- |
| Serviceability per postcode | 24 h | Carrier data changes daily |
| Calendar | 24 h | Changes rarely, fail closed if old |
| Promise per basket signature | 60 s | Repeated checkout renders |

## Failure behaviour

| Failure | Result |
| :--- | :--- |
| Carrier down | Cached serviceability, then fallback |
| Calendar missing | No date, alert |
| Bulky beyond horizon | Week commencing |
| Any unexpected error | Fallback estimate, logged with reason |

## Metrics

| Metric | Alert at |
| :--- | :--- |
| Promise p95 | 250 ms (cache miss) |
| Fallback share | Above 3 % for 30 min |
| Serviceability error rate | Above 2 % |
| Promises per minute | Drop of 50 % vs the same hour last week |

The fourth catches a silent failure where promises simply stop being created, which no error rate
would show.

## Related

[Delivery promise API](../../reference/api/delivery-promise-api.md) ·
[Service levels](../../delivery-promise/calculation/service-levels.md) ·
[Event flows](../event-flows.md)
