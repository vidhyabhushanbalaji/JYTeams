# Test Cases — Marketplace Stock Display

Status: Draft · Owner: Aisha Bello · Last updated: 2026-11-13

Amazon and eBay see stock every five minutes, from a pool that neither of them reserves against. These
cases test the feed we push and the consequences of pushing it badly, because a marketplace oversell
is not a refund: it is an account health warning.

## The cases

| ID | Given | When | Then |
| :--- | :--- | :--- | :--- |
| MP-01 | 40 units available at Midlands | Push cycle runs | Amazon quantity becomes 40 (AC-15) |
| MP-02 | 40 units, 12 reserved by website orders | Push cycle runs | Marketplace quantity is 28 |
| MP-03 | Two marketplace orders in the same minute | Both processed | Both reserved, third customer sees 78 not 80 |
| MP-04 | Feed stale beyond threshold | Push cycle runs | Push skipped, previous quantity retained |
| MP-05 | Quarantine of 30 units | Push cycle runs | Quantity drops by 30 (AC-03) |
| MP-06 | Amazon pending order never confirms | 30 minutes pass | Reservation released with a reason |
| MP-07 | eBay buyer cancels within an hour | Cancel received | Reservation released, quantity restored |
| MP-08 | ChannelBridge returns 429 | Push cycle runs | Back off honoured, no duplicate push |
| MP-09 | Push fails for 30 minutes | Alert threshold passes | Alert raised, marketplace quantity marked stale |
| MP-10 | SKU not ranged on Amazon | Push cycle runs | Not included; no error |
| MP-11 | Order pulls arrive out of order | Both processed | Later order time wins; earlier not double-counted |
| MP-12 | Amazon order for 3, only 2 available | Order processed | Partial or cancel path, no oversell |

## The five-minute promise

| Property | Test | Pass |
| :--- | :--- | :--- |
| Push latency | 100 cycles timed | p95 ≤ 5 min |
| Reservation reflected | Reserve then time the push | ≤ 5 min |
| Release reflected | Release then time the push | ≤ 5 min |
| Stale suppression | Force stale, observe push | Skipped within 1 cycle |
| Idempotency | Re-run a cycle | No quantity change |

## What matters more than the cases

**MP-02** is the whole design in one test: a marketplace must see unreserved stock, not on-hand stock.
If it sees 40 while the website has sold 12, Amazon will sell units that do not exist and the account
warning follows three weeks later.

**MP-06** is the pending-order trap that regressed in September 2026. Amazon sends a pending order,
Mercury reserves against it, and the order never confirms. The test asserts the release happens and
carries `reservation.expired`.

**MP-11** covers ordering: marketplace pulls can interleave, and a naive implementation applies the
later order before the earlier one and then double-counts.

## Volume checks

| Scenario | Orders/minute | Expectation |
| :--- | :--- | :--- |
| Normal | 2.6 | No throttling |
| Peak | 9.5 | Throttling within allowance, no loss |
| Promotion burst | 18 | Backoff, no duplicate reservations |

## Related

[Marketplace channel](../../current-state/channels/marketplaces.md) ·
[ADR 0004](../../decisions/0004-poll-marketplace-inventory.md) ·
[Failure scenarios](./failure-scenarios.md)
