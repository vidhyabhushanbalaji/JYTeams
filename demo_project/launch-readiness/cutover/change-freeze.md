# Change Freeze

Status: Agreed · Owner: Priya Raman · Last updated: 2026-11-06

Three freeze windows protect the launch and the peak that follows it. A freeze is not a ban on work; it
is a rule that the default answer is no and the exception has a name attached.

## The windows

| Window | Dates | Applies to | Default |
| :--- | :--- | :--- | :--- |
| Pre-UAT | 2027-03-19 to 2027-04-05 | Platform code, feed contracts | Fixes only |
| Launch | 2027-05-11 to 2027-06-08 | Everything customer-facing | No change without sponsor approval |
| Peak | 2027-10-25 to 2028-01-08 | Stock, promise, carriers | Change request plus go/no-go |

## What is allowed during a launch freeze

| Change | Allowed? | Approval |
| :--- | :--- | :--- |
| Fix for a Sev-1 defect | Yes | Launch lead |
| Fix for a Sev-2 defect | Yes | Launch lead plus platform lead |
| Configuration change to a policy key | No, unless it is a rollback action | Sponsor in writing |
| Carrier cut-off change | No | — |
| Copy change | No | — |
| New SKU dimensions in Atlas | Yes | Trading |
| Warehouse hold | Yes | Fulfilment |

The last two lines matter: a freeze on the platform is not a freeze on the business. Data still
changes, stock still moves, and the runbooks still apply.

## Exception process

| Step | Detail |
| :--- | :--- |
| 1 | Written request: what, why now, blast radius, rollback |
| 2 | Impact assessment by the platform lead |
| 3 | Approval by the launch lead, or sponsor during launch |
| 4 | Deploy with two people watching |
| 5 | Record in the freeze log |

Requests during a freeze are answered within two hours, including a no. A queue nobody answers is how
people start working around a freeze.

## Peak freeze

The peak freeze is longer and narrower. Nothing that touches stock, promise or carrier logic may
change between 25 October 2027 and 8 January 2028, because that window carries 31 % of annual revenue
and a broken promise at peak is not fixable quickly.

| Allowed during peak freeze | Example |
| :--- | :--- |
| Emergency rollback | Revert to the previous promise source |
| Carrier capacity response | Withdraw next-day for a day |
| Warehouse hold | Hold a stale warehouse |
| Copy for a known issue | Add a banner about a carrier delay |

## Before each freeze

| Check | Owner |
| :--- | :--- |
| No half-finished feature branches deployed | Nadia Kerr |
| Configuration exported and versioned | Nadia Kerr |
| Rollback tested within the last 14 days | Nadia Kerr |
| Monitoring thresholds reviewed | Dan Whitcombe |
| Comms sent to all teams | Jo Bell |

## History

The programme has had one attempt to bypass a freeze, in September 2026, when a carrier change was
deployed during the UAT environment build. It worked, and it invalidated three days of test data.
Since then the freeze log has been reviewed at every steering meeting.

## Related

[Change control](../../programme/governance/change-control.md) · [Cutover plan](./cutover-plan.md) ·
[Rollback plan](../rollback/rollback-plan.md)
