# Quick Start

This walkthrough imports three small folders of markdown, then searches them. It takes about
five minutes and needs nothing beyond a running Meridian instance.

## 1. Create a Project

A project is the container for one documentation tree.

```bash
curl -X POST http://localhost:8080/api/projects \
  -H "Authorization: Bearer $MERIDIAN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"handbook","description":"Engineering handbook"}'
```

The response contains a project `id` — keep it for the next steps.

## 2. Import a Folder

```bash
meridian import ./docs \
  --project handbook \
  --watch
```

`--watch` streams progress: files are summarised first, then folders bottom-up. On a 60-file
set this takes roughly two minutes.

## 3. Inspect the Tree

```bash
meridian tree --project handbook --depth 2
```

Every node prints its description in one line, for example:

```text
handbook/
├─ getting-started/  Install, configure and run Meridian for the first time.
└─ operations/       On-call procedures, alerting and recovery runbooks.
```

## 4. Search

```bash
meridian search --project handbook "what happens during a database failover?"
```

Each hit includes the file path, its summary and a `relevance` score between 0 and 1.

## 5. Add a New Document

```bash
meridian add ./draft/new-alert-runbook.md --project handbook
```

Meridian suggests candidate folders, you pick one, and the ancestors are re-described so the
tree description stays accurate. The full flow is in
[Placing a new document](../tutorials/placing-a-new-document.md).

## Where to Go Next
- [Configuration](./configuration.md) — tune chunk sizes, model and storage backend.
- [API authentication](../api/authentication.md) — if you would rather call the API directly.
- [Glossary](../reference/glossary.md) — every Meridian-specific term in one place.
