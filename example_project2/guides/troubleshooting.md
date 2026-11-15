# Troubleshooting

Start with the health endpoint. It tells you which dependency is unhappy, which usually halves
the search space.

```bash
curl -s http://localhost:8080/health | jq
```

## Symptom Index

| Symptom | Likely cause | Where to go |
| :--- | :--- | :--- |
| `database: "error"` | Postgres down, wrong URL, missing extension | [Local development](./local-development.md) |
| `storage: "error"` | Bucket missing, bad credentials | Below |
| Import stuck at `summarise_files` | Model rate limit or key exhausted | Below |
| Import finished, tree empty | Everything pruned as empty directories | Below |
| Search returns nothing | Vocabulary mismatch or `max_folders` too low | Below |
| 401 on every call | Clock skew or stale key cache | [Authentication](../api/authentication.md) |
| Placement suggests the root only | Document summary too short or too generic | Below |

## Storage Errors

```bash
meridian storage check
# → bucket meridian-docs: missing
pnpm storage:init
```

If credentials are correct but uploads still fail, confirm the endpoint has no trailing slash —
`S3` clients differ and this is the single most common misconfiguration.

## Import Stuck

1. Check worker logs for `MODEL_TIMEOUT` or `429` — both retry automatically.
2. Verify the worker is leasing jobs: `meridian jobs list --status running`.
3. If a lease looks orphaned, wait five minutes for expiry rather than forcing a delete.
4. Cancel cleanly with `meridian jobs cancel <id>`; nodes not yet described roll back.

## Tree Is Empty After Import

Every directory was pruned because no markdown was found beneath it. Confirm the archive
contains `.md` files and that `MERIDIAN_SKIP_EXTENSIONS` is not swallowing everything. Re-run
with `--prune-empty=false` to see the unpruned shape.

## Search Returns Nothing

| Try | Why |
| :--- | :--- |
| Rephrase using words from the docs | Search matches summaries, not bodies |
| Remove `max_folders` | A cap also disables the fallback sweep |
| Check `folders_visited` in the response | Very low values mean the walk pruned early |
| Run with a 2-word query | Long questions dilute the signal per folder |

## Weak Placement Suggestions

A summary of fewer than 100 characters gives the walk little to match. Add a paragraph of real
content, or pass `path_hint` in the request.

## Collecting Diagnostics

```bash
meridian diagnose > meridian-diag.txt
```

Includes versions, resolved config (secrets redacted), recent job summaries and health output.
Attach it to any support request along with the `request_id` from the failing call.

## Still Stuck

Open a discussion in `#meridian-dev` with the diagnostic file. If it is user-visible in
production, follow [Incident response](../operations/runbooks/incident-response.md) instead.
