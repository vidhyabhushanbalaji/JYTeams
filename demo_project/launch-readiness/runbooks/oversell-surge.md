# Runbook — Oversell Surge

**Symptom:** more than five order lines cancelled with `NO_STOCK_AFTER_ORDER` in an hour, or a
warehouse reporting units that do not exist.

**Customer impact:** direct. Every oversell is a cancellation, a refund and often a complaint. Ten in an
hour is a hard rollback trigger.

## 1. Quantify (2 minutes)

| Check | Where | Look for |
| :--- | :--- | :--- |
| Oversells per hour | Operations dashboard | Above 5 |
| Concentration | Same panel, by warehouse and SKU | One warehouse or one SKU |
| Reservations active for those SKUs | Reservation search | Reservations against missing stock |
| Feed timestamps for the warehouse | Health dashboard | Stale in the last hour |

## 2. Identify the pattern (5 minutes)

| Pattern | Likely cause | Action |
| :--- | :--- | :--- |
| One SKU | A stock correction or a transfer | Check Atlas and the warehouse's adjustment log |
| One warehouse | Feed stale or wrong | Apply the warehouse hold (step 3) |
| All warehouses, one channel | Channel bypassing reservations | Check the channel's integration, likely a deploy |
| Split across everything | Reservation worker failure | Check the worker: is it running, is it lagging? |

The third pattern is rare and serious: a channel that reads availability without reserving will oversell
the same unit all day.

## 3. Stop the bleeding

| Action | Effect | Authority |
| :--- | :--- | :--- |
| Hold the suspect warehouse | No new reservations there | On-call |
| Pause the offending channel's integration | No new orders from it | Marcus Feld |
| Withdraw next-day for affected SKUs | Reduces pressure | Tom Alder |
| Soft rollback | Back to stock flags | Marcus Feld |

Hold first, rollback second. A hold is reversible in a minute; a rollback is a 45-minute operation.

## 4. Recover the affected orders

| Step | Owner |
| :--- | :--- |
| Extract the list of affected orders | On-call |
| Prioritise by value and by collection orders | Marcus Feld |
| Call orders over £200, email the rest | Contact centre |
| Offer: alternative item, delivery when restocked, or refund | Marcus Feld |
| Record every contact in the order | Contact centre |

The third option is offered last, and the first option only where stock exists in another location.

## 5. Fix the cause

| Cause | Fix | Owner |
| :--- | :--- | :--- |
| Stale feed | Contract or cadence fix | Dan Whitcombe |
| Feed mapping wrong | Correct mapping, replay the batch | Dan Whitcombe |
| Reservation worker lagging | Scale the worker, check consumer lag | Nadia Kerr |
| Channel bypass | Disable path until fixed | Nadia Kerr |
| Manual override | Review who and why; remove the ability | Marcus Feld |

## 6. Review

| Item | When |
| :--- | :--- |
| Incident timeline | Within 24 hours |
| Customer impact and cost | Within 5 days |
| Whether the trigger threshold was right | Within 5 days |
| Follow-up actions and owners | Within 5 days |

## Escalation

| Condition | To |
| :--- | :--- |
| 5–9 oversells in an hour | Marcus Feld |
| 10 or more | Marcus and Priya, hard rollback decision |
| Any oversell involving a collection order | Elena Vasquez as well |

## Never do

| Never | Why |
| :--- | :--- |
| Release reservations in bulk to "reset" | Creates stock that does not exist |
| Correct the warehouse's stock figure manually at source | The next feed overwrites it and the audit trail breaks |
| Cancel orders silently | The customer finds out when nothing arrives |
| Blame the warehouse in customer comms | The customer bought from us |

## Related

[Oversell prevention](../../reservation-policy/policy/oversell-prevention.md) ·
[Rollback triggers](../rollback/rollback-triggers.md) ·
[Stale stock handling](../../stock-feeds/reliability/stale-stock-handling.md)
