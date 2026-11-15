# Runbook — Stock Feed Failure

**Symptom:** a warehouse's stock is missing from availability, or its number looks wrong. Customers may
see a fallback date for products stocked there.

**Customer impact today:** unknown until you check step 3. If the warehouse is excluded, that stock is
unsellable but nothing is wrong; if it is included and stale, every sale from it is a risk.

## 1. Confirm what you are seeing (2 minutes)

| Check | Where | Means |
| :--- | :--- | :--- |
| Last batch timestamp per source | `/health` dashboard | Stale or current |
| Excluded sources | Availability dashboard | Automatic protection is working |
| Quarantine row count | Ingestor metrics | One SKU or many |
| Alert channel | `#truestock-platform` | Cursor or completeness failure |

Do not restart anything before this step. Two of the three previous incidents were resolved by waiting
for the next cycle.

## 2. Decide whether the platform is protecting itself (1 minute)

| State | Action |
| :--- | :--- |
| Source excluded automatically | Go to step 4; the guard is working |
| Source included but stale (degraded) | Apply a manual hold now: step 3 |
| Source current, numbers wrong | Suspect the warehouse, not the feed: step 5 |

## 3. Apply a manual hold (1 minute)

1. Open the admin console, `Warehouse holds`.
2. Select the source, choose reason `feed_data_doubt`.
3. Confirm; new reservations for that source stop within 60 seconds.
4. Post in `#truestock-platform`: source, time, reason.

Existing reservations are kept. Never release them to "clean up"; they expire on their own.

## 4. Check the source (5 minutes)

| Question | How |
| :--- | :--- |
| Is the source system up? | Vendor status page or site contact |
| Did the last batch fail validation? | `feed.rejected` table, reason column |
| Was the cursor rejected? | Ingestor log, `cursor_mismatch` |
| Is it the declared maintenance window? | Northgate 02:00–02:20; check the clock before doing anything |

A cursor mismatch resolves itself: the ingestor requests a full snapshot, which takes 11 seconds at
Northgate and 11 minutes at Riverside. Wait for it.

## 5. If the data is current but wrong

| Symptom | Likely cause | Action |
| :--- | :--- | :--- |
| One SKU wrong | Mapping or adjustment | Check Atlas for a duplicate SKU |
| A block of SKUs wrong | Quarantine not applied | Check the feed's quarantine field mapping |
| Everything wrong | Wrong source or wrong location | Stop the ingestor for that source and page Dan |

## 6. Recover

1. Ask for a fresh batch, or wait for the next cycle.
2. Confirm the timestamp advanced and the row count is within 5 % of the previous batch.
3. Remove the manual hold.
4. Check reservations resume within 60 seconds.
5. Note the incident ID in the daily checkpoint.

## 7. Escalate

| When | To | How |
| :--- | :--- | :--- |
| Excluded more than 30 minutes | Dan Whitcombe | Phone |
| Both own DCs excluded | Marcus Feld and Nadia Kerr | Incident bridge |
| Data wrong in a way you cannot explain | Dan, then Nadia | Page |

## Never do

| Never | Why |
| :--- | :--- |
| Restart the ingestor repeatedly | It will not fix a cursor and it delays the snapshot |
| Release existing reservations | Creates a second problem |
| Correct stock manually in the source system | The feed will overwrite it and audit will not match |
| Tell support to quote a date | Availability is unreliable until recovery |

## Related

[Stale stock handling](../../stock-feeds/reliability/stale-stock-handling.md) ·
[Failure and retry](../../stock-feeds/reliability/failure-and-retry.md) ·
[Feed incidents](../../stock-feeds/reliability/feed-incidents.md)
