-- Tickets: a name-only identity, shared projects, Jira-style tickets with files, comments and an
-- activity feed. Also the search cache a ticket keeps so reopening it does not re-walk the tree.
--
-- Apply with the Supabase CLI (`npx supabase db push`) or paste into the SQL editor.
--
-- Identity change (the only part that is not additive):
--   * `members` becomes the identity table. A member is a display name, nothing else — no
--     password and no token, because this is a hackathon build with no authentication.
--   * `projects.owner_id`, `creation_jobs.owner_id` and `add_requests.owner_id` are repointed
--     from `auth.users` to `members`. Every existing owner is seeded into `members` with its
--     old uuid, so no row is rewritten and the new constraints validate immediately.
--   * The `auth.uid()` row level security policies are dropped: the Electron app never talks to
--     Supabase directly, the backend is the only client (service role, which bypasses RLS).
--
-- Rollback is at the bottom of this file.

-- ---------------------------------------------------------------- identity

create table if not exists public.members (
  id           uuid primary key default gen_random_uuid(),
  display_name text not null check (length(btrim(display_name)) between 1 and 60),
  name_key     text generated always as (lower(btrim(display_name))) stored,
  created_at   timestamptz not null default now()
);

create unique index if not exists members_name_key_idx on public.members (name_key);

-- Seed one member per existing owner, keeping the old uuid so the FK swap needs no UPDATE.
-- Duplicate e-mail local parts get a numeric suffix, because a member's name must be unique
-- (it is how somebody signs in).
do $$
declare
  r         record;
  base      text;
  candidate text;
  suffix    integer;
begin
  for r in
    select u.id, coalesce(nullif(split_part(u.email, '@', 1), ''), 'Member') as base_name
    from auth.users u
    where u.id in (
      select owner_id from public.projects
      union select owner_id from public.creation_jobs
      union select owner_id from public.add_requests
    )
  loop
    base := left(btrim(r.base_name), 50);
    candidate := base;
    suffix := 2;
    while exists (select 1 from public.members m where m.name_key = lower(candidate)) loop
      candidate := base || ' ' || suffix;
      suffix := suffix + 1;
    end loop;
    insert into public.members (id, display_name) values (r.id, candidate)
    on conflict (id) do nothing;
  end loop;
end $$;

alter table public.projects      drop constraint if exists projects_owner_id_fkey;
alter table public.creation_jobs drop constraint if exists creation_jobs_owner_id_fkey;
alter table public.add_requests  drop constraint if exists add_requests_owner_id_fkey;

alter table public.projects      add constraint projects_owner_id_fkey
  foreign key (owner_id) references public.members (id) on delete cascade;
alter table public.creation_jobs add constraint creation_jobs_owner_id_fkey
  foreign key (owner_id) references public.members (id) on delete cascade;
alter table public.add_requests  add constraint add_requests_owner_id_fkey
  foreign key (owner_id) references public.members (id) on delete cascade;

-- ------------------------------------------------------------ project sharing

create table if not exists public.project_members (
  project_id uuid not null references public.projects (id) on delete cascade,
  member_id  uuid not null references public.members (id) on delete cascade,
  role       text not null default 'member' check (role in ('owner', 'member')),
  added_by   uuid references public.members (id) on delete set null,
  added_at   timestamptz not null default now(),
  primary key (project_id, member_id)
);

create index if not exists project_members_member_idx on public.project_members (member_id);

-- Every existing project's creator joins its own project.
insert into public.project_members (project_id, member_id, role)
select p.id, p.owner_id, 'owner' from public.projects p
on conflict (project_id, member_id) do nothing;

-- ------------------------------------------------------------------- tickets

create table if not exists public.tickets (
  id                  uuid primary key default gen_random_uuid(),
  project_id          uuid not null references public.projects (id) on delete cascade,
  number              integer not null check (number > 0),
  title               text not null check (length(btrim(title)) between 1 and 200),
  description         text not null default '',
  status              text not null default 'todo'
                      check (status in ('todo', 'in_progress', 'done')),
  priority            text not null default 'medium'
                      check (priority in ('low', 'medium', 'high')),
  due_date            date,
  labels              text[] not null default '{}',
  assignee_id         uuid references public.members (id) on delete set null,
  reporter_id         uuid not null references public.members (id) on delete cascade,
  completed_at        timestamptz,
  completed_by        uuid references public.members (id) on delete set null,
  -- Graph AI Search cache: filled the first time the ticket is opened, refreshed when the
  -- fingerprint below no longer describes the project.
  search_query        text,
  search_context      text,
  search_results      jsonb,
  search_fingerprint  text,
  search_refreshed_at timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (project_id, number)
);

create index if not exists tickets_project_idx on public.tickets (project_id, status);
create index if not exists tickets_assignee_idx on public.tickets (assignee_id, status);

create table if not exists public.ticket_files (
  ticket_id uuid not null references public.tickets (id) on delete cascade,
  file_id   uuid not null references public.files (id) on delete cascade,
  added_by  uuid references public.members (id) on delete set null,
  source    text not null default 'upload' check (source in ('upload', 'existing')),
  added_at  timestamptz not null default now(),
  primary key (ticket_id, file_id)
);

create table if not exists public.ticket_comments (
  id         uuid primary key default gen_random_uuid(),
  ticket_id  uuid not null references public.tickets (id) on delete cascade,
  author_id  uuid not null references public.members (id) on delete cascade,
  body       text not null check (length(btrim(body)) between 1 and 4000),
  created_at timestamptz not null default now()
);

create index if not exists ticket_comments_ticket_idx on public.ticket_comments (ticket_id);

create table if not exists public.ticket_events (
  id         uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  ticket_id  uuid references public.tickets (id) on delete cascade,
  member_id  uuid references public.members (id) on delete set null,
  kind       text not null,
  detail     jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists ticket_events_project_idx
  on public.ticket_events (project_id, created_at desc);
create index if not exists ticket_events_ticket_idx
  on public.ticket_events (ticket_id, created_at desc);

-- The search cache compares the project's newest document edit, which today leaves no
-- timestamp. A trigger keeps Graph Creation's insert/update code untouched.
alter table public.files add column if not exists updated_at timestamptz not null default now();

create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end $$;

drop trigger if exists files_touch_updated_at on public.files;
create trigger files_touch_updated_at
  before update on public.files
  for each row execute function public.touch_updated_at();

-- ------------------------------------------------------------------ security

alter table public.members         enable row level security;
alter table public.project_members enable row level security;
alter table public.tickets         enable row level security;
alter table public.ticket_files    enable row level security;
alter table public.ticket_comments enable row level security;
alter table public.ticket_events   enable row level security;

-- The identity is a header the backend trusts in AUTH_MODE=dev, so `auth.uid()` can never
-- match it. Direct client access is denied instead of being policy-gated; the service role
-- (the API) bypasses RLS and enforces access in the service layer.
drop policy if exists projects_owner_all on public.projects;
drop policy if exists directories_owner_all on public.directories;
drop policy if exists files_owner_all on public.files;
drop policy if exists creation_jobs_owner_all on public.creation_jobs;
drop policy if exists add_requests_owner_all on public.add_requests;

-- ------------------------------------------------------------------ rollback
--
-- drop table if exists public.ticket_events;
-- drop table if exists public.ticket_comments;
-- drop table if exists public.ticket_files;
-- drop table if exists public.tickets;
-- drop table if exists public.project_members;
--
-- alter table public.files drop column if exists updated_at;
-- drop trigger if exists files_touch_updated_at on public.files;
-- drop function if exists public.touch_updated_at();
--
-- alter table public.projects      drop constraint if exists projects_owner_id_fkey;
-- alter table public.creation_jobs drop constraint if exists creation_jobs_owner_id_fkey;
-- alter table public.add_requests  drop constraint if exists add_requests_owner_id_fkey;
-- alter table public.projects      add constraint projects_owner_id_fkey
--   foreign key (owner_id) references auth.users (id) on delete cascade;
-- alter table public.creation_jobs add constraint creation_jobs_owner_id_fkey
--   foreign key (owner_id) references auth.users (id) on delete cascade;
-- alter table public.add_requests  add constraint add_requests_owner_id_fkey
--   foreign key (owner_id) references auth.users (id) on delete cascade;
--
-- create policy projects_owner_all on public.projects
--   for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
-- create policy directories_owner_all on public.directories
--   for all
--   using (exists (select 1 from public.projects p
--                  where p.id = project_id and p.owner_id = auth.uid()))
--   with check (exists (select 1 from public.projects p
--                       where p.id = project_id and p.owner_id = auth.uid()));
-- create policy files_owner_all on public.files
--   for all
--   using (exists (select 1 from public.projects p
--                  where p.id = project_id and p.owner_id = auth.uid()))
--   with check (exists (select 1 from public.projects p
--                       where p.id = project_id and p.owner_id = auth.uid()));
-- create policy creation_jobs_owner_all on public.creation_jobs
--   for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
-- create policy add_requests_owner_all on public.add_requests
--   for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
--
-- drop table if exists public.members;
