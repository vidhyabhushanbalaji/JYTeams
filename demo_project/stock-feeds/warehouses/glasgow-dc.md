# Glasgow DC Feed

Status: Draft · Owner: Dan Whitcombe · Last updated: 2026-11-13

Glasgow is the smaller own DC: 96,000 records, 14 % of orders, and the only site that makes
personalised products. It shares the DC-WMS codebase with Midlands but runs a different WMS release,
which matters more than it should.

## What the feed is

| Property | Today | Contract target |
| :--- | :--- | :--- |
| Mechanism | SQL view polled by Orbit | Same view, API wrapper |
| Shape | Full snapshot | Delta |
| Records | 96,000 | 96,000 |
| Cadence | 15 minutes | 5 minutes |
| Dispatch cut-off | 14:30 | 14:30 (unchanged) |
| WMS release | 8.4.1 with site customisations | 8.4.2 before UAT |

## The differences from Midlands

| Difference | Why it matters |
| :--- | :--- |
| Personalisation queue | 2,100 SKUs can never be fulfilled from another site |
| Earlier cut-off (14:30) | Delivery promise must use a different cut-off per warehouse |
| `UNAVAILABLE` has a different meaning | Includes personalisation queue, not just damage |
| WMS release lag | The 8.4.1 `UPDATED_AT` bug affects 4 % of rows |

The third row is the trap. In Glasgow's data, `UNAVAILABLE` counts items queued for personalisation,
which are genuinely not sellable, and items awaiting a quality signature, which usually are sellable
within the hour. Treating the field as one number understates availability by about 900 units a day.

The feed contract therefore splits it into `PERSONALISATION_HOLD` and `QUALITY_HOLD`, which the
Glasgow WMS team has agreed to expose in release 8.4.2. Until then availability is conservative here,
which is the right direction to be wrong in.

## Known data issues

| Issue | Volume | Handling |
| :--- | :--- | :--- |
| `UPDATED_AT` null on 4 % of rows | ~3,800 rows | Delta feed falls back to a full row comparison for those SKUs |
| Personalisation SKUs duplicated in two zones | 41 SKUs | De-duplicated by highest `ON_HAND` |
| Quality holds not cleared after sign-off | ~60 units/day | Ageing task at 24 hours |

## The personalisation rule

Personalised items are made to order and are never split, never substituted and never served from
another location. Routing already sends them here (priority 1), and the reservation worker gets the
same rule from the policy: a personalisation SKU resolves to Glasgow or to nothing.

## Why the release upgrade matters

Glasgow runs 8.4.1 plus four site customisations. UAT runs 8.4.2. The upgrade is scheduled for
2027-02-05, before UAT starts, because testing against a different release would make the feed
contract meaningless. It is a four-hour outage on a Tuesday night and the site has approved it.

## Related

[Midlands DC](./midlands-dc.md) · [Delta and snapshot](../protocol/delta-and-snapshot.md) ·
[Feed contracts](../protocol/feed-contracts.md)
