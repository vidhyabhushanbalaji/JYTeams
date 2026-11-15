# Rollback Plan

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

How to get back to the previous promise within 45 minutes. A rollback is a controlled change, not an
emergency: it has an order, a checklist, and a decision-maker who is named before launch day.

## What rollback means

Two levels, deliberately separated:

| Level | What it does | Time | Customer impact |
| :--- | :--- | :--- | :--- |
| Soft rollback | Turn off the new promise for new traffic; keep everything already created | 5 min | New customers see the old flag again |
| Full rollback | Turn off the new promise and stop the new services | 45 min | As above, plus reservations stop being created |

Soft rollback is the default. Full rollback is only needed if the platform itself is causing harm, for
example writing wrong reservations faster than we can stop it.

## The sequence (soft)

| Step | Action | Owner | Time |
| :--- | :--- | :--- | :--- |
| 1 | Set the website promise flag to legacy | Tom Alder | 1 min |
| 2 | Confirm product pages show the old behaviour | Nadia Kerr | 3 min |
| 3 | Pause new reservations for existing orders | Nadia Kerr | 2 min |
| 4 | Leave existing reservations to expire naturally | Nadia Kerr | 30 min |
| 5 | Check contact volume and error rate | Marcus Feld | 10 min |
| 6 | Announce in the incident channel | Jo Bell | 2 min |

## The sequence (full)

| Step | Action | Time |
| :--- | :--- | :--- |
| 1 | Website flag to legacy | 1 min |
| 2 | Marketplace push disabled, Mercury extract re-enabled | 5 min |
| 3 | Store collection promise disabled, nightly file mode restored | 5 min |
| 4 | Reservation worker paused; reservation table frozen read-only | 2 min |
| 5 | DPS traffic routed to the fallback estimate | 2 min |
| 6 | Feeds continue into ATP but ATP is not read by channels | 1 min |
| 7 | Verify all four channel behaviours | 20 min |
| 8 | Post-rollback check with finance and fulfilment | 10 min |

Step 4 is the one that needs care: pausing the worker while leaving reservations read-only means no
new claims and no silent releases. Releasing 8,000 reservations in a panic would create an oversell
storm in the opposite direction.

## What happens to data created in the new world

| Data | After rollback | Owner |
| :--- | :--- | :--- |
| Soft reservations | Expire naturally, released with reason | Nadia Kerr |
| Allocated reservations | Stay allocated; Mercury dispatch continues | Sofia Mendes |
| Promises issued | Honoured where possible, otherwise contact centre | Marcus Feld |
| Feed history | Retained for the review | Dan Whitcombe |
| Promise records | Read-only, retained 90 days | Nadia Kerr |

Orders already promised a date are honoured, even after a rollback. A rollback that cancels customer
promises is worse than the problem it fixes, and the contact centre script for this case is in the
runbook pack.

## Verification

| Check | Expected after soft rollback |
| :--- | :--- |
| Product page | Old stock flag, no date |
| Basket | No delivery groups |
| New reservations per minute | 0 |
| Existing reservations | Still expiring normally |
| Marketplace pushes | Old extract cadence |
| Contact volume | Falling within 30 minutes |

## Rehearsals

| Rehearsal | Date | Target | Result |
| :--- | :--- | :--- | :--- |
| 1 | 2027-03-11 | Complete in ≤ 60 min | Not yet run |
| 2 | 2027-04-22 | Complete in ≤ 45 min | Not yet run |

Both rehearsals include a deliberate wrinkle: the first includes a carrier API failure during the
rollback, the second includes a person not answering their phone. A rehearsal with everything going
well is not a rehearsal.

## After a rollback

| Step | Owner | Timing |
| :--- | :--- | :--- |
| Incident review scheduled | Marcus Feld | Within 24 h |
| Root cause and fix plan | Nadia Kerr | Within 5 days |
| Re-launch decision | Steering group | Next meeting |
| Customer communication, if promises slipped | Jo Bell | Same day |

## Related

[Rollback triggers](./rollback-triggers.md) · [Hypercare plan](../hypercare/hypercare-plan.md) ·
[Runbook: ATP outage](../runbooks/atp-service-outage.md)
