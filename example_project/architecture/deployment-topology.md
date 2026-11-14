# Deployment Topology

Meridian runs as two stateless services in front of two stateful ones. Everything scales
horizontally except Postgres.

## Topology

| Service | Replicas | Scaling signal | State |
| :--- | :--- | :--- | :--- |
| `meridian-api` | 2+ | CPU, p95 latency | None |
| `meridian-worker` | 1+ | Queue depth (`import_jobs` queued) | None |
| `postgres` | 1 primary + 1 replica | Connections, WAL lag | Persistent |
| `minio` / S3 | managed | Throughput | Persistent |

## Network Layout

```text
public ──▶ ingress (TLS) ──▶ meridian-api ──▶ postgres (private)
                                     │
                                     └──────▶ object store (private)

meridian-worker ──▶ postgres, object store, model API (egress allowlist)
```

The worker needs outbound access to the model API; the API service does not. Keep the egress
allowlist tight — the threat model in [Threat model](../security/threat-model.md) assumes it.

## Resource Guidance

| Workload | CPU | Memory | Notes |
| :--- | :--- | :--- | :--- |
| API | 0.5 vCPU | 512 MiB | Mostly I/O bound |
| Worker, import | 1 vCPU | 1 GiB | Parallel summary calls |
| Worker, search | 1 vCPU | 1 GiB | Burst to 2 vCPU on wide trees |

## Configuration Differences per Environment

| Setting | Staging | Production |
| :--- | :--- | :--- |
| `MERIDIAN_AUTH_MODE` | `token` | `token` |
| `MERIDIAN_LOG_LEVEL` | `debug` | `info` |
| `MERIDIAN_SEARCH_MAX_FOLDERS` | unset | `120` |
| Backups | nightly, kept 3 days | nightly + weekly, kept 90 days |

## Failure Behaviour

- **Worker restarts** requeue the leased job; stages are idempotent, so no duplicate nodes.
- **API restarts** drop in-flight job streams; clients reconnect using the last seen cursor.
- **Postgres replica lag** only affects read-only reporting; all writes go to the primary.
- **Object store outage** fails the import at stage 1 with a clear error rather than a partial tree.

Recovery steps for the two most likely incidents are written up as
[database failover](../operations/runbooks/database-failover.md) and
[certificate rotation](../operations/runbooks/certificate-rotation.md).
