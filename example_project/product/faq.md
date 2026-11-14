# FAQ

## Is Meridian a search engine?

Not in the full-text sense. It searches the summaries and folder descriptions it generated at
import time. That is why a query phrased in the documentation's own vocabulary works well and an
unusual phrasing can miss — see [Search service](../architecture/services/search-service.md).

## Does it read my documents on every query?

No. Search reads stored summaries only. Document bodies are read once, at import, to produce a
summary. This is faster and cheaper, and it means search is read-only by construction.

## What happens to non-markdown files?

They are stored and listed but marked `summary_status: "skipped"`. They never appear in search
results and do not influence placement beyond their name. Multimodal support is on the
[roadmap](./roadmap.md).

## Can I import the same folder twice?

Yes. Identical content is hashed and stored once, and existing summaries are reused. Importing
the same tree twice does not double your document count.

## Why does placement suggest the project root?

Two reasons: either the document is genuinely top-level, or its summary is too short to match
anything. Add a paragraph of real content, or pass `path_hint`. Details in
[Placing a new document](../tutorials/placing-a-new-document.md).

## How long does an import take?

Roughly 1.5 s per file plus 0.4 s per folder on default settings, dominated by model latency.
A 50-file, 12-folder tree takes about 75 seconds. See the measured baselines in
[Service level objectives](../operations/service-level-objectives.md).

## Can two people import at once?

Not into the same project — one import per project, enforced with `409 IMPORT_IN_PROGRESS`. Different
projects import in parallel, limited by worker replicas.

## Is my documentation used to train anything?

Document text is sent to the model provider to produce summaries and placement suggestions,
under their retention terms. Prompt logging is off by default. See
[Data privacy](../security/data-privacy.md).

## Why can't I rename a folder?

Renaming changes the `ltree` path of every descendant, which would invalidate descriptions that
mention the old name. It is possible but currently requires `meridian tree move`, which
re-describes the affected subtree. Renaming from the UI is on the
[roadmap](./roadmap.md).

## Do I need an account for each project?

No. Accounts are per tenant; projects are containers inside a tenant. Roles are per tenant too —
see [Access control](../security/access-control.md).

## Can I run it air-gapped?

Not completely: summaries and placement require a model. Search and browsing work without one,
and `MERIDIAN_MODEL=stub` gives deterministic placeholder summaries for evaluation. A
self-hosted model is under consideration in the [roadmap](./roadmap.md).

## Something else?

Start with [Troubleshooting](../guides/troubleshooting.md), then `#meridian-dev`.
