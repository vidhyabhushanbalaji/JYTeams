# Incident Response

Applies to anything user-visible in production. If you are unsure whether it is an incident,
open one — closing a false alarm costs five minutes.

## Severity

| Severity | Definition | Response |
| :--- | :--- | :--- |
| SEV1 | All requests failing, or data loss risk | Page on-call, incident channel, exec update in 30 min |
| SEV2 | A core flow broken for many tenants | Page on-call, incident channel |
| SEV3 | Degraded performance or one tenant affected | Ticket, next business day |
| SEV4 | Cosmetic or internal only | Backlog |

## First Ten Minutes

1. **Acknowledge** the page so the rotation knows you have it.
2. **Declare** severity in `#meridian-incident` with one line: what users see.
3. **Check** health and the overview dashboard: `curl -s $BASE/health | jq`.
4. **Stop the bleeding** before diagnosing — roll back, disable the feature flag, scale workers.
5. **Write down timestamps** as you go; memory reconstructs badly.

> Rollback is always a legitimate first move. Diagnosis happens afterwards, on a stable system.

## Useful Commands

```bash
meridian deploy --env production --tag <previous>
meridian jobs list --status running
meridian jobs cancel <job_id>
meridian storage check
meridian diagnose > diag.txt
```

## Decision Guide

| Symptom | First move | Runbook |
| :--- | :--- | :--- |
| 5xx spike after a deploy | Roll back | This page |
| Postgres unreachable | Promote replica | [Database failover](./database-failover.md) |
| TLS errors, handshake failures | Check expiry | [Certificate rotation](./certificate-rotation.md) |
| Imports stuck, queue deep | Scale workers, check model status | [Monitoring](../monitoring.md) |
| Slow searches only | Raise limit awareness, rephrase | [Troubleshooting](../../guides/troubleshooting.md) |

## Communication

- Update the incident channel every 30 minutes, even with no change: "still investigating".
- Status page updates for SEV1 and SEV2, written in user terms.
- No blame in updates; the review is where causes get examined.

## Closing Out

1. Confirm the SLI has returned to baseline for at least 30 minutes.
2. Post a summary with timeline, impact and the rollback (if any).
3. Open a follow-up issue for every contributing factor, each with an owner.
4. Review within five working days for SEV1 and SEV2, within fifteen for SEV3.

## Post-Incident Review

Blameless and short: what happened, what we saw, what we changed. Actions must be concrete and
assignable — "improve monitoring" is not an action, "alert on queue depth over 100" is.

Related: [Service level objectives](../service-level-objectives.md) — budget impact belongs in
the review.
