# Interview — Contact Centre

Status: Agreed · Owner: Marcus Feld · Last updated: 2026-10-21

Interview with **Nadia Suleiman**, contact centre team leader (customer, not to be confused with
Nadia Kerr in engineering), on 2026-10-19, 50 minutes, remote. Supported by a review of 400 call
transcripts from September 2026.

## Call mix, September 2026

| Category | Share | Volume | Notes |
| :--- | :--- | :--- | :--- |
| Where is my order | 22 % | 3,960 | Most mention the promised date |
| Item not in stock after ordering | 9 % | 1,620 | Almost always the website's fault |
| Collection order not found in store | 7 % | 1,260 | Highest complaint rate |
| Delivery date changed after ordering | 6 % | 1,080 | Usually bulky goods |
| Returns and refunds | 31 % | 5,580 | Outside this programme |
| Other | 25 % | 4,500 | — |

**31 % of calls** in the stock-related categories start with the customer quoting a date or an
"in stock" message from our own website. That is the number the programme is judged on.

## What they said

> "We are not allowed to promise a date on the phone, because the website's date is different from
> the one the warehouse gives us. So we say 'usually three to five days' and the customer hears
> 'three days'." — Nadia

> "When a collection order fails, the store usually knows before we do. The customer calls us
> because nobody called them."

## The two scripts that exist

| Script | Used for | Problem |
| :--- | :--- | :--- |
| "Your order is being prepared" | Any delay under 48 hours | Says nothing about the date |
| "We are sorry, the item is unavailable" | Oversell and phantom stock | Offers a refund only; no alternative |

Agents have written their own third script, an informal one, which offers to check another store.
It is not approved and it works, which tells you what the approved scripts are missing.

## What they want

1. A single date they can quote, the same one the customer saw.
2. A proactive notification when the date changes, before the customer calls.
3. For collection, a call or message when the store cannot find the item, within 30 minutes.

The second is CR-009, currently in review. The third is a manual process in the hypercare plan
because it needs an integration with the store task list that does not exist yet.

## What they fear

That the new system will be accurate but less forgiving: "If the system says Thursday and it turns
up Friday, that is worse than 'three to five days', because now it is a broken promise rather than
an estimate." This is the reasoning behind the conservative fallback in
[ADR 0010](../../decisions/0010-conservative-fallback-promise.md) and the ±1 day tolerance in the
promise accuracy metric.

## Related

[Discovery findings](./discovery-findings.md) · [Promise accuracy](../../delivery-promise/customer-messaging/promise-accuracy.md) ·
[Fallback messaging](../../delivery-promise/customer-messaging/fallback-messaging.md)
