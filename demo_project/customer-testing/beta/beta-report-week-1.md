# Beta Report — Week 1 Template

Status: Template · Owner: Aisha Bello · Last updated: 2026-11-13

The report that will be published on 2027-04-19, covering wave 1 and the first days of wave 2. This
is the template, complete with the thresholds and decision rules agreed in advance; the numbers are
entered during the beta window.

## Header

| Field | Value to complete |
| :--- | :--- |
| Period | 2027-04-12 to 2027-04-18 |
| Cohort size | 100 then 400 |
| Orders | … |
| Author | Aisha Bello |
| Status | Draft / Issued |

## Headline numbers

| Metric | Target | Actual | RAG |
| :--- | :--- | :--- | :--- |
| Orders placed | ≥ 150 | — | — |
| Promise accuracy (strict) | ≥ 84 % | — | — |
| Promise accuracy (tolerant) | ≥ 90 % | — | — |
| Oversells | 0 | — | — |
| Fallback share | ≤ 1 % | — | — |
| Split orders | 30–45 % | — | — |
| Collection orders | ≥ 20 | — | — |
| Date changed after purchase | ≤ 3 % | — | — |
| Contacts per 100 orders | ≤ 6 | — | — |
| Sev-1 defects | 0 | — | — |
| Sev-2 defects | ≤ 3 | — | — |

## What we expect to learn

| Question | Why it matters |
| :--- | :--- |
| Does the date match the confirmation email? | The most common failure in the old system |
| Do customers understand "two parcels, two dates"? | Split messaging |
| Is the fallback understood or alarming? | Copy risk |
| Do store collections work with real staff? | Least reliable promise |
| Does support cope with promise questions? | Hypercare readiness |

## Decision rules

| Condition at the end of week 1 | Decision |
| :--- | :--- |
| Accuracy ≥ 84 %, no Sev-1 | Proceed to wave 2 unchanged |
| Accuracy 75–84 % | Proceed, with a defect triage session on the misses |
| Accuracy < 75 % | Pause, investigate, restart only with a fix |
| Any oversell | Pause, root cause, review the reservation path |
| Any Sev-1 | Pause immediately |
| Fallback above 5 % | Proceed, but escalate the feed issue to the programme board |

The rules are agreed in advance so that a bad week cannot be talked into a good one.

## Sections to complete

1. **Volume and mix** — orders by service, split rate, bulky count.
2. **Accuracy** — promised versus delivered, with the hour-of-day slice.
3. **Contacts** — categories, verbatims, and the three most common questions.
4. **Defects** — list with severity and owner.
5. **Customer quotes** — five verbatims, approved for use.
6. **Support observations** — staffing, response times, escalations.
7. **Recommendation** — continue, pause, or change something specific.

## Standing agenda for the review

| Item | Owner | Minutes |
| :--- | :--- | :--- |
| Numbers | Aisha Bello | 10 |
| Verbatims | Marcus Feld | 10 |
| Defects | Nadia Kerr | 10 |
| Decision | Priya Raman | 5 |

## Related

[Beta cohort](./beta-cohort.md) · [Feedback survey](./feedback-survey.md) ·
[Week 2 template](./beta-report-week-2.md)
