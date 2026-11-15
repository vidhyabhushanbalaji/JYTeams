# Beta Cohort

Status: Agreed · Owner: Aisha Bello · Last updated: 2026-11-13

400 real customers on the website channel for two weeks, 12–26 April 2027, running alongside UAT.
This document defines who they are, why 400, and what would make us stop.

## Why 400

| Question | Value | Reasoning |
| :--- | :--- | :--- |
| Expected accuracy | 88 % | Launch target for the beta window |
| Confidence interval | ±3.2 % | Enough to distinguish 88 % from 82 % |
| Expected orders | 620 | 400 customers, 1.55 orders each |
| Split orders | ~236 | Enough to test the two-date experience |
| Bulky orders | ~19 | Too few to prove bulky; UAT covers it |
| Collection orders | ~50 | Enough to catch store issues early |

Nineteen bulky orders cannot prove a 58 % to 88 % improvement, and the document says so rather than
pretending the sample covers every segment. Bulky is proven in UAT and in the pilot stores.

## Composition

| Segment | Share | Why included |
| :--- | :--- | :--- |
| Frequent website customers | 40 % | They notice changes and give useful feedback |
| Lapsed customers (12–18 months) | 20 % | Tests whether the promise brings people back |
| Customers who had an oversell in 2026 | 20 % | The people most likely to test our claims |
| Collection users | 15 % | Store promise feedback |
| Employees (non-project) | 5 % | Convenient, and excluded from analysis |

Employees are excluded from the accuracy analysis because they are not representative, but they are
included in the cohort so that the support team gets early exposure to unusual journeys.

## Exclusions

| Excluded | Why |
| :--- | :--- |
| Wholesale accounts | Different promise, different support |
| Marketplace customers | Cannot be segmented at the marketplace level |
| Northern Ireland customers | Parcelway next-day does not cover them |
| Customers with open complaints | Not a good experience to test on |
| Project team and immediate families | Cannot give unbiased feedback |

## Waves

| Wave | Date | Size | Purpose |
| :--- | :--- | :--- | :--- |
| 1 | 2027-04-12 | 100 | Shake out support and monitoring |
| 2 | 2027-04-16 | 300 | Volume and variety |
| Hold | 2027-04-20 | — | Pause if any stop condition is met |

Wave 2 only starts if wave 1 has no Sev-1 and accuracy is above 80 %. That threshold is deliberately
lower than the exit target: the purpose of wave 1 is to find catastrophic problems, not to prove the
metric.

## What beta can prove

| Provable | Not provable |
| :--- | :--- |
| The promise is understood by customers | Peak volume behaviour |
| Dates are broadly accurate on parcels | Bulky accuracy |
| Support can handle the questions | Marketplace behaviour |
| The copy does not mislead | Long-term trust |

## Stop conditions

| Condition | Action |
| :--- | :--- |
| Any Sev-1 defect | Pause the cohort, fix, restart after review |
| Accuracy below 75 % over 100 orders | Pause and investigate |
| More than 5 oversells | Pause, even if accuracy is acceptable |
| A stock feed excluded for more than 2 hours | Pause new orders for that warehouse |
| Customer complaints above 3× baseline | Pause and review copy |

A pause is Marcus Feld's call, with Aisha Bello and Tom Alder consulted. Restarting requires the
programme lead's agreement, and the reason for both is recorded in the beta report.

## Support

| Channel | Staffing | Hours |
| :--- | :--- | :--- |
| Dedicated phone line | 2 agents | 08:00–20:00 |
| Email alias | 1 agent, shared | 08:00–20:00 |
| Escalation to engineering | On-call | 24/7 |

Beta customers are told they have a named team, which is both honest and a useful way to find out
what the standard support flow will miss.

## Related

[Recruitment and consent](./recruitment-and-consent.md) · [Beta scripts](./beta-scripts.md) ·
[Feedback survey](./feedback-survey.md)
