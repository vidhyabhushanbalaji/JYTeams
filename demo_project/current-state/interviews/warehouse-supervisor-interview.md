# Interview — Warehouse Supervisor

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-10-21

Interview with **Dermot Shaw**, shift supervisor at Midlands DC, on 2026-10-16, 45 minutes, on the
mezzanine floor during a shift change. Two further supervisors at Glasgow and Northgate were
interviewed the same week with the same script.

## What the floor actually does

> "The system tells me I have twelve of something. I walk over and there are nine. I change it to
> nine, and then somebody in an office changes it back because finance asked them to." — Dermot

That single quote explains the stock accuracy problem better than any measurement. The warehouse
corrects the shelf, the office corrects the system, and neither correction carries a reason.

## The five points they made

| Point | Detail | Design consequence |
| :--- | :--- | :--- |
| Allocation without a pick is invisible | Stock is allocated when a wave is built, which can be 9 hours after the order | Reservations must be visible before the wave, not at it |
| Release has no reason | When stock comes back, nobody knows if it was cancelled or expired | Every release needs a reason code |
| Wave building is the real cut-off | 15:00 is the dispatch cut-off; the wave is built at 12:30 | The promise must use 12:30, not 15:00 |
| Quarantine is not separated | Damaged stock sits in the same number until someone writes it off | Feeds must exclude quarantine explicitly |
| Overnight is dead time | Nothing moves between 22:00 and 06:00, but orders still arrive | Promises made overnight must assume the morning shift |

## On the new system

Supervisors want **fewer numbers, not more**. Their current screen has eleven quantities per SKU
and no explanation of any of them. The requirement they care about is a single "available to sell"
figure that matches what they can physically pick.

They are sceptical of the 5-minute feed target: "We update the floor when we update the floor. If
you poll every five minutes you will get the same number eleven times and change once." That is
accepted and is the reason the feed contract specifies change-driven deltas rather than fixed
snapshots.

## A story worth keeping

In August, a pallet of 240 garden planters was received against the wrong purchase order and sat in
quarantine for nine days. The system showed them as available the whole time, so 61 orders were
taken and 61 customers were called. The write-off was £4,900. No process failure was recorded
because each step was individually correct.

## Related

[Manual interventions](../order-flow/manual-interventions.md) · [Midlands DC feed](../../stock-feeds/warehouses/midlands-dc.md) ·
[Discovery findings](./discovery-findings.md)
