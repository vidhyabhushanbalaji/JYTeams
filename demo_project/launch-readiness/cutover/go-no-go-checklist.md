# Go/No-Go Checklist

Status: Draft · Owner: Priya Raman · Last updated: 2026-11-13

The checklist the steering group will use on 2027-05-11. Each line has an owner and evidence, and a
single unmet line in the "must" column means no-go, regardless of how good everything else looks.

## Must be true (any failure = no-go)

| # | Item | Owner | Evidence |
| :--- | :--- | :--- | :--- |
| 1 | UAT signed off with no Sev-1 or Sev-2 | Aisha Bello | Sign-off record |
| 2 | Promise accuracy in beta ≥ 88 % | Tom Alder | Beta week 2 report |
| 3 | No oversell in beta | Aisha Bello | Beta report |
| 4 | All five feeds fresh within thresholds for 10 days | Dan Whitcombe | Feed report |
| 5 | Reconciliation within tolerance for 10 days | Ben Osei | Reconciliation report |
| 6 | Rollback rehearsed within 7 days, completing in ≤ 45 min | Nadia Kerr | Rehearsal record |
| 7 | Penetration test critical and high findings closed | Nadia Kerr | Security report |
| 8 | DPIA signed and beta consent records complete | Leah Okafor | DPIA |
| 9 | Contact centre briefed and roster confirmed | Marcus Feld | Training record |
| 10 | Runbooks published and walkthrough done | Marcus Feld | Runbook index |
| 11 | Rollback decision-maker named and contactable on the day | Priya Raman | Launch rota |
| 12 | Comms ready for customers, stores, carriers | Jo Bell | Comms pack |

## Should be true (failure = condition, not veto)

| # | Item | Owner | Evidence |
| :--- | :--- | :--- | :--- |
| 13 | Sev-3 defects ≤ 15 | Aisha Bello | Tracker |
| 14 | Fallback share ≤ 1 % in the last week | Gavin Shore | Dashboard |
| 15 | Accessibility sign-off complete | Tom Alder | Accessibility record |
| 16 | Peak cut-off changes configured in advance | Gavin Shore | Configuration |
| 17 | Store pilot (40 stores) reporting positively | Elena Vasquez | Pilot note |
| 18 | Hypercare rota agreed with named engineers | Nadia Kerr | Rota |

## Discussion items (no threshold)

| # | Item | Why it is discussed |
| :--- | :--- | :--- |
| 19 | Residual risks R-01, R-03, R-05 | The three that could still bite |
| 20 | Bulky accuracy, which beta cannot prove | Whether to launch bulky with the website |
| 21 | Northern Ireland and islands coverage | CR-010 decision timing |

Item 20 is the one likely to produce a real argument. The options are to launch bulky with the website
and accept a lower accuracy, or hold bulky for two weeks and launch it with wholesale. Gavin favours
launching together; Sofia favours holding.

## The paper

The go/no-go paper is four pages: the checklist with evidence links, the residual risk position, the
beta verdict, and a recommendation. It is circulated on 4 May, and no new evidence is accepted after
8 May except a Sev-1.

## If it is a no-go

| Scenario | What happens |
| :--- | :--- |
| One "must" item unmet | Launch moves to 1 June, steering reconvenes 25 May |
| Two or more unmet | Launch moves out of Q2; replan |
| Beta accuracy below 88 % but above 82 % | Conditional go with a remediation plan and a daily review |
| Feed instability only | Launch website only, hold marketplaces and stores |

The last row is the most likely partial outcome and is pre-agreed, so it does not need a new decision
on the day.

## Related

[Timeline](./timeline.md) · [Rollback triggers](../rollback/rollback-triggers.md) ·
[Milestones](../../programme/plan/milestones.md)
