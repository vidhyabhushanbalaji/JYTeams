# Feed Incidents

Status: Agreed · Owner: Dan Whitcombe · Last updated: 2026-11-13

Five incidents from the discovery and UAT-rehearsal period. They are kept because each one changed
the design, and because a new engineer reading only the happy-path documents would rebuild the same
bugs.

## INC-001 — Truncated Midlands snapshot (2026-10-09, UAT rehearsal)

| | |
| :--- | :--- |
| Duration | 14 minutes |
| Impact | 168,000 records disappeared from availability; test orders rejected |
| Cause | A poll timed out at 8 seconds and the partial response parsed correctly |
| Detection | Snapshot completeness check (row count 20 % of previous) |
| Fix | Reject snapshots whose count is below 95 % of the previous one |

This incident is the reason [snapshot completeness](../protocol/delta-and-snapshot.md) has three checks
rather than one. The truncated response was valid JSON with a valid record count in the header,
because the header described the intended size, not the delivered one.

## INC-002 — Northgate maintenance storm (2026-10-14, staging)

| | |
| :--- | :--- |
| Duration | 20 minutes, nightly |
| Impact | Two alerts every night; on-call learned to ignore them |
| Cause | WMS maintenance rejected polls; each rejection retried three times |
| Detection | Alert fatigue, reported by the on-call engineer |
| Fix | Declared maintenance window, poll skipped, staleness clock paused |

The lesson is about alerting rather than feeding: an alert that fires every night for a known benign
condition trains people to ignore the channel, which is worse than no alert.

## INC-003 — Cursor drift at Riverside (2026-10-22, staging)

| | |
| :--- | :--- |
| Duration | 38 minutes |
| Impact | Stock figure for 1,200 bulky SKUs frozen at the previous delta |
| Cause | Delta request landed during a delivery run; LogiCore returned a delta from an older cursor |
| Detection | Cursor mismatch rule |
| Fix | Full snapshot requested automatically; staleness threshold raised to 45 min |

Riverside's delta endpoint does not fail during a delivery run, which was the surprise: it returns
the last delta it managed to generate, with a cursor from before. The cursor check caught it; without
that check the platform would have applied an old delta to a newer base and produced a figure wrong
in an unbounded way.

## INC-004 — Store file double-applied (2026-11-02, staging)

| | |
| :--- | :--- |
| Duration | 41 minutes |
| Impact | 41,000 store rows applied twice; stock doubled for the test estate |
| Cause | SFTP transfer retried after a timeout that had in fact succeeded |
| Detection | Reconciliation report, next morning |
| Fix | File timestamp check at ingest; a file older than or equal to the last applied one is ignored |

Detected by reconciliation rather than by an alert, which is the argument for the daily report even
when everything appears healthy.

## INC-005 — Quarantine field ignored (2026-11-06, UAT)

| | |
| :--- | :--- |
| Duration | 2 days, undetected |
| Impact | 61 test orders reserved against quarantined stock |
| Cause | Ingestion applied `on_hand - allocated` but not `quarantine` for two new sources |
| Detection | UAT scenario `quarantine-not-sellable` failed |
| Fix | Availability computation moved into one function; per-source field mapping tested |

The fix is architectural rather than a bug fix: the formula existed in three places and two of them
were wrong. There is now exactly one implementation, and the UAT scenario exists to keep it that way.

## What these incidents have in common

Every one was a **data-shape** failure rather than a crash, and every one was silent until something
looked at the result. That is why the platform invests in completeness checks, cursors, reconciliation
and a simulator with fault injection, rather than in retry counts.

## Related

[Failure and retry](./failure-and-retry.md) · [Reconciliation](./reconciliation.md) ·
[Stock feed failure runbook](../../launch-readiness/runbooks/stock-feed-failure.md)
