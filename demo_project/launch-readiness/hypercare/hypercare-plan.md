# Hypercare Plan

Status: Draft · Owner: Marcus Feld · Last updated: 2026-11-13

Four weeks of heightened support after the website launch, ending 15 June 2027. Hypercare is not
"watching"; it is a named team, a daily rhythm and a defined exit.

## Shape of the four weeks

| Week | Dates | Focus | War room |
| :--- | :--- | :--- | :--- |
| 1 | 18–24 May | Website live, stabilise | Staffed 07:00–21:00 |
| 2 | 25–31 May | Marketplaces live | Staffed 08:00–20:00 |
| 3 | 1–7 Jun | Wholesale live | Staffed 08:00–18:00 |
| 4 | 8–15 Jun | Stores live, close-out | On-call, daily check |

## The team

| Role | Person | Commitment |
| :--- | :--- | :--- |
| Hypercare lead | Marcus Feld | 100 % |
| Platform engineer | Nadia Kerr | 80 % |
| Feed engineer | Dan Whitcombe | 50 % |
| Product | Tom Alder | 40 % |
| QA | Aisha Bello | 50 % |
| Comms | Jo Bell | 30 % |
| Support liaison | Contact centre lead | 30 % |

The 50 % commitments are real: a person at 20 % during hypercare is a person who is not there when it
matters.

## Daily rhythm

| Time | What | Who | Duration |
| :--- | :--- | :--- | :--- |
| 08:30 | Overnight review: alerts, accuracy, fallbacks | On-call | 20 min |
| 09:15 | Stand-up: yesterday, today, blockers | Hypercare team | 20 min |
| 13:00 | Accuracy check, half-day | Aisha Bello | 10 min |
| 17:00 | Day summary to the programme channel | Marcus Feld | 15 min |
| 17:30 | Defect triage for the next day | Aisha Bello | 20 min |

## What we watch

| Signal | Green | Amber | Red |
| :--- | :--- | :--- | :--- |
| Promise accuracy (rolling 24 h) | ≥ 90 % | 85–90 % | < 85 % |
| Fallback share | ≤ 1 % | 1–3 % | > 3 % |
| Oversells | 0 | 1–2 | ≥ 3 |
| Reservations failed | ≤ 0.5 % | 0.5–2 % | > 2 % |
| Contacts per 100 orders | ≤ 5 | 5–8 | > 8 |
| Feed exclusions | 0 | 1 source, < 30 min | 2 sources or > 30 min |

## Exit criteria

| Criterion | Threshold |
| :--- | :--- |
| Two consecutive weeks inside green on accuracy | Required |
| No open Sev-1 or Sev-2 | Required |
| All four channels live and stable | Required |
| Runbooks updated with what we learned | Required |
| Support volume back within 20 % of baseline | Required |
| Post-incident actions from hypercare closed or owned | Required |

If exit is not met on 15 June, hypercare extends week by week, and each extension is reported to
steering. It is not a failure to extend; it is a failure to pretend.

## Handover to steady state

| Item | To | Date |
| :--- | :--- | :--- |
| Monitoring and alerting | Platform on-call | 2027-06-08 |
| Feed operations | Dan Whitcombe's team | 2027-06-15 |
| Customer support scripts | Contact centre | 2027-06-08 |
| Policy changes | Sofia Mendes | 2027-06-15 |
| Peak readiness planning | Marcus Feld | 2027-07-01 |

## Related

[Daily checkpoints](./daily-checkpoints.md) · [Escalation](./escalation.md) ·
[Launch week rota](./launch-week-rota.md)
