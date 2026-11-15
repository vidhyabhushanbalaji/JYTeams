# Deployment

Deployments are image-based and forward-only. One command promotes a build through staging and
production; there is no separate release branch.

## Pipeline

```text
push → lint + unit → build image → integration → staging deploy → smoke → manual approval → production
```

The approval gate exists because production migrations are applied automatically on boot.

## Deploying

```bash
meridian deploy --env staging --tag 1.8.2
meridian deploy --env production --tag 1.8.2
```

Or from CI, tag the commit: `git tag v1.8.2 && git push --tags`.

## What Happens on Boot

1. The API runs pending migrations (advisory-locked, so only one replica applies them).
2. The worker starts and registers a lease heartbeat.
3. Readiness reports `503` until `SELECT 1` and a storage `HEAD` both succeed.

Rollout is rolling with a 30-second drain. In-flight imports finish on the old pod because the
job lease is longer than the drain window.

## Pre-Deploy Checklist

| Check | Why |
| :--- | :--- |
| Changelog entry added | Users need to know what changed |
| Migration reviewed by a second engineer | Forward-only, no rollback |
| Staging smoke test passed | Catches config drift |
| Dashboards watched for 10 minutes after | Alert noise is the fastest signal |

## Rollback

```bash
meridian deploy --env production --tag 1.8.1
```

Images roll back cleanly; schema does not. Every minor release must therefore be
schema-compatible with the previous minor — enforce this in review, see
[Review checklist](../contributing/review-checklist.md).

## Smoke Test

```bash
curl -sf http://staging.meridian.example.com/health
meridian import ./fixtures/smoke --project smoke --wait
meridian search --project smoke "failover" | head -5
```

Expected: health is `ok`, the import finishes under 60 s, and search returns at least one hit.

## Related
- [Deployment topology](../architecture/deployment-topology.md)
- [Release process](../contributing/release-process.md)
- [Monitoring](../operations/monitoring.md)
