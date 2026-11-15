# ADR 0003: One Model Call per Folder, No Expansion Budget

- **Status:** accepted
- **Date:** 2026-06-02
- **Deciders:** search & indexing team
- **Supersedes:** the two-call "which files" + "which subfolders" design

## Context

Search walks the tree. The first design made two calls per folder: one to find matching files,
one to choose subfolders to open. Measured on a 120-folder tree that was 240 calls, roughly 14
seconds, and the two answers occasionally disagreed — files were returned from a folder whose
subfolders the model had refused to open.

Alternatives considered:

1. Embed every summary in a vector store, retrieve top-k, then walk to answer.
2. Ask the model once per folder, for both answers, with no cap on expansion.
3. Ask once per folder with a hard expansion budget (e.g. top 2 subfolders).

## Decision

Combine both questions into one call per folder, and open **every** subfolder the model marks as
potentially relevant. No expansion budget by default.

Additionally: if nothing is logged and the project has at most 40 documents, sweep every folder
once. Setting `MERIDIAN_SEARCH_MAX_FOLDERS` opts into a cap and disables the fallback.

## Rationale

- **Consistency:** one call cannot disagree with itself. Files and subfolder decisions come from
  the same reasoning step.
- **Cost follows relevance:** a narrow query costs a handful of calls; a broad query costs more
  because it genuinely touches more of the tree. That is the correct gradient.
- **Pruning stays meaningful:** a folder description is derived evidence, so skipping a branch
  is justified by the description rather than by a heuristic.

## Consequences

**Good**

- Half the calls and roughly half the latency of the previous design.
- Simpler prompt, simpler code path, fewer failure modes.
- Latency correlates with relevance, which users perceive as "it thought about it".

**Bad**

- A misleading folder description can hide a whole branch. Mitigated by the fallback sweep for
  small projects and by the ability to set a cap.
- Worst case is a full traversal of a large tree, which is expensive. Accepted because it
  requires the model to find every branch relevant.
- Relevance scores across different calls are not comparable, forcing a single consolidation
  call to rank results.

**Neutral**

- Document bodies are still never read during search; a query phrased outside the docs'
  vocabulary may miss. See [Data privacy](../security/data-privacy.md) for why we do not want
  to start reading them casually.

## Alternatives Rejected

| Alternative | Why |
| :--- | :--- |
| Vector store top-k then walk | Loses the "why" behind a branch; needs a second index to keep in sync |
| Budget of top 2 subfolders | Cheap, but silently drops correct branches; failures are invisible |
| Two calls per folder | Consistency problems, twice the latency |

## Review

Revisit if mean `folders_visited` on real traffic exceeds 60, or if the fallback sweep fires on
more than 10% of queries. Both signals mean descriptions are too vague to prune.
