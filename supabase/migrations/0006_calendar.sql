-- Calendars: one per project, plus the individual calendar that merges every project a member is
-- in. A row is either a project event (`project_id` set, visible to the whole project) or a
-- personal event (`project_id` null, visible only to its creator).
--
-- Ticket deadlines are NOT copied here. They are read from `tickets.due_date` on every request
-- (through the tickets section's public module), so editing a ticket moves its calendar deadline
-- immediately and a completed ticket stops shadowing the calendar.
--
-- Apply with the Supabase CLI (`npx supabase db push`) or paste into the SQL editor.
-- Additive only: one new table, no existing row is touched.

create table if not exists public.calendar_events (
  id         uuid primary key default gen_random_uuid(),
  -- null = a personal event (only `member_id` sees it); set = a project event.
  project_id uuid references public.projects (id) on delete cascade,
  member_id  uuid not null references public.members (id) on delete cascade,
  title      text not null check (length(btrim(title)) between 1 and 200),
  notes      text not null default '' check (length(notes) <= 2000),
  starts_at  timestamptz not null,
  ends_at    timestamptz,
  all_day    boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint calendar_events_range check (ends_at is null or ends_at >= starts_at)
);

comment on column public.calendar_events.project_id is
  'null = personal event (member_id only); set = project event visible to every project member';

create index if not exists calendar_events_project_idx
  on public.calendar_events (project_id, starts_at);
create index if not exists calendar_events_member_idx
  on public.calendar_events (member_id, starts_at);

-- Updated automatically, so the API never has to remember to stamp an edit.
create or replace function public.calendar_touch_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists calendar_events_touch_updated_at on public.calendar_events;
create trigger calendar_events_touch_updated_at
  before update on public.calendar_events
  for each row execute function public.calendar_touch_updated_at();

-- RLS on, no policies: the Electron app never talks to Supabase. The service role (the API)
-- bypasses RLS and enforces membership and event ownership in the service layer.
alter table public.calendar_events enable row level security;

-- ------------------------------------------------------------------ rollback
--
-- drop table if exists public.calendar_events;
-- drop function if exists public.calendar_touch_updated_at();
