# Backups and Restore

Two things need backing up: Postgres (the tree) and the object store (the blobs). Neither is
useful without the other, so restores are always rehearsed as a pair.

## Schedule

| Target | Method | Frequency | Retention |
| :--- | :--- | :--- | :--- |
| Postgres | `pg_basebackup` + WAL archive | continuous | 7 days point-in-time |
| Postgres | logical dump (`pg_dump -Fc`) | nightly | 30 days |
| Object store | bucket versioning + replication | continuous | 90 days |
| Config and secrets | sealed secret backup | on change | indefinite |

Point-in-time recovery is the primary mechanism; the nightly dump exists for the case where a
migration needs a forensic look at yesterday's shape.

## Verifying a Backup

A backup nobody restored is a rumour. The weekly job restores the newest dump into a scratch
database and runs the invariant queries:

```sql
-- every non-root directory has exactly one parent
SELECT count(*) FROM directories d
WHERE d.parent_id IS NULL AND d.is_root = false;

-- counts agree with reality
SELECT d.id
FROM directories d
JOIN files f ON f.directory_id = d.id
GROUP BY d.id
HAVING d.file_count <> count(f.id);
```

Both queries must return zero rows. Failures page the platform team under
[Incident response](./runbooks/incident-response.md).

## Restore Procedure

1. Provision a fresh Postgres instance with the `ltree` and `pg_trgm` extensions available.
2. Restore to a target timestamp: `restore_target_time='2026-11-14 18:00:00Z'`.
3. Restore object-store keys for the same window; blobs are content-addressed so overlap is harmless.
4. Run the invariant queries above.
5. Point `MERIDIAN_DATABASE_URL` and `MERIDIAN_STORAGE_URL` at the restored pair.
6. Boot with `MERIDIAN_READ_ONLY=1` first, smoke test, then enable writes.

## What Is Not Backed Up

- In-flight job progress. Jobs resume from the last committed stage; work in the current stage
  is recomputed. Cost, not correctness.
- Browser sessions and cached JWKS — both re-derive on demand.
- Search results. Nothing is cached across requests by design.

## Retention Rationale

Blob retention is longer than database retention because a restored older tree may reference
blobs written after the restore point. Deleting blobs too eagerly would break
`download_url` for recovered rows.

## Restore Drill

Quarterly, restore into staging and run the smoke test from
[Deployment](../guides/deployment.md). Record the outcome and the wall-clock duration in the
runbook log — the drill is only useful if the numbers are tracked.
