# Environments

Status: Draft · Owner: Nadia Kerr · Last updated: 2026-11-13

How the platform's environments are built, what differs between them, and what a release actually does.
The test-facing view is in [test environments](../../customer-testing/strategy/environments.md); this is
the infrastructure view.

## The environments

| Environment | Cluster | Instances | Database | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| Local | Docker Compose | 1 each | Local Postgres | Development |
| CI | Ephemeral | 1 each | Ephemeral Postgres | Automated tests |
| Integration | Shared, small | 1 each | Shared, seeded | Feed and carrier work |
| UAT | Shared, medium | 4 each | Restored nightly | Acceptance |
| Staging | Production-shaped | 8 each | Production-shaped | Rehearsal |
| Production | Multi-zone | 8–16 | HA with replica | Live |

## Infrastructure

| Component | Technology | Notes |
| :--- | :--- | :--- |
| Container platform | Managed Kubernetes | Two zones in production |
| Database | Managed Postgres 16 | Primary plus read replica |
| Cache | Managed Redis 7 | Cluster mode in production |
| Event bus | Managed Kafka, 3 brokers | `truestock-events` |
| Object storage | Bucket per environment | Feed batches and evidence |
| Secrets | Managed secret store | Per environment, no sharing |
| Ingress | Managed load balancer, TLS | mTLS internally |

## Configuration

| Source | Precedence |
| :--- | :--- |
| Environment variables | Base |
| Secret store | Overrides secrets |
| Policy configuration table | Overrides business keys at runtime |
| Admin console | Final override for business keys |

The separation is deliberate: platform configuration moves with a deployment, business rules move with
a person and an audit entry.

## Release process

| Step | Detail | Time |
| :--- | :--- | :--- |
| 1 | Build image, tag with commit | 6 min |
| 2 | Deploy to integration, run smoke tests | 8 min |
| 3 | Deploy to UAT, run regression subset | 25 min |
| 4 | Deploy to staging, run full regression | 45 min |
| 5 | Approve for production | Human |
| 6 | Blue/green deploy, shift 10 % traffic | 5 min |
| 7 | Observe 5 minutes, shift 100 % | 5 min |
| 8 | Keep old version warm 30 minutes | — |

Step 8 is what makes a three-minute rollback possible.

## Database changes

| Rule | Why |
| :--- | :--- |
| Migrations are forward-only | Rollback of a schema is harder than rollback of code |
| Every migration is additive for one release | Old code must run against the new schema |
| Destructive changes are two releases apart | Stop writing, then drop |
| A migration must complete in under 60 seconds | Long locks during trading hours |

## Access

| Environment | Who | Controls |
| :--- | :--- | :--- |
| Local | Everyone | None |
| Integration, UAT | Team and testers | SSO, role-based |
| Staging | Engineering, SRE | SSO, MFA |
| Production | SRE and approvers | SSO, MFA, break-glass with an audit entry |

## Related

[Observability](./observability.md) · [Security architecture](./security-architecture.md) ·
[Release process](../../programme/plan/milestones.md)
