-- Keep foreign-key maintenance efficient as collections/history grow.
create index if not exists kb_current_prices_collection_id_idx
  on public.kb_current_prices (collection_id);

create index if not exists kb_price_history_collection_id_idx
  on public.kb_price_history (collection_id);
