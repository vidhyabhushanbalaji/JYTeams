-- Calendar events can mention a document, a folder or a ticket, the same way a chat message can.
--
-- An event's `notes` keep the text as it was typed, including `@[label](kind:uuid)` markers. The
-- resolved set is denormalised here when the event is written, validated against the event's
-- project in app/calendar/service.py — which is what lets a ticket show the events it is
-- mentioned in without re-parsing every event's notes.
--
-- Apply with the Supabase CLI (`npx supabase db push`) or paste into the SQL editor.
-- Additive only: one new column with a default, no existing row is touched.

alter table public.calendar_events
  add column if not exists mentions jsonb not null default '[]'::jsonb;

comment on column public.calendar_events.mentions is
  'Resolved file/directory/ticket mentions from notes, validated against the event''s project';

-- A personal event (project_id is null) has nothing to validate a mention against, so the API
-- stores an empty list for it; a project event may carry up to 20 resolved references.
--
-- ------------------------------------------------------------------ rollback
--
-- alter table public.calendar_events drop column if exists mentions;
