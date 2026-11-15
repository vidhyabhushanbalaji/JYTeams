# Product Page Messaging

Status: In review · Owner: Tom Alder · Last updated: 2026-11-13

The product page is where most promises are made and where most complaints begin. Today it shows a
binary stock flag with no date; from launch it shows stock state and the earliest promised date, with
wording that has been argued over more than the algorithm.

## What appears

| Stock state | Product page shows | Notes |
| :--- | :--- | :--- |
| Available, date known | "Order within 3 h 42 m for delivery by Thu 20 May" | Countdown only when under 6 hours |
| Available, no date | "In stock. Delivery date unavailable right now." | Stale or degraded |
| Low stock (reserved for a future feature) | Not shown this release | CR-008 rejected |
| Pre-order | "Pre-order for release on 2 June" | No delivery date |
| Backorder | "Available from 12 March" | Never a specific day |
| Out of stock | "Out of stock. Notify me when available." | No date |
| Collection available | "Collect from Bristol today, free" | Separate line, store stock |
| Restricted | "Available to collect in store only" | Age or hazard |

## The wording rules

1. **Never a range for a real promise.** "Thu 20 May", not "19–21 May". Ranges appear only in the
   fallback.
2. **Always a day, never a time.** Even for lockers, where the 24-hour clock exists.
3. **Countdown only inside six hours of cut-off**, because a countdown all day trains customers to
   ignore it.
4. **The date must match checkout.** If checkout offers only a later date, the product page was
   wrong; that is a defect, not a copy variation.
5. **Stock is never expressed as a number.** A count invites gaming and creates urgency we do not
   want, and it is factually unreliable while store stock is 91 % accurate.

## Where the date comes from

The page calls `quote` for the default postcode (from the customer's location or a stored address) and
one unit of the product. It does **not** call `quote` per variant, because a variant that changes
weight or warehouse is rare and the burst cost is high; a variant change triggers one additional
quote.

| Cache | TTL | Why |
| :--- | :--- | :--- |
| Page-level quote | 15 s | Burst absorption |
| CDN fragment | 10 s | Avoids a request per render |
| Variant quote | 60 s | Matches availability cache |

## What we changed from the design review

The first mock showed "In stock — arrives Thursday" for everything, which read as though Thursday was
guaranteed. Legal's view was that "arrives" is a stronger claim than the platform can support on a
58 %-accurate bulky segment, so the copy was changed to "delivery by" with the fallback caveat for
any segment below 80 % accuracy. Bulky pages therefore never show a day beyond the 14-day horizon.

## Accessibility

| Requirement | Implementation |
| :--- | :--- |
| Date is not colour-only | Text always present |
| Countdown does not flash | Static text, refreshed every minute |
| Screen reader announcement | `aria-live="polite"` on the date, not the countdown |
| Timezone | Rendered in the customer's locale, no abbreviations |

The countdown was originally an animated element, which failed WCAG 2.2.2 because it could not be
paused. It is now plain text, and the accessibility test in UAT checks exactly that.

## Related

[Basket and checkout](./basket-and-checkout.md) · [Fallback messaging](./fallback-messaging.md) ·
[Accessibility testing](../../customer-testing/non-functional/accessibility-testing.md)
