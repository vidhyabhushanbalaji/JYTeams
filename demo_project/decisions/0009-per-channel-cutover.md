# 0009 — Per-Channel Cutover

Status: Accepted · Date: 2026-10-30 · Deciders: Priya Raman, Tom Alder, Marcus Feld

## Context

Five channels, one new platform, and a single go-live date in the original plan. The question was whether
to switch everything at once or stage it, and if staged, in which order.

## Options

| Option | Risk profile | Time to full launch | Learning |
| :--- | :--- | :--- | :--- |
| A. All channels on one day | Maximum, one shot | Immediate | None until it is too late |
| B. Website first, then channels weekly | Contained | 3 weeks | High, each week informs the next |
| C. Stores first | High (physical process) | 3 weeks | Poor, store issues are slow to surface |
| D. One warehouse first, all channels | Narrow blast radius | 3 weeks | Medium, but channel behaviour untested |

## Decision

Cut over **per channel**: website 18 May, marketplaces 25 May, wholesale 1 June, stores 8 June.

## Why the website first

We control the frontend, can roll back with a flag, and see the whole customer journey. It gives the
fastest learning with the smallest irreversible risk. Marketplaces first would risk an account-health
warning while we were still learning; stores first would put an unfamiliar process in front of colleagues
and customers simultaneously.

## Consequences

| Easier | Harder |
| :--- | :--- |
| Four smaller decisions instead of one enormous one | Three extra weeks of dual-running |
| Each channel's behaviour observed in isolation | Old and new paths coexist, so bugs can hide in the seam |
| Rollback scope is limited to one channel | More comms, more briefings, more roster |
| Failure in one channel does not stop the others | The last channel launches after hypercare has started |

The fourth row is the most awkward: store collection goes live at the end of week three of hypercare, so
the hypercare team changes shape mid-flight. The plan accounts for it with a dedicated store week in the
rota.

## The seam risk

Running the old marketplace extract alongside the new push would be dangerous, so the old path is disabled
at cutover rather than left as a fallback. That means marketplace rollback restores the old extract, which
is tested in the second rehearsal.

## Related

[Rollout by channel](../launch-readiness/cutover/rollout-by-channel.md) ·
[Cutover plan](../launch-readiness/cutover/cutover-plan.md) ·
[Rollback plan](../launch-readiness/rollback/rollback-plan.md)
