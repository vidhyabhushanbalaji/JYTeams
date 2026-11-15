# Damaged and Quarantine Stock

Status: Agreed · Owner: Sofia Mendes · Last updated: 2026-11-06

Every warehouse holds stock that exists physically but must not be sold: damaged items awaiting
write-off, supplier returns, quality holds and stock awaiting investigation. Today some of it is
counted as available, which is one of the quiet causes of oversell.

## What counts as quarantine

| Reason | Who applies it | Typical duration | Sellable |
| :--- | :--- | :--- | :--- |
| Damage found at pick | Warehouse | Until write-off, 1–5 days | No |
| Quality hold from supplier | Quality team | Days to weeks | No on release only |
| Stock awaiting investigation | Fulfilment management | Up to 14 days | No |
| Recall | Brand team | Until cleared | No |
| Client hold (Northgate only) | Northgate's own client | Unknown | Never ours to sell |
| Awaiting put-away | Warehouse | Hours | Not yet |

## How it appears in the feeds

| Warehouse | Field | Current behaviour |
| :--- | :--- | :--- |
| Midlands DC | `unavailable_quantity` | Sent, but Mercury ignores it |
| Glasgow DC | `unavailable_quantity` | Sent, ignored |
| Northgate | `on_hold_for_client` | Sent, partially applied |
| Riverside | `quarantine` | Sent and applied correctly |
| Stores | None | Damage written off manually |

The pattern is the same everywhere: the data exists and the consumption is inconsistent. Under
Truestock, availability is `on_hand - allocated - quarantine`, computed once in the feed ingestor so
no downstream system can forget a term.

## The August incident

A pallet of 240 garden planters arrived against the wrong purchase order, was placed in quarantine
for investigation, and stayed there for nine days. Mercury counted them as available for the whole
period, 61 orders were accepted, and every one was cancelled by phone. The write-off was £4,900 and
the goodwill cost was never counted.

Nothing in that sequence was a mistake by an individual. The lesson is that quarantine must be a
**first-class state in the availability calculation**, not a field somebody remembers to subtract.

## Rules

| Rule | Detail |
| :--- | :--- |
| RSV-13 | Quarantined units are never available |
| Quarantine ageing | Any unit in quarantine over 14 days raises a task |
| Write-off | Removes the unit from `on_hand` at the next feed; no separate event needed |
| Returns to supplier | Treated as quarantine until the supplier collects |
| Store damage | Written off in StorePOS; visible to availability from the hourly file |

## What good looks like

The target is that a unit enters quarantine within 15 minutes of being identified and leaves
availability at the same moment. Today the average is 2 hours for warehouse stock and 14 hours for
store stock. The measure is reported weekly in the operations dashboard as "quarantine lag".

## Related

[Returns and restock](./returns-and-restock.md) · [Feed contracts](../../stock-feeds/protocol/feed-contracts.md) ·
[Warehouse supervisor interview](../../current-state/interviews/warehouse-supervisor-interview.md)
