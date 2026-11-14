"""Graph AI Search section.

Answers "which document deals with this?" from the tree Graph Creation built, without reading
the documents themselves — the stored per-file summaries and per-directory descriptions are
the index.

The agreed algorithm lives in ``search.py``: start at the root, log every child file whose
summary matches the query, recurse into every child folder whose description matches, and
keep going until the frontier is empty. There is no expansion budget; a small project that
finds nothing by that route gets one exhaustive sweep instead. The logged files are then
ranked in a single consolidation pass (batched when the log is large), because relevance
values from separate model calls are not comparable.

Read-only: no tables of its own, no job rows, no writes to the project.
"""
