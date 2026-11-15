# Stock Feeds

Status: In review · Owner: Dan Whitcombe · Last updated: 2026-11-13

Five sources of stock truth, four of them warehouses and one of them 184 shops. This workstream is
about getting their numbers into the platform quickly, correctly, and in a form that says how
trustworthy each number is.

## The five sources

| Source | Type | Records | Cadence today | Contract target |
| :--- | :--- | :--- | :--- | :--- |
| [Midlands DC](./warehouses/midlands-dc.md) | Own DC | 210,000 | 15 min snapshot | 5 min delta |
| [Glasgow DC](./warehouses/glasgow-dc.md) | Own DC | 96,000 | 15 min snapshot | 5 min delta |
| [Northgate Fulfilment](./warehouses/northgate-fulfilment.md) | 3PL | 148,000 | 15 min delta | 5 min delta |
| [Riverside Logistics](./warehouses/riverside-logistics.md) | 3PL | 61,000 | 15 min delta | 10 min delta |
| [Store network](./warehouses/store-stock-network.md) | 184 stores | 41,000 lines | nightly file | 60 min file |

## The loop

```text
poll or receive → validate → normalise → compute availability → publish stock.changed
```

| Step | What it guarantees |
| :--- | :--- |
| Poll or receive | Every source has a recorded last-success time |
| Validate | Rejected records are quarantined with a reason, never silently dropped |
| Normalise | One schema, one SKU key, one location key |
| Compute | `available = on_hand - allocated - quarantine`, in one place |
| Publish | One `stock.changed` per SKU whose available figure actually moved |

## What "fresh" means

Freshness is per source, not global, and it is measured from the **feed timestamp**, not from when
we received the message. A feed that arrives on time but contains an hour-old timestamp is stale,
and pretending otherwise is how a platform ends up confidently wrong.

| Source | Stale after | Effect |
| :--- | :--- | :--- |
| Midlands, Glasgow, Northgate | 15–20 min | Warehouse removed from availability |
| Riverside | 45 min | Marked degraded, last value used |
| Stores | 90 min | Collection promises withdrawn |

## Where to read

| Question | Document |
| :--- | :--- |
| What does each warehouse send, and what does it get wrong? | [Warehouses](./warehouses/) |
| What is in a message, exactly? | [Feed contracts](./protocol/feed-contracts.md) |
| How often do we poll, and why? | [Polling and cadence](./protocol/polling-and-cadence.md) |
| Delta or snapshot? | [Delta and snapshot](./protocol/delta-and-snapshot.md) |
| How is a feed authenticated? | [Authentication](./protocol/authentication.md) |
| How do we test without a warehouse? | [Feed simulator](./protocol/feed-simulator.md) |
| What is the latency budget? | [Latency budget](./reliability/latency-budget.md) |
| How do the three stock numbers reconcile? | [Reconciliation](./reliability/reconciliation.md) |
| What happens when a feed stops? | [Stale stock handling](./reliability/stale-stock-handling.md) |

## Current status

Three of five feed contracts are drafted (Midlands, Glasgow, Northgate). Riverside needs a vendor
change request for a 10-minute delta; the store network needs the hourly change agreed with store
operations (CR-007, approved). M3 on 2027-01-15 requires all five signed.

## Related

[Current state warehouse systems](../current-state/systems/warehouse-systems.md) ·
[Availability API](../reference/api/availability-api.md) ·
[Feed failures](../stock-feeds/reliability/failure-and-retry.md)
