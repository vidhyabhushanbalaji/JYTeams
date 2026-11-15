# Database Failover

Use this when the Postgres primary is unreachable or corrupt and a replica must be promoted.
Expected recovery time is 8–12 minutes.

## Before You Start

- You need the `platform-oncall` role and access to the database console.
- Confirm it is a primary problem, not a network path: `pg_isready -h $PRIMARY_HOST`.
- Announce the action in `#meridian-incident` — writes will fail during the switch.

## 1. Confirm the Replica Is Healthy

```bash
psql "$REPLICA_URL" -c "select pg_is_in_recovery(), pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();"
```

`pg_last_wal_replay_lsn` should keep advancing. A large gap between receive and replay means the
replica is behind — promotion will lose that window of writes, so record the LSN.

## 2. Stop Writers

Scale the API and worker to zero. This prevents split-brain writes while the connection string
changes:

```bash
kubectl scale deploy meridian-api --replicas=0
kubectl scale deploy meridian-worker --replicas=0
```

## 3. Promote the Replica

```bash
pg_ctl promote -D /var/lib/postgresql/data
psql "$REPLICA_URL" -c "select pg_is_in_recovery();"   # expect f
```

## 4. Repoint the Application

Update the `MERIDIAN_DATABASE_URL` secret to the promoted host, then scale back up one API
replica first:

```bash
kubectl scale deploy meridian-api --replicas=1
curl -sf http://meridian-api/health | jq
```

Only scale the worker once health is `ok`; the worker will otherwise burn retries.

## 5. Recover Jobs

Jobs whose lease expired during the outage resume automatically within five minutes. Check
before intervening:

```bash
meridian jobs list --status running
```

Cancel anything that has been running longer than three times its estimated duration.

## 6. Verify Data

Run the invariant queries from [Backups and restore](../backups.md). Counts should match the
last known totals within the LSN gap you recorded in step 1.

## 7. Follow Up

- Rebuild the old primary as a new replica from the promoted node.
- Write a timeline into the incident channel.
- Open an action for the LSN gap: was data lost, and can that window shrink?

## If There Is No Replica

Restore from [Backups and restore](../backups.md) instead. This is a SEV1 and the restore point
decides how much history is lost.
