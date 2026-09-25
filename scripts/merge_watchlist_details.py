#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
market_path=ROOT/'data/buy_watchlist_market.json'; detail_path=ROOT/'data/buy_watchlist_listings.json'; dist_path=ROOT/'dist/buy_watchlist_market.json'
market=json.loads(market_path.read_text(encoding='utf-8')); detail=json.loads(detail_path.read_text(encoding='utf-8'))
idx={(int(x['complex_id']),int(x['area_id'])):x for x in detail.get('items',[]) if x.get('complex_id') and x.get('area_id')}; matched=0
for row in market.get('items',[]):
    d=idx.get((int(row.get('complex_id') or 0),int(row.get('area_id') or 0)))
    if not d: continue
    for k in ('avg_ask_manwon','recent_trade_manwon','recent_trade_date','kb_general_check_manwon','kb_price_date'):
        if d.get(k) is not None: row[k]=d[k]
    matched+=1
market['kb_detail_collected_at']=detail.get('collected_at'); market['kb_detail_matched_rows']=matched
text=json.dumps(market,ensure_ascii=False,indent=2)+'\n'; market_path.write_text(text,encoding='utf-8'); dist_path.write_text(text,encoding='utf-8')
print(json.dumps({'market_rows':len(market.get('items',[])),'detail_rows':len(detail.get('items',[])),'matched':matched},ensure_ascii=False))
if matched==0: raise SystemExit('no KB detail rows matched market rows')
