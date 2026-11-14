# Tutorial: Import Your First Project

This tutorial imports a small handbook, inspects the generated tree, and verifies that the root
summary actually describes the whole set. It assumes Meridian is running locally — see
[Installation](../getting-started/installation.md) if not.

## The Sample Tree

Create these five files. The nesting is deliberate: one deep branch, one flat folder, one file at
the root.

```text
handbook/
├─ README.md
├─ setup/
│  └─ local-environment.md
├─ services/
│  ├─ billing.md
│  └─ identity/
│     └─ tokens.md
└─ oncall/
   └─ escalation.md
```

Give each file a couple of real paragraphs. Single-line files produce weak summaries, which makes
the rest of the tutorial less interesting.

## 1. Import

```bash
meridian import ./handbook --project handbook --wait
```

Expected output:

```text
queued   job_2f81
running  stage=validate        nodes=0/7
running  stage=summarise_files nodes=5/7
running  stage=describe_folders nodes=6/7
done     status=succeeded nodes=7 duration=31.4s
```

## 2. Inspect the Tree

```bash
meridian tree --project handbook
```

```text
handbook/
├─ setup/      Instructions for preparing a developer workstation.
├─ services/   Service-level documentation, including identity and billing.
│  └─ identity/ How authentication tokens are issued and rotated.
├─ oncall/     Escalation paths and expectations for the on-call engineer.
└─ README.md   Overview of the handbook and how to navigate it.
```

Notice that `services/` mentions both its file (`billing.md`) and its child folder — a folder
description is built from both.

## 3. Check the Root Summary

```bash
meridian project show handbook --json | jq -r .root_summary
```

You should get one or two sentences covering setup, services and on-call. If the root summary
only mentions one area, a child summary was probably too thin — see
[Troubleshooting](../guides/troubleshooting.md).

## 4. Confirm Deduplication

```bash
meridian import ./handbook --project handbook --wait
meridian project show handbook --json | jq '.documents'
```

The count is unchanged. Identical content hashed to the same blobs, and existing summaries were
reused — see [ADR 0002](../decisions/0002-content-addressed-blob-storage.md).

## 5. Try a Search

```bash
meridian search --project handbook "how are tokens rotated?"
```

`services/identity/tokens.md` should rank first, with `folders_visited` around 3 or 4. If
`folders_visited` equals the folder count, the fallback sweep ran — a sign the query used
vocabulary the docs do not.

## Next

Move on to [Placing a new document](./placing-a-new-document.md) to add a page to this tree.
