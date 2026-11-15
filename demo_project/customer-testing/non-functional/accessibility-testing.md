# Accessibility Testing

Status: Agreed · Owner: Tom Alder · Last updated: 2026-11-06

The new promise adds a date to every product page, which is the single most important accessibility
surface we touch. Target is WCAG 2.2 AA, and the test plan is deliberately narrow: the screens we
changed, tested properly.

## Scope

| Screen | Change | Tested |
| :--- | :--- | :--- |
| Product page | Date, countdown, stock state | Yes |
| Basket | Delivery groups and dates | Yes |
| Checkout | Service list, dates, collection | Yes |
| Order confirmation | Per-shipment dates | Yes |
| Order tracking | Promise and changes | Yes |
| Store collection page | Ready time, instructions | Yes |
| Postcode lookup | Error messages, autocomplete | Yes |

## The criteria that caused work

| Criterion | Issue found | Fix |
| :--- | :--- | :--- |
| 1.4.3 Contrast | Date text at 3.9:1 on the pale background | Darkened to 5.4:1 |
| 2.2.2 Pause, stop, hide | Countdown animated and could not be paused | Static text, refreshed per minute |
| 2.4.4 Link purpose | "See delivery options" repeated five times | Added product context to the label |
| 3.3.1 Error identification | Postcode failure used colour only | Text explanation added |
| 3.3.2 Labels | Locker option used a placeholder as a label | Proper label element |
| 4.1.3 Status messages | Date update not announced | `aria-live="polite"` on the date region |
| 1.4.4 Resize text | Delivery group table overflowed at 200 % | Responsive stacking |

The countdown was the most significant change: an animated element that cannot be paused fails the
criterion outright, and it is easy to miss because the animation looks decorative.

## How it is tested

| Method | Tool or person | Frequency |
| :--- | :--- | :--- |
| Automated scan | axe-core in CI | Every commit |
| Keyboard only | Aisha Bello, 90 minutes | Each release candidate |
| Screen reader | NVDA on Windows, VoiceOver on Safari | Each release candidate |
| Zoom and reflow | 200 % and 400 %, 320 px width | Each release candidate |
| Cognitive review | Contact centre team, plain-English check | Once before UAT |
| Real users | Four customers with access needs, April | Once |

The real-user session is the part most programmes skip and it is the part that finds the problems
automated tools cannot: whether "delivered by Thursday" is a sentence a screen-reader user can act
on.

## Plain language

The date copy was reviewed for readability with the contact centre team, who are the closest thing we
have to plain-language experts. Two changes came out of it:

| Before | After |
| :--- | :--- |
| "Delivery available from 20/05" | "Delivery by Thursday 20 May" |
| "Serviceability unavailable" | "We cannot deliver to this postcode" |

## What we are not doing

| Not doing | Why |
| :--- | :--- |
| Full estate accessibility audit | The store estate is a separate programme |
| AAA | Not required, and the contrast target would constrain brand colours |
| Native app testing | There is no app |
| PDF accessibility | We do not publish PDFs to customers |

## Sign-off

Accessibility is checked before UAT exit, and the checker is not the person who wrote the frontend.
Two issues remain open at time of writing, both colour-related and both scheduled for the February
release.

## Related

[Product page messaging](../../delivery-promise/customer-messaging/product-page-messaging.md) ·
[UAT exit criteria](../uat/entry-and-exit-criteria.md) ·
[Test strategy](../strategy/test-strategy.md)
