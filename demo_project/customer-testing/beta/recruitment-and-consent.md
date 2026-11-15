# Recruitment and Consent

Status: Draft · Owner: Leah Okafor · Last updated: 2026-11-13

How 400 customers are recruited, what they are told, and what they can do about it. Consent is not a
tick box here: beta customers are taking a real order on a changed system, and they need to know what
that means.

## Recruitment

| Step | Detail | Owner |
| :--- | :--- | :--- |
| 1. Audience build | Opted-in customers, segments from the cohort definition | Marcus Feld |
| 2. Invitation | Email to 12,000, first come by segment quota | Jo Bell |
| 3. Screening | Exclusions applied, segment quotas filled | Marcus Feld |
| 4. Confirmation | Joining instructions, support details, dates | Jo Bell |
| 5. Reminder | 48 hours before the window opens | Jo Bell |

Twelve thousand invitations for 400 places is a 3.3 % acceptance assumption. The October trial of the
same mechanic, with 40 places, got 4.1 %, so there is headroom.

## What the invitation says

> You are invited to try our new delivery promise before it goes live. You will see a confirmed
> delivery date when you shop, and your orders are real. For two weeks you will have a named support
> team, and we will ask you two short surveys. If anything goes wrong with your order, you can
> cancel it at any point for a full refund, whatever the reason.

The refund commitment is deliberate: it removes the risk argument from the customer's decision, and
it was the single change that took acceptance from 1.9 % to 4.1 % in the trial.

## Consent

| Item | Detail |
| :--- | :--- |
| Lawful basis | Consent for the beta interaction; contract for the orders themselves |
| What is consented to | Participation, surveys, order data used in analysis |
| Withdrawal | Any time, by email or a link in every survey; orders unaffected |
| Retention | Beta data deleted 90 days after the report, anonymised aggregates kept |
| Data protection contact | Named in every communication |

Withdrawal is one click, and the customer keeps shopping normally. A beta that traps people in it
produces compliance risk and bad feedback.

## Privacy impact

| Data | Used for | Risk | Mitigation |
| :--- | :--- | :--- | :--- |
| Order history | Cohort selection | Low | Existing basis, no new data |
| Postcode | Promise calculation | Medium | District only in logs, hash elsewhere |
| Survey responses | Product decisions | Low | Pseudonymous, quotes approved before use |
| Support recordings | Training and analysis | Medium | Consent captured, deleted after 90 days |

The DPIA for beta is drafted and must be signed before recruitment (DEP-04). The main open point is
support call recordings, which are useful and not strictly necessary; the default is not to record
unless the customer agrees at the start of the call.

## Incentive

A £10 voucher on completing the second survey, plus a full refund on any cancelled order during the
window. The voucher is offered for feedback, not for orders: paying people to buy would bias both the
sample and the accuracy measurement.

## What we tell them about risk

| Risk | What we say |
| :--- | :--- |
| A date may change | "We will tell you if it does, and you can cancel." |
| A store may not find an item | "You will be told within 30 minutes and refunded." |
| The site may behave oddly | "Tell us; you will not be charged for our errors." |

Nothing is hidden. A customer who is surprised by a beta behaviour is a customer lost.

## Related

[Beta cohort](./beta-cohort.md) · [Feedback survey](./feedback-survey.md) ·
[Data protection](../../architecture/platform/security-architecture.md)
