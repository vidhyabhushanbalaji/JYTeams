# Access Control

Two roles exist today and both operate within a tenant. Folder-level permissions are a known gap.

## Roles

| Role | Can do | Cannot do |
| :--- | :--- | :--- |
| `viewer` | Read projects, run searches | Import, add, delete |
| `editor` | Everything a viewer can, plus import, add, delete | Manage tokens or members |
| `admin` | Manage members, tokens and webhooks | Cross-tenant access |

Roles are assigned per tenant, not per project. A project-scoped service token grants `editor`
rights on exactly one project.

## Enforcement Points

| Layer | Enforces |
| :--- | :--- |
| Auth module | Token validity, tenant and user resolution |
| Route guard | Role required by the endpoint |
| Repository | `tenant_id` filter on every query |
| Storage | Per-tenant key prefix in blob paths |

The repository filter is the important one: authorisation checks can be forgotten in a new
handler, but a missing `tenant_id` predicate fails tests immediately.

## Decision Table

| Action | viewer | editor | admin |
| :--- | :--- | :--- | :--- |
| List projects | ✅ | ✅ | ✅ |
| Read a document | ✅ | ✅ | ✅ |
| Search | ✅ | ✅ | ✅ |
| Create a suggestion | ❌ | ✅ | ✅ |
| Commit a placement | ❌ | ✅ | ✅ |
| Import a tree | ❌ | ✅ | ✅ |
| Delete a project | ❌ | ✅ | ✅ |
| Issue tokens | ❌ | ❌ | ✅ |
| Manage webhooks | ❌ | ❌ | ✅ |

## Service Tokens

```bash
meridian token create --project handbook --role editor --ttl 24h
```

Tokens are shown once. Narrow `--ttl` and `--project`; a token that outlives its CI job is a
liability. Revocation is immediate — the JWKS key set is unaffected.

## What Is Missing

Folder-level permissions. Today, an editor can add a document anywhere in the tree, and a viewer
sees every folder. The design sketch for per-folder grants is in the
[roadmap](../product/roadmap.md); it requires a new table and an additional predicate, so it is
a minor release, not a patch.

## Audit

Every mutating endpoint writes an audit row: actor, action, target, `request_id`. Audit rows are
append-only and retained for 400 days. Queries are documented in
[Glossary](../reference/glossary.md) under *audit row* and exported by
`meridian audit export`.

Related: [Threat model](./threat-model.md) and [Data privacy](./data-privacy.md).
