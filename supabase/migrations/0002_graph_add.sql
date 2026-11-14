-- Graph Add: the wizard's two steps (suggest → place) need somewhere to hold the uploaded
-- document and the ranking the user was shown, so placement never re-uploads or re-summarises
-- the document and a stale choice can be detected.
--
-- Apply with the Supabase CLI (`npx supabase db push`) or paste into the SQL editor.
-- Additive only: no existing table is altered.

create table if not exists public.add_requests (
  id              uuid primary key default gen_random_uuid(),
  project_id      uuid not null references public.projects (id) on delete cascade,
  owner_id        uuid not null references auth.users (id) on delete cascade,
  file_name       text not null,
  content_sha256  text not null,
  size_bytes      bigint not null check (size_bytes >= 0),
  mime_type       text,
  storage_bucket  text not null,
  storage_path    text not null,
  summary         text not null,
  summary_model   text,
  suggestions     jsonb not null default '[]'::jsonb,
  traversal       jsonb not null default '{}'::jsonb,
  status          text not null default 'suggested'
                  check (status in ('suggested', 'placed', 'abandoned', 'expired')),
  placed_file_id  uuid references public.files (id) on delete set null,
  created_at      timestamptz not null default now(),
  expires_at      timestamptz not null default now() + interval '24 hours'
);

create index if not exists add_requests_project_idx on public.add_requests (project_id);
create index if not exists add_requests_expiry_idx on public.add_requests (expires_at);

-- Row level security: the backend uses the service role (which bypasses RLS), so this
-- protects direct access from the Electron client with a user JWT.
alter table public.add_requests enable row level security;

drop policy if exists add_requests_owner_all on public.add_requests;
create policy add_requests_owner_all on public.add_requests
  for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
