"""Graph Creation section.

Turns an uploaded markdown directory into a described tree stored in Supabase Postgres
(with the files themselves in Supabase Storage):

* ``directories`` — one row per folder, carrying a description of its whole subtree;
  a *leaf* is simply a directory with no child directories. Empty directories are dropped.
* ``files`` — one row per uploaded file, carrying a short summary.
* ``creation_jobs`` — progress for the background summarisation run.

Summaries are produced bottom-up (post-order): every file first, then each directory from
its child file summaries and child directory descriptions, ending with the root, which
describes the project as a whole.
"""
