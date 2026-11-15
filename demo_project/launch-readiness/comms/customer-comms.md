# Customer Comms

Status: Draft · Owner: Jo Bell · Last updated: 2026-11-13

What customers are told before, during and after launch. The principle is that the promise should be
visible in the product rather than announced in a campaign, so there is no "exciting news" email.

## What customers experience

| Moment | What they see | Changed? |
| :--- | :--- | :--- |
| Product page | A delivery date instead of an in-stock flag | Yes |
| Basket | Delivery groups and dates | Yes |
| Checkout | Only services that can be delivered | Yes |
| Confirmation | Per-shipment dates | Yes |
| Dispatch | Same emails, per parcel | No |
| Delivery | Same carrier experience | No |

The promise is a product change, not a marketing one. Tom Alder's position, accepted by trading, is
that announcing a "new delivery promise" before it has proven itself invites scrutiny of every late
parcel, while showing it silently lets the experience speak.

## Communications that do go out

| Audience | Message | Channel | When |
| :--- | :--- | :--- | :--- |
| Beta cohort | Invitation and joining instructions | Email | 2027-03-25 |
| Beta cohort | Thank you and what changed | Email | 2027-04-27 |
| All customers | Delivery page updated with how dates work | Help centre | 2027-05-18 |
| Affected customers | Date change notifications | Email | Ongoing |
| Customers in an incident | Apology and corrected date | Email | As needed |

The third row is the only public-facing explanation: a help-centre page titled "How we calculate your
delivery date", updated on launch day. It exists so that colleagues and customers have one link to
share.

## Incident comms

| Scenario | Message | Owner | Timing |
| :--- | :--- | :--- | :--- |
| Dates unavailable for a warehouse | "Some delivery dates are temporarily unavailable" banner | Tom Alder | Within 1 hour |
| Order dates changed | Email with old and new date | Jo Bell | Within 4 hours |
| Oversell and cancellation | Personal email and a call for orders over £200 | Marcus Feld | Within 2 hours |
| Rollback | No announcement; behaviour reverts quietly | — | — |
| Store collection failure | "We could not find your item" plus refund | Jo Bell | Within 30 minutes |

The store collection timing is the tightest because the customer may already be on their way.

## Tone

| Do | Do not |
| :--- | :--- |
| "Your order will arrive on Thursday 20 May" | "Your order should arrive around Thursday" |
| "We cannot confirm a date right now" | "An error occurred" |
| "We are sorry, this item is no longer available" | "Unfortunately your item is unavailable due to system issues" |
| Say what happens next | Blame a carrier or a system |

The last prohibition matters: blaming a carrier is factually tempting and commercially self-harming,
since the carrier is the one holding the parcel.

## Approval

| Message type | Approver |
| :--- | :--- |
| Standard product copy | Tom Alder |
| Incident message, existing template | Tom Alder |
| New incident wording | Tom Alder plus Leah Okafor |
| Compensation offer | Marcus Feld plus finance |
| Anything mentioning a security incident | Leah Okafor plus Iain McCrae |

## Templates

Templates live with the runbooks, so an on-call engineer at 02:00 does not have to write copy. Each
template has placeholders only for the order number, the old date and the new date, and nothing else.

## Related

[Fallback messaging](../../delivery-promise/customer-messaging/fallback-messaging.md) ·
[Runbooks](../runbooks/runbook-index.md) · [Beta cohort](../../customer-testing/beta/beta-cohort.md)
