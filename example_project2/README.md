# Meridian

Meridian turns an unstructured folder of markdown into a navigable knowledge tree. You import
a documentation set once, Meridian summarises every file and every folder, and from then on you
can search the tree or add a new document straight into the folder where it belongs.

## Features
- **Hierarchical summaries:** every file gets a short summary; every folder gets a description written from its children.
- **Guided placement:** a new document is matched against the tree and offered a short list of candidate folders.
- **Tree-aware search:** queries are answered by walking folders, not by scanning every file.
- **Content-addressed storage:** identical documents are stored once, no matter how often they are imported.

## Quick Start
1. Install the CLI: `npm install -g @meridian/cli`
2. Authenticate: `meridian login`
3. Import a documentation folder: `meridian import ./docs --project handbook`
4. Search it: `meridian search --project handbook "how do I rotate certificates?"`

## Documentation Map

| Area | Start here |
| :--- | :--- |
| Install and configure | [Installation](./getting-started/installation.md) · [Configuration](./getting-started/configuration.md) |
| How the system works | [Architecture overview](./architecture/overview.md) · [Data model](./architecture/data-model.md) |
| HTTP surface | [Authentication](./api/authentication.md) · [Endpoints](./api/endpoints/projects.md) |
| Day-to-day work | [Local development](./guides/local-development.md) · [Testing](./guides/testing.md) |
| Running it in production | [Monitoring](./operations/monitoring.md) · [Incident response](./operations/runbooks/incident-response.md) |
| Why it looks like this | [Decision records](./decisions/0001-use-postgres-ltree.md) |

## Repository Layout

```text
meridian/
├─ apps/
│  ├─ api/          # HTTP API and job workers
│  └─ web/          # browser client
├─ packages/
│  ├─ summariser/   # model prompts and consolidation logic
│  └─ shared/       # schemas, types, error codes
├─ deploy/          # container and infrastructure definitions
└─ docs/            # this documentation set
```

## Project Status
Meridian is at `1.x`: import, placement and search are all generally available. Multimodal
import (images and PDFs) is still in preview — see the [roadmap](./product/roadmap.md).
