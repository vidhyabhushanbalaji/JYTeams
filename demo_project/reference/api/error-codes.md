# Error Codes

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

Every error the platform returns, what it means, and what the caller should do. A code that is not in
this table should not exist; if one appears in a log, that is a defect.

## Availability and reservations

| Code | HTTP | Meaning | Caller action |
| :--- | :--- | :--- | :--- |
| `ATP_STOCK_STALE` | 409 | No contributing feed is fresh enough | Show fallback; do not reserve |
| `ATP_INSUFFICIENT_STOCK` | 409 | Fewer units than requested | Offer partial options |
| `ATP_UNKNOWN_SKU` | 404 | SKU not in Atlas | Treat as unavailable |
| `ATP_LOCATION_UNAVAILABLE` | 409 | Warehouse on hold | Retry other locations |
| `ATP_RESERVATION_EXPIRED` | 410 | Reservation no longer valid | Re-quote and re-reserve |
| `ATP_NO_SERVICE` | 409 | No carrier serves the postcode | Offer collection |
| `ATP_RATE_LIMITED` | 429 | Caller over quota | Back off using `Retry-After` |
| `ATP_INVALID_QUANTITY` | 422 | Zero or negative quantity | Fix the request |

## Feeds

| Code | HTTP | Meaning | Caller action |
| :--- | :--- | :--- | :--- |
| `FEED_CURSOR_MISMATCH` | 409 | Unknown starting point | Wait for the snapshot |
| `FEED_BATCH_INCOMPLETE` | 422 | Record count mismatch | Re-send the batch |
| `FEED_SCHEMA_INVALID` | 422 | Missing field or wrong type | Fix the source; do not retry |
| `FEED_UNKNOWN_LOCATION` | 422 | Location not configured | Fix the mapping |
| `FEED_SIGNATURE_INVALID` | 401 | Bad signature or stale timestamp | Re-sign |
| `FEED_TOO_LARGE` | 413 | Over 250,000 records or 200 MB | Split the batch |
| `FEED_MAINTENANCE` | 503 | Declared maintenance window | Wait; do not alert |

`FEED_MAINTENANCE` is deliberately distinct from an error: a declared window is expected and must not
trigger the same alerting as a failure.

## Promise

| Code | HTTP | Meaning | Caller action |
| :--- | :--- | :--- | :--- |
| `PROMISE_UNAVAILABLE` | 409 | No date can be defended | Use the fallback |
| `PROMISE_OUTSIDE_HORIZON` | 422 | Bulky beyond 14 days | Show a week |
| `PROMISE_SHIPMENT_DISPATCHED` | 409 | Too late to recalculate | Do not change |
| `PROMISE_CALENDAR_STALE` | 503 | Calendar older than 24 hours | Fail closed |

## Carrier

| Code | HTTP | Meaning | Caller action |
| :--- | :--- | :--- | :--- |
| `CARRIER_TIMEOUT` | 504 | Carrier did not answer in time | Use cached serviceability |
| `CARRIER_UNAVAILABLE` | 503 | Carrier is down | Withdraw the service |
| `CARRIER_REJECTED` | 422 | Booking refused (capacity, size) | Rebook or reroute |
| `CARRIER_AUTH` | 502 | Credential rejected | Alert; credential rotation |

## Platform

| Code | HTTP | Meaning |
| :--- | :--- | :--- |
| `PLATFORM_DEGRADED` | 503 | A dependency is unhealthy; partial service |
| `PLATFORM_RATE_LIMITED` | 429 | Infrastructure throttling |
| `PLATFORM_UNAUTHORISED` | 401 | Missing or invalid identity |
| `PLATFORM_FORBIDDEN` | 403 | Identity not permitted for this resource |

## Conventions

| Rule | Detail |
| :--- | :--- |
| Codes are stable | The meaning may be refined; the code never changes |
| Bodies are structured | `{ "code": "...", "message": "...", "retryable": true }` |
| `retryable` is authoritative | A caller does not need to infer from the status code |
| Messages are for engineers | Customer-facing copy lives in the storefront |
| Codes are logged | Every occurrence is counted, which is how alerts are built |

## What each caller should never do

| Caller | Never |
| :--- | :--- |
| Storefront | Retry a 409 in a loop |
| Marketplace adapter | Treat `ATP_STOCK_STALE` as zero stock |
| Warehouse | Retry a 422 |
| Internal service | Swallow a `PROMISE_CALENDAR_STALE` |

## Related

[ATP service contract](../../reservation-policy/specification/atp-service-contract.md) ·
[Availability API](./availability-api.md) · [Feed contracts](../../stock-feeds/protocol/feed-contracts.md)
