alter table public.manual_refresh_requests
  add column if not exists dispatched_at timestamptz,
  add column if not exists dispatched_by text,
  add column if not exists dispatch_attempts integer not null default 0;

create index if not exists manual_refresh_requests_pending_idx
  on public.manual_refresh_requests (requested_at)
  where dispatched_at is null;
