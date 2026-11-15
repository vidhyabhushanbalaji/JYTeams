# Test Cases — Store Collection Scenarios

Status: Draft · Owner: Aisha Bello · Last updated: 2026-11-13

Store collection is the least reliable promise and the one with a physical customer at the end of it.
These cases test the reservation, the store task, the hold and the release, plus the failure modes
that a store can produce that no other location can.

## The cases

| ID | Given | When | Then |
| :--- | :--- | :--- | :--- |
| SC-01 | Store has 1 unit, fresh file | Collection order placed | Reservation created within 2 s (AC-16) |
| SC-02 | Store has 1 unit, another collection order | Second order placed | Second refused with a clear message |
| SC-03 | Reservation created | 30 minutes, not picked | Released, store task cancelled, stock returns |
| SC-04 | Store picks within 20 minutes | Pick scanned | Reservation becomes allocated, "ready" email sent |
| SC-05 | Picked item | Customer collects | Reservation becomes dispatched, store quantity decremented |
| SC-06 | Picked item | 5 days pass, not collected | Released with `NOT_COLLECTED`, customer emailed |
| SC-07 | Store cannot find the item | Store cancels pick | Released, customer told within 30 minutes |
| SC-08 | Store file 100 minutes old | Collection offered? | No: stale threshold blocks it (AC-18) |
| SC-09 | Store has stock but no pick task visible | Collection order placed | Task appears on handheld within 60 s |
| SC-10 | Customer chooses a store 200 miles away | Checkout | Allowed, but no "today" promise |
| SC-11 | Store's last count was 120 days ago | Collection offered? | Offered with a confidence caveat |
| SC-12 | Customer wants a different size at pick | Store substitutes | Substitution recorded, reservation moves to new SKU |
| SC-13 | Two stores within 20 miles, one out of stock | Checkout | Only the stocked store offered |
| SC-14 | Pick reservation expires, customer still wants it | Order page | Re-reservation attempted if stock permits |

## The two clocks

| Clock | Duration | Test proves |
| :--- | :--- | :--- |
| Store pick window | 30 minutes | SC-03 |
| Collection hold | 5 days (RSV-11 open) | SC-06 |

SC-03 and SC-06 are easy to confuse in the implementation. A test that runs "the reservation expires"
against the wrong constant will pass while the customer waits five days for a pick that never
happened.

## The store's perspective

| Scenario | What the store sees | What we assert |
| :--- | :--- | :--- |
| New collection order | Task with name and order number | Task fields present |
| Same order, 24 hours later | Reminder task, area manager copied | Escalation fired |
| Item not found | Cancel button with reasons | Reason captured, no silent cancel |
| Collected | Scan completes the task | Task closed, no duplicate |

## Known gaps

| Gap | Impact | Plan |
| :--- | :--- | :--- |
| No store task API in UAT | SC-09 and SC-10 cannot run yet | Store integration from 2027-02 |
| Stale last-counted data | SC-11 asserts a caveat, not accuracy | Scanner rollout Q3 2027 |
| Substitution lacks a UI | SC-12 is API-level only | Hypercare backlog |

## Why collection is tested with real stores

Forty of the 184 stores take part in a pilot from 2027-04, chosen for scanner coverage and willingness.
The rest are tested with the simulator, because a test environment cannot produce "the item is on a
shelf but nobody can find it", and that is the failure we most need to understand.

## Related

[Store collection rules](../../reservation-policy/edge-cases/store-collection.md) ·
[Store channel](../../current-state/channels/stores.md) ·
[Beta cohort](../beta/beta-cohort.md)
