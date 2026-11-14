# CLI Reference

The CLI wraps the HTTP API. Every command accepts `--json` for scripting and `--project` to avoid
repeating the target.

## Global Options

| Option | Description |
| :--- | :--- |
| `--project <name>` | Default project for the command |
| `--json` | Machine-readable output |
| `--api <url>` | Override the API base URL |
| `--verbose` | Print request ids and timings |
| `--help` | Per-command help |

## Authentication

```bash
meridian login                        # browser flow, stores a refreshed token
meridian logout
meridian token create --project handbook --role editor --ttl 24h
meridian token revoke <token_id>
meridian auth test                    # verifies the current token
```

## Import and Trees

```bash
meridian import ./docs --project handbook --wait
meridian import ./docs.zip --project handbook --replace
meridian tree --project handbook --depth 2
meridian tree --project handbook --json | jq '.. | .path?'
meridian reindex --project handbook --failed
meridian tree move operations/runbooks operations/incidents --project handbook
```

`--wait` blocks until the job ends and exits non-zero on failure, which is what you want in CI.

## Search and Placement

```bash
meridian search --project handbook "how do I rotate certificates?"
meridian search --project handbook "failover" --limit 5 --json
meridian add ./draft/new-page.md --project handbook            # interactive
meridian add ./draft/new-page.md --project handbook --folder operations/runbooks
```

`add` without `--folder` shows candidates with their reasons and lets you pick, including
creating a new folder at the chosen point.

## Jobs

```bash
meridian jobs list --status running
meridian jobs wait <job_id>
meridian jobs cancel <job_id>
meridian jobs logs <job_id> --follow
```

## Operations

```bash
meridian health
meridian config check
meridian storage check
meridian diagnose > meridian-diag.txt
meridian keys rotate --publish-only --kid k-2026-02
meridian audit export --actor user_8f21 --since 2026-10-01
```

## Exit Codes

| Code | Meaning |
| :--- | :--- |
| 0 | Success |
| 1 | Command failed (API returned an error) |
| 2 | Usage error — bad flag or missing argument |
| 3 | Authentication required or expired |
| 4 | Job finished with `failed` status |
| 5 | Timeout waiting for a job |

## Environment

`MERIDIAN_TOKEN` supplies a token without a login flow, and `MERIDIAN_API` overrides the base URL.
Both are useful in CI; neither is written to disk.

## Related
- [Quick start](../getting-started/quickstart.md)
- [Troubleshooting](../guides/troubleshooting.md)
