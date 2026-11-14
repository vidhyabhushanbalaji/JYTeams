"""Graph Add section.

Places a single markdown document into an existing project tree, with the user in the loop:

* the tree is scanned locally — every folder is scored against the document's own vocabulary
  (``scoring.py``, ``navigate.py``), using the same weights Graph AI Search uses, so a document
  is offered the folders a search would look in. No model is called;
* the user picks a location — or asks for a new folder at that point — and ``service.place``
  writes the row, then updates the affected folder descriptions (the new folder, the folder it
  landed in, and its ancestors) in a **single** model call, so the tree keeps the invariant
  Graph Creation established.

Uploaded bytes and suggestions live on an ``add_requests`` row between the two steps
(``supabase/migrations/0002_graph_add.sql``), so placement never re-uploads the document. The
document itself is not summarised: only the folders around it are described.
"""
