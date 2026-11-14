# Data Privacy

This page states plainly what Meridian stores, where, for how long, and how to remove it.

## What We Store

| Data | Purpose | Retention |
| :--- | :--- | :--- |
| Markdown bodies | Source of truth for summaries | Until deleted by tenant |
| Summaries and descriptions | Search and placement | Until deleted by tenant |
| File paths and names | Tree navigation | Until deleted by tenant |
| Audit rows | Security and debugging | 400 days |
| Request logs | Operations | 14 days |
| Model prompts and completions | Not stored by default | — |

Prompts are not persisted. With `MERIDIAN_LOG_PROMPTS=1` they are written to stdout for
debugging, which means they also land in the log platform — use it only in staging.

## Where It Goes

- Postgres and object storage stay in the region chosen at signup.
- Document text is sent to the model provider to produce summaries and placement suggestions.
  The provider's retention terms govern that copy; we send only the file being summarised plus
  its immediate context, never a whole project.
- Nothing is sent to a third party other than the model provider and the transactional email
  provider.

## Data Subject Requests

| Request | How |
| :--- | :--- |
| Export everything | `meridian export --project <name> --out backup.zip` |
| Delete a project | `meridian project delete <name>` |
| Delete a user's audit trail | Not available; audit rows are retained for compliance |
| Confirm what is held | `meridian audit export --actor <user>` |

Deleting a project removes rows first, then blobs that no other project references. Shared
content-addressed blobs are deliberately kept — see
[Content-addressed storage](../decisions/0002-content-addressed-blob-storage.md).

## Encryption

- In transit: TLS 1.2+ everywhere, including internal hops.
- At rest: provider-managed disk encryption; object store server-side encryption with a
  per-instance key.
- Secrets: sealed in the platform secret store, never in images or repositories.

## What Tenants Must Not Put in Documentation

Meridian summarises whatever you give it. Do not import files containing credentials, personal
data of customers, or regulated material unless your agreement allows a third-party model
provider to process it.

## Incident Notification

Any confirmed exposure of document content triggers the SEV1 path in
[Incident response](../operations/runbooks/incident-response.md), and affected tenants are
notified within 72 hours with what was exposed and what changed.

## Related
- [Threat model](./threat-model.md)
- [Access control](./access-control.md)
- [Backups and restore](../operations/backups.md)
