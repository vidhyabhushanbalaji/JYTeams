-- Tickets now distil a ticket's wording into a short search query before asking Graph AI Search
-- for the documents it is about. This column records which wording the stored `search_query` was
-- distilled from, so:
--
--   * opening a ticket again reuses both the terms and the result (no model call);
--   * a project document added or edited re-runs only the local search;
--   * an edited title or description distils the terms again, once.
--
-- Apply with the Supabase CLI (`npx supabase db push`) or paste into the SQL editor.
-- Additive only: one nullable column, no existing row is rewritten. Rows written before this
-- migration keep their cached result and re-distil once, the next time they are opened.

alter table public.tickets
  add column if not exists search_terms_fingerprint text;

comment on column public.tickets.search_terms_fingerprint is
  'sha256 of the title, description and distiller version the stored search_query came from';
