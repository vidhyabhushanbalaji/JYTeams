# Carrier Notification

Status: Draft · Owner: Gavin Shore · Last updated: 2026-11-13

Carriers need to know three things before launch: that booking volume will change shape, that
serviceability queries will increase sharply, and that rebookings should fall. None of that is
obvious from their side.

## What changes for each carrier

| Carrier | Today | From launch | Notice required |
| :--- | :--- | :--- | :--- |
| Parcelway | Bookings created by Mercury nightly | Bookings created at order time, higher rate | 4 weeks |
| Northline | Bookings made by the desk | Bookings created at promise time, slot-checked | 6 weeks |
| Swiftbox | As Parcelway | As Parcelway | 4 weeks |

The volume does not change much; the **timing** does. Bookings move from a nightly batch to a steady
stream, which affects carrier systems that expect a batch.

## The three conversations

| Topic | With | Owner | By |
| :--- | :--- | :--- | :--- |
| Rate limits and API behaviour at 30 bookings/second | Parcelway solutions architect | Dan Whitcombe | 2027-03-12 |
| Slot capacity commitment for weeks 15–18 | Northline commercial | Gavin Shore | 2027-03-05 |
| Locker capacity feed and sizing | Swiftbox integration | Dan Whitcombe | 2027-02-19 |

The second is R-06 and the only one with a real risk of not being agreed.

## Serviceability query volume

Serviceability calls rise from about 40,000 a day to roughly 150,000 a day at peak, because every
product page and checkout step asks. Parcelway's contract allows 600 calls per minute; the platform
caches aggressively and expects 90 calls per minute at peak, so the allowance is comfortable.

| Carrier | Current calls/day | Expected at launch | Contract limit |
| :--- | :--- | :--- | :--- |
| Parcelway | 38,000 | 145,000 | 600/min |
| Northline | 2,100 | 6,500 | 120/min |
| Swiftbox | 6,400 | 22,000 | 300/min |

## What we ask carriers to do

| Ask | Why |
| :--- | :--- |
| Confirm cut-off times in writing | The promise depends on them |
| Nominate a named contact for launch week | Escalation |
| Provide a daily capacity figure during peak | Withdraw next-day before it fails |
| Tell us about planned changes 30 days ahead | Freeze compliance |
| Alert us to serviceability changes the same day | Postcode promises |

The third is new and only Parcelway has agreed so far. Northline provides a weekly capacity forecast,
which is slower but usable.

## Launch week comms

| When | What | To |
| :--- | :--- | :--- |
| 2027-05-11 | Launch confirmed, contact list shared | All three carriers |
| 2027-05-17 | War room hours and escalation path | All three carriers |
| 2027-05-18 | Launch-day note | All three carriers |
| 2027-05-25 | Marketplace volume added | Parcelway, ChannelBridge |
| 2027-06-08 | Store collection live (no carrier impact) | Parcelway |

## If a carrier cannot support the change

| Scenario | Response |
| :--- | :--- |
| Parcelway cannot take steady bookings | Keep nightly booking for that carrier, promise from stock only |
| Northline cannot commit capacity | Launch bulky with website, hold bulky promotions until June |
| Swiftbox feed unavailable | Hide locker option; no customer-visible error |

Each of these is a degraded outcome, not a launch blocker, which is why the carrier work is scoped to
allow partial launch.

## Related

[Carrier onboarding](../../delivery-promise/carriers/carrier-onboarding.md) ·
[Carrier performance](../../delivery-promise/carriers/carrier-performance.md) ·
[Cutover plan](../cutover/cutover-plan.md)
