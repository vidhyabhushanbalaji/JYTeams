# Postcode Lookup

Status: Agreed · Owner: Nadia Kerr · Last updated: 2026-11-06

One call decides whether a customer can have next-day, a locker, a two-person delivery or nothing at
all. It is the highest-traffic carrier call in checkout and the most likely to fail in a way a
customer notices.

## What the lookup returns

| Field | Example | Used for |
| :--- | :--- | :--- |
| `postcode` | `BS1 4DJ` | Display and cache key |
| `region` | `south_west` | Warehouse preference, carrier zone |
| `services[]` | See below | Checkout options |
| `restrictions[]` | `bulky_no_kerbside` | Messaging |
| `store_options[]` | 3 stores | Collection |

Per service:

```json
{ "service": "parcel_next_day", "available": true, "lead_days": 1,
  "saturday": false, "surcharge": 0.00, "cut_off": "12:30" }
```

## Sources and merging

| Carrier | Source | Refresh | Notes |
| :--- | :--- | :--- | :--- |
| Parcelway | Serviceability API | Daily 23:00 | Authoritative per postcode |
| Northline | Weekly zone file | Weekly, Monday | Zone numbers, not postcodes |
| Swiftbox | Locker search API | Real time | Distance-based, not serviceability |
| Own fleet | Not used | — | Store replenishment only |

The service merges three sources into one answer. Where they disagree, the most restrictive wins,
because a promise built on the optimistic source is the one that fails.

## Caching

| Layer | TTL | Key |
| :--- | :--- | :--- |
| In-memory | 10 min | Postcode district (e.g. `BS1`) |
| Redis | 24 h | Full postcode |
| Negative | 1 h | Unserviceable postcode |

Caching by district is a deliberate approximation: carrier zone files are district-level, and
Parcelway's postcode differences inside a district are rare (0.3 % of postcodes). A wrong cached
answer is possible for a newly restricted postcode, which is why Parcelway's daily refresh also
invalidates that district's cache.

## The 1.9 % problem

Some postcodes genuinely cannot receive a bulky delivery: no vehicle access, no safe place for a
two-person drop, or a carrier exclusion. Today the site offers bulky and then the booking fails,
which costs £46 and a phone call. The lookup now returns `bulky_unavailable` with a reason, and the
product page offers collection instead.

| Postcode class | Bulky available | Note |
| :--- | :--- | :--- |
| Standard residential | Yes | 97.1 % of postcodes |
| Flats above 3rd floor, no lift | Yes, kerbside only | Messaging required |
| Islands (HS, ZE, KW15-17) | Yes, 7–10 days | Surcharge |
| Pedestrianised centres | No | Collection only |
| 1.9 % excluded | No | Reason code returned |

## Failure behaviour

| Failure | Behaviour |
| :--- | :--- |
| Parcelway timeout (2 s) | Retry once; then district cache; then standard-only estimate |
| Northline zone file missing | Bulky marked unavailable, parcels unaffected |
| Swiftbox down | Locker option hidden, no error shown |
| All sources down | Standard estimate, labelled, and an alert |

Hiding the locker option when Swiftbox is down is deliberate: customers do not need to know a locker
network exists if we cannot use it today.

## Privacy

The postcode is personal data in combination with an address, and the lookup is logged without the
full postcode: only the district and a hash. That decision is recorded in the DPIA and enforced by
the service, not by convention.

## Related

[Basket and checkout](./basket-and-checkout.md) · [Carrier performance](../carriers/carrier-performance.md) ·
[Security architecture](../../architecture/platform/security-architecture.md)
