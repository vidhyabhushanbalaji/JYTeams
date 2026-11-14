"""Graph Creation section.

Turns an uploaded markdown directory into a described tree stored in Supabase Postgres
(with the files themselves in Supabase Storage):

* ``directories`` — one row per folder, carrying a description of its whole subtree;
  a *leaf* is simply a directory with no child directories. Empty directories are dropped.
* ``files`` — one row per uploaded file. Documents are *not* summarised: the folder that holds
  them carries the description, so import costs one model call per folder.
* ``creation_jobs`` — progress for the background describing run.

Descriptions are produced bottom-up (post-order): each folder is described from the text of the
files directly inside it and the descriptions of its child folders, ending with the root, which
describes the project as a whole.
"""
