# Beta Scripts

Status: Draft · Owner: Tom Alder · Last updated: 2026-11-13

Beta customers are not given scripts; they are given six **suggestions** and a support number. This
document is for the support team: what to ask, what to watch, and which journeys must be exercised for
the beta to be worth running.

## The six journeys

| ID | Journey | What it exercises | Suggested to |
| :--- | :--- | :--- | :--- |
| BJ-01 | One small item, next-day | The basic promise and the cut-off | Everyone |
| BJ-02 | Two items from different warehouses | Split shipment, two dates | Frequent customers |
| BJ-03 | One bulky item | Two-person slot and the date range | 20 % of cohort |
| BJ-04 | Collection from a store | Store reservation and pick task | Collection users |
| BJ-05 | Cancel before dispatch | Release and refund path | Everyone, once |
| BJ-06 | Change delivery address before dispatch | Fraud rules and re-promise | As needed |

BJ-03 is suggested rather than required because bulky items are expensive and the cohort has only 19
expected bulky orders. Pushing harder would distort the sample.

## What support asks

| Moment | Question |
| :--- | :--- |
| Order placed | "Did the delivery date you saw make sense?" |
| Date changed | "Were you told before you noticed?" |
| Delivery completed | "Did it arrive when we said?" |
| Any contact | "What were you expecting to see?" |

Support records the answer verbatim in the beta log. The verbatim quotes are the most useful output of
the whole exercise, because they reveal the mental model, not just the outcome.

## What to watch on each journey

| Journey | Watch for |
| :--- | :--- |
| BJ-01 | Countdown confusion; whether the date matched the confirmation email |
| BJ-02 | Surprise at two parcels; whether the second date was understood |
| BJ-03 | The range instead of a day; the slot booking call |
| BJ-04 | "Ready" email timing; store finding the item |
| BJ-05 | Refund timing; whether the date disappeared cleanly |
| BJ-06 | Re-promise accuracy after an address change |

## Observation checklist

- [ ] Customer can state the promised date back to us unprompted
- [ ] Customer knows whether the order will arrive in one or two parcels
- [ ] Customer knows what happens if the date changes
- [ ] Customer can find the collection instructions without help
- [ ] Customer is not surprised by the fallback message, if shown

The first item is the real test of the messaging. If a customer cannot repeat the date, the promise
did not land, whatever the API returned.

## What we do not ask

We do not ask customers to test failure modes, and we do not tell them which journeys are new. A
customer who is looking for problems behaves differently from one who is shopping, and the beta is
valuable precisely because they are shopping.

## Related

[Beta cohort](./beta-cohort.md) · [Feedback survey](./feedback-survey.md) ·
[Product page messaging](../../delivery-promise/customer-messaging/product-page-messaging.md)
