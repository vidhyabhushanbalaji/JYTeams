-- Graph Creation schema: projects → directories (hierarchy via ltree) → files, plus the
-- background upload jobs that build them.
--
-- Apply with the Supabase CLI (`npx supabase db push`) or paste into the SQL editor.
-- `ltree` gives index-backed subtree queries: `where ltree_path <@ 'docs.api'`.

create extension if not exists pgcrypto;
create extension if not exists ltree;

create table if not exists public.projects (
  id                uuid primary key default gen_random_uuid(),
  owner_id          uuid not null references auth.users (id) on delete cascade,
  name              text not null,
  description       text,
  root_directory_id uuid,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create table if not exists public.directories (
  id                    uuid primary key default gen_random_uuid(),
  project_id            uuid not null references public.projects (id) on delete cascade,
  parent_id             uuid references public.directories (id) on delete cascade,
  name                  text not null,
  path                  text not null,
  ltree_path            ltree,
  depth                 integer not null check (depth >= 0),
  description           text,
  description_model     text,
  direct_file_count     integer not null default 0,
  child_directory_count integer not null default 0,
  created_at            timestamptz not null default now(),
  unique (project_id, path)
);

create index if not exists directories_parent_idx on public.directories (parent_id);
create index if not exists directories_ltree_idx on public.directories using gist (ltree_path);

alter table public.projects
  drop constraint if exists projects_root_directory_fk;
alter table public.projects
  add constraint projects_root_directory_fk
  foreign key (root_directory_id) references public.directories (id) on delete set null;

create table if not exists public.files (
  id             uuid primary key default gen_random_uuid(),
  project_id     uuid not null references public.projects (id) on delete cascade,
  directory_id   uuid not null references public.directories (id) on delete cascade,
  name           text not null,
  path           text not null,
  size_bytes     bigint not null check (size_bytes >= 0),
  content_sha256 text not null,
  mime_type      text,
  storage_bucket text not null,
  storage_path   text not null,
  summary        text,
  summary_status text not null default 'pending'
                 check (summary_status in ('pending', 'ok', 'skipped', 'failed')),
  summary_model  text,
  created_at     timestamptz not null default now(),
  unique (project_id, path)
);

create index if not exists files_directory_idx on public.files (directory_id);
create index if not exists files_hash_idx on public.files (content_sha256);

create table if not exists public.creation_jobs (
  id              uuid primary key default gen_random_uuid(),
  project_id      uuid not null references public.projects (id) on delete cascade,
  owner_id        uuid not null references auth.users (id) on delete cascade,
  mode            text not null check (mode in ('new', 'add')),
  status          text not null default 'queued'
                  check (status in ('queued', 'extracting', 'summarising', 'persisting',
                                    'ok', 'partial', 'failed')),
  total_files     integer not null default 0,
  processed_files integer not null default 0,
  failed_files    integer not null default 0,
  error           text,
  created_at      timestamptz not null default now(),
  finished_at     timestamptz
);

create index if not exists creation_jobs_project_idx on public.creation_jobs (project_id);

-- Row level security. The backend uses the service role (which bypasses RLS), so these
-- policies protect direct access from the Electron client with a user JWT.
alter table public.projects enable row level security;
alter table public.directories enable row level security;
alter table public.files enable row level security;
alter table public.creation_jobs enable row level security;

drop policy if exists projects_owner_all on public.projects;
create policy projects_owner_all on public.projects
  for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());

drop policy if exists directories_owner_all on public.directories;
create policy directories_owner_all on public.directories
  for all
  using (exists (select 1 from public.projects p
                 where p.id = project_id and p.owner_id = auth.uid()))
  with check (exists (select 1 from public.projects p
                      where p.id = project_id and p.owner_id = auth.uid()));

drop policy if exists files_owner_all on public.files;
create policy files_owner_all on public.files
  for all
  using (exists (select 1 from public.projects p
                 where p.id = project_id and p.owner_id = auth.uid()))
  with check (exists (select 1 from public.projects p
                      where p.id = project_id and p.owner_id = auth.uid()));

drop policy if exists creation_jobs_owner_all on public.creation_jobs;
create policy creation_jobs_owner_all on public.creation_jobs
  for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
