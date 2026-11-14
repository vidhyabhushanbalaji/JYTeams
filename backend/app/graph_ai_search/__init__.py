"""Graph AI Search section.

Answers "which document deals with this?" from the tree Graph Creation built. Search calls no
model: the query is matched locally against the stored folder descriptions (which decide which
branches to open) and against the documents' own text (which decides which files match), so a
search costs no prompts and no quota.

The algorithm lives in ``search.py``: start at the root, score the files directly inside every
opened folder, open every child folder whose description clears the vocabulary threshold, and
keep going until the frontier is empty. A project that matches nothing that way gets one
exhaustive sweep, so a vague description cannot hide a branch. Scoring is one shared function
(``app.core.text``), so the ordering needs no consolidation call.

Read-only: no tables of its own, no job rows, no writes to the project.
"""
