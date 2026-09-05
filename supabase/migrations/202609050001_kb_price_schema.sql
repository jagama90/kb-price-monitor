create extension if not exists pgcrypto;

create table if not exists public.kb_collections (
  id uuid primary key default gen_random_uuid(),
  schema_version integer not null check (schema_version = 2),
  scope text not null,
  districts text[] not null,
  collected_at timestamptz not null,
  catalog_collected_at timestamptz,
  target_complex_count integer not null,
  successful_complex_count integer not null,
  type_count integer not null,
  priced_count integer not null,
  empty_complex_count integer not null default 0,
  status text not null default 'importing' check (status in ('importing','published','failed')),
  created_at timestamptz not null default now()
);

create table if not exists public.kb_current_prices (
  complex_id bigint not null,
  area_id bigint not null,
  collection_id uuid not null references public.kb_collections(id),
  name text not null,
  district text not null,
  dong text,
  households integer,
  type_households integer,
  built_ymd text,
  type_label text,
  supply_m2 numeric,
  exclusive_m2 numeric,
  supply_pyeong numeric not null,
  exclusive_pyeong numeric,
  general_price_manwon numeric,
  price_status text not null,
  price_date date,
  collected_at timestamptz not null,
  url text not null,
  primary key (complex_id, area_id)
);

create table if not exists public.kb_price_history (
  complex_id bigint not null,
  area_id bigint not null,
  collection_id uuid not null references public.kb_collections(id),
  general_price_manwon numeric,
  price_status text not null,
  price_date date,
  collected_at timestamptz not null,
  primary key (complex_id, area_id, collection_id)
);

create table if not exists public.kb_import_rows (
  collection_id uuid not null references public.kb_collections(id) on delete cascade,
  complex_id bigint not null,
  area_id bigint not null,
  name text not null,
  district text not null,
  dong text,
  households integer,
  type_households integer,
  built_ymd text,
  type_label text,
  supply_m2 numeric,
  exclusive_m2 numeric,
  supply_pyeong numeric not null,
  exclusive_pyeong numeric,
  general_price_manwon numeric,
  price_status text not null,
  price_date date,
  collected_at timestamptz not null,
  url text not null,
  primary key (collection_id, complex_id, area_id)
);

create index if not exists kb_current_filter_idx on public.kb_current_prices (district, supply_pyeong, households);
create index if not exists kb_current_price_idx on public.kb_current_prices (general_price_manwon);
create index if not exists kb_history_pair_idx on public.kb_price_history (complex_id, area_id, collected_at desc);

alter table public.kb_collections enable row level security;
alter table public.kb_current_prices enable row level security;
alter table public.kb_price_history enable row level security;
alter table public.kb_import_rows enable row level security;

drop policy if exists "public read published collections" on public.kb_collections;
create policy "public read published collections" on public.kb_collections for select
  using (status = 'published');
drop policy if exists "public read current prices" on public.kb_current_prices;
create policy "public read current prices" on public.kb_current_prices for select using (true);

create or replace function public.promote_kb_collection(p_collection_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  c public.kb_collections%rowtype;
  imported integer;
  changed integer;
begin
  select * into c from public.kb_collections where id = p_collection_id for update;
  if c.id is null or c.status <> 'importing' then
    raise exception 'collection is missing or not importing';
  end if;

  select count(*) into imported from public.kb_import_rows where collection_id = p_collection_id;
  if imported <> c.type_count then
    raise exception 'row count mismatch: expected %, got %', c.type_count, imported;
  end if;

  insert into public.kb_price_history
    (complex_id, area_id, collection_id, general_price_manwon, price_status, price_date, collected_at)
  select i.complex_id, i.area_id, i.collection_id, i.general_price_manwon,
         i.price_status, i.price_date, i.collected_at
  from public.kb_import_rows i
  left join public.kb_current_prices old using (complex_id, area_id)
  where i.collection_id = p_collection_id
    and (old.complex_id is null or
         old.general_price_manwon is distinct from i.general_price_manwon or
         old.price_status is distinct from i.price_status or
         old.price_date is distinct from i.price_date);
  get diagnostics changed = row_count;

  insert into public.kb_current_prices
  select complex_id, area_id, collection_id, name, district, dong, households,
         type_households, built_ymd, type_label, supply_m2, exclusive_m2,
         supply_pyeong, exclusive_pyeong, general_price_manwon, price_status,
         price_date, collected_at, url
  from public.kb_import_rows where collection_id = p_collection_id
  on conflict (complex_id, area_id) do update set
    collection_id = excluded.collection_id, name = excluded.name,
    district = excluded.district, dong = excluded.dong,
    households = excluded.households, type_households = excluded.type_households,
    built_ymd = excluded.built_ymd, type_label = excluded.type_label,
    supply_m2 = excluded.supply_m2, exclusive_m2 = excluded.exclusive_m2,
    supply_pyeong = excluded.supply_pyeong, exclusive_pyeong = excluded.exclusive_pyeong,
    general_price_manwon = excluded.general_price_manwon,
    price_status = excluded.price_status, price_date = excluded.price_date,
    collected_at = excluded.collected_at, url = excluded.url;

  delete from public.kb_current_prices cur
  where cur.district = any(c.districts)
    and not exists (
      select 1 from public.kb_import_rows i
      where i.collection_id = p_collection_id
        and i.complex_id = cur.complex_id and i.area_id = cur.area_id
    );

  update public.kb_collections set status = 'published' where id = p_collection_id;
  delete from public.kb_import_rows where collection_id = p_collection_id;
  return jsonb_build_object('published_rows', imported, 'changed_rows', changed);
end;
$$;

revoke all on function public.promote_kb_collection(uuid) from public, anon, authenticated;
grant execute on function public.promote_kb_collection(uuid) to service_role;
grant select on public.kb_collections, public.kb_current_prices to anon, authenticated;

