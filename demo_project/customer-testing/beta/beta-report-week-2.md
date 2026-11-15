# Beta Report — Week 2 Template

Status: Template · Owner: Aisha Bello · Last updated: 2026-11-13

The closing beta report, published 2027-04-26, which feeds directly into UAT exit and the go/no-go
paper. As with week 1, the thresholds and decision rules are fixed in advance.

## Header

| Field | Value to complete |
| :--- | :--- |
| Period | 2027-04-12 to 2027-04-26 |
| Cohort size | 400 |
| Orders | … |
| Author | Aisha Bello |
| Distribution | Programme board, steering group |

## Final metrics

| Metric | Target | Actual | Verdict |
| :--- | :--- | :--- | :--- |
| Orders placed | ≥ 500 | — | — |
| Promise accuracy (strict) | ≥ 88 % | — | — |
| Promise accuracy (tolerant) | ≥ 93 % | — | — |
| Oversells | 0 | — | — |
| Date changed after purchase | ≤ 3 % | — | — |
| Fallback share | ≤ 1 % | — | — |
| Survey 1 responses | ≥ 200 | — | — |
| Survey 2 responses | ≥ 160 | — | — |
| Satisfaction (S2-03 mean) | ≥ 4.0 | — | — |
| Sev-1 defects | 0 | — | — |
| Sev-2 defects open at close | 0 | — | — |

## What the metrics cannot show

| Limitation | Effect on the decision |
| :--- | :--- |
| Bulky sample of ~19 | Bulky accuracy is inferred from UAT, not beta |
| Website only | Marketplace and store channel confidence comes from UAT |
| Two weeks | Seasonal and peak behaviour not covered |
| Self-selected cohort | Enthusiastic customers; complaints may be under-represented |

The recommendation to steering will state which of its claims rest on beta and which on UAT. A
recommendation that blurs the two would not survive the go/no-go discussion, and rightly.

## Sections to complete

1. **Final numbers** — as tabled above, with the tolerance explained.
2. **Themes** — the four or five things customers said most, with two verbatims each.
3. **Defect position** — every Sev-1 and Sev-2, with fix status and verification evidence.
4. **Support load** — contacts per 100 orders, compared to baseline.
5. **Copy changes made during beta** — what changed, and why it was safe to change mid-flight.
6. **Residual risks** — what beta could not test.
7. **Recommendation** — proceed to go/no-go, proceed with conditions, or delay.

## Decision rules

| Condition | Recommendation |
| :--- | :--- |
| All targets met, no open Sev-2 | Proceed to go/no-go |
| Targets met, ≤ 2 Sev-2 with fixes verified | Proceed with conditions |
| Accuracy 82–88 % | Proceed only with a documented plan to reach 88 % by hypercare exit |
| Accuracy < 82 %, or any oversell unaccounted for | Delay the website launch |

A delay is a legitimate outcome of this exercise and is written here so that recommending one does not
feel like a failure.

## Feed into the go/no-go paper

| Input | Where it appears |
| :--- | :--- |
| Beta verdict | Go/no-go checklist, row "evidence" |
| Residual risks | Risk register, R-01 and R-03 review |
| Copy changes | Customer messaging documents |
| Support readiness | Hypercare plan |

## Related

[Week 1 report template](./beta-report-week-1.md) · [UAT exit criteria](../uat/entry-and-exit-criteria.md) ·
[Go/no-go checklist](../../launch-readiness/cutover/go-no-go-checklist.md)
