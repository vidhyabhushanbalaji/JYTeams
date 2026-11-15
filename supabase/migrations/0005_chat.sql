-- Project chat: one group chat per project, with messages that may reference a document, a folder
-- or a ticket.
--
-- A project *is* its chat. There is no channel table and nothing to backfill: `project_id` is the
-- channel, so every project already has one and sharing a project (project_members) puts the
-- member in its chat. Deleting the project takes its messages with it.
--
-- Apply with the Supabase CLI (`npx supabase db push`) or paste into the SQL editor.
-- Additive only: one new table, no existing row is touched.

create table if not exists public.chat_messages (
  -- Monotonic cursor for the desktop app's poll (?after_seq=). Bigger is newer.
  seq        bigint generated always as identity primary key,
  id         uuid not null unique default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  member_id  uuid not null references public.members (id) on delete cascade,
  -- The text as it was typed, including `@[label](kind:uuid)` mention markers.
  body       text not null check (length(btrim(body)) between 1 and 4000),
  -- Resolved mentions, denormalised so rendering and clicking need no lookup:
  -- [{"kind":"file","id":"...","label":"auth.md","path":"guides/auth.md",
  --   "directory_path":"guides","ticket_number":null}]
  mentions   jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

comment on column public.chat_messages.seq is
  'Poll cursor for GET /api/chat/projects/{id}/messages?after_seq=';
comment on column public.chat_messages.mentions is
  'Resolved file/directory/ticket mentions, validated against the message''s project when posted';

create index if not exists chat_messages_project_idx
  on public.chat_messages (project_id, seq desc);

-- Like every table the API owns: RLS is on and there are no policies, because the Electron app
-- never talks to Supabase. The service role (the API) bypasses RLS and enforces membership in
-- app/core/access.py.
alter table public.chat_messages enable row level security;

-- ------------------------------------------------------------------ rollback
--
-- drop table if exists public.chat_messages;
