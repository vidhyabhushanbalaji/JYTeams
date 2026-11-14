# ADR 0001: Represent the Tree With Postgres `ltree`

- **Status:** accepted
- **Date:** 2026-03-04
- **Deciders:** platform team
- **Supersedes:** the adjacency-list-only prototype

## Context

A documentation set is a directory hierarchy. We need to answer three questions quickly:

1. What are the children of this folder?
2. What is in this entire subtree?
3. What is the ancestor chain from a node to the root?

The prototype stored only `parent_id`. Question 2 required a recursive CTE per request, and the
search walk needed the whole subtree before it could decide anything.

## Decision

Store both:

- `parent_id` — adjacency list, for exact children and referential integrity.
- `path ltree` — the materialised position, e.g. `operations.runbooks.database-failover`.

Subtree reads become one operator: `path <@ 'operations.runbooks'::ltree`. Ordering by `path`
gives a stable depth-first traversal with `ORDER BY path`, which is what the UI and the search
walk both want.

## Consequences

**Good**

- Subtree queries are a single index scan (GIST on `path`).
- Ordering is deterministic without a recursive sort.
- Ancestor lookups are a string prefix operation, not a loop.

**Bad**

- `ltree` labels cannot contain dots; folder names are normalised, and a separate `name` column
  keeps the original for display.
- Renaming or moving a folder rewrites `path` for every descendant.
- The extension must be installable in every target Postgres — true for our managed offering,
  not for some stripped images.

**Neutral**

- We still keep `parent_id`; it costs one column and makes integrity checks trivial.

## Alternatives Considered

| Alternative | Why rejected |
| :--- | :--- |
| Adjacency list only | Recursive CTE per subtree read; too slow on a 400-node tree |
| Materialised path as text | No containment operator, manual prefix matching, worse indexes |
| Nested sets | Correct but every insert rewrites many rows |
| Graph database | Operationally heavy for a strict hierarchy; see the retirement notes |

## Follow-Up

Rename support was deferred; `meridian tree move` re-describes affected subtrees and is
documented as a known gap in the [FAQ](../product/faq.md).
