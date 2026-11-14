"""Graph Add section.

Places a single markdown document into an existing project tree, with the user in the loop:

* the document is summarised, then the tree is walked semantically to find the folders whose
  descriptions align with it (``navigate.py``); the resulting candidates are ranked, and
  the ranked list is what the wizard shows;
* the user picks a location — or asks for a new folder at that point — and ``service.place``
  writes the row, then re-describes the affected directories bottom-up so the tree keeps the
  invariant Graph Creation established.

Uploaded bytes and suggestions live on an ``add_requests`` row between the two steps
(``supabase/migrations/0002_graph_add.sql``), so placement never re-uploads or re-summarises
the document.
"""
