#!/usr/bin/env python3
"""Merge watchlist detail sources without cross-type substitution.

Guarantees one representative row per supported target complex, then overlays
independent exact-area sources: KB general price, MOLIT recent trade and asking
price/listing details. Missing sources remain null instead of becoming false 0.
"""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
market_path=ROOT/'data/buy_watchlist_market.json'
detail_path=ROOT/'data/buy_watchlist_listings.json'
trade_path=ROOT/'data_sources/watchlist_recent_trades.json'
dist_path=ROOT/'dist/buy_watchlist_market.json'

def load(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return default

def norm(s):return re.sub(r'[^0-9A-Za-z가-힣]','',str(s or '')).replace('아파트','').lower()
def pyeong(t):
    m=re.search(r'\d+(?:\.\d+)?',str(t.get('type_label') or ''))
    return float(m.group()) if m else None

market=load(market_path,{'items':[]})
detail=load(detail_path,{'items':[]})
trades=load(trade_path,{'items':[]})
master=load(ROOT/'data/buy_watchlist_master.json',{'items':[]})
targets=load(ROOT/'data/buy_watchlist_targets.json',{'items':[]})

masters=master.get('items') or []
by_name={norm(x.get('user_name')):x for x in masters}
by_kb={norm(x.get('kb_name')):x for x in masters if x.get('kb_name')}
target_by_complex={}

def allowed_types(c,t):
    types=c.get('types') or []
    aids={int(x) for x in (t.get('area_ids') or []) if x}
    if aids:return [x for x in types if int(x.get('area_id') or 0) in aids]
    lo,hi=t.get('min_pyeong'),t.get('max_pyeong')
    if lo is None and hi is None:return types
    out=[]
    for x in types:
        py=pyeong(x)
        if py is not None and (lo is None or py>=float(lo)) and (hi is None or py<=float(hi)):out.append(x)
    return out

supported=[]
known_unavailable=[]
for t in targets.get('items') or []:
    c=by_name.get(norm(t.get('name'))) or by_kb.get(norm(t.get('name')))
    if not c or not c.get('complex_id'):
        if c and c.get('status') in ('confirmed_preoccupancy','preoccupancy'):
            known_unavailable.append(t.get('name'))
        continue
    types=allowed_types(c,t)
    if not types:continue
    # Representative type = largest household count in the user's requested group.
    typ=max(types,key=lambda x:(int(x.get('type_households') or 0),-int(x.get('area_id') or 0)))
    supported.append((c,t,typ))
    target_by_complex[int(c['complex_id'])]=(c,t,types,typ)

rows=market.get('items') or []
row_by_complex={int(x.get('complex_id')):x for x in rows if x.get('complex_id')}
for c,t,typ in supported:
    cid=int(c['complex_id'])
    if cid not in row_by_complex:
        row={'complex_id':cid,'area_id':int(typ['area_id']),'type_label':typ.get('type_label'),'name':c.get('user_name') or c.get('kb_name'),
             'sale_listing_count':None,'sale_listing_week_delta':None,'avg_ask_manwon':None,'recent_trade_manwon':None,'recent_trade_date':None,
             'market_scope':'target_area_id','row_source':'target_seed'}
        rows.append(row);row_by_complex[cid]=row

kb_exact={(int(c['complex_id']),int(t['area_id'])):t for c in masters if c.get('complex_id') for t in c.get('types') or [] if t.get('area_id')}
detail_idx={(int(x['complex_id']),int(x['area_id'])):x for x in detail.get('items') or [] if x.get('complex_id') and x.get('area_id')}
trade_idx={(int(x['complex_id']),int(x['area_id'])):x for x in trades.get('items') or [] if x.get('complex_id') and x.get('area_id')}

matched_detail=matched_trade=exact_kb=0
for row in rows:
    cid=int(row.get('complex_id') or 0)
    target=target_by_complex.get(cid)
    if target:
        _,_,types,rep=target
        allowed={int(x.get('area_id') or 0) for x in types}
        if int(row.get('area_id') or 0)!=int(rep['area_id']):
            # One canonical representative type across KB price, listing, trade,
            # monthly history and regional-temperature calculations.
            row['area_id']=int(rep['area_id']);row['type_label']=rep.get('type_label')
            for k in ('sale_listing_count','sale_listing_week_delta','avg_ask_manwon','avg_ask_week_delta_manwon',
                      'listing_collected_at','recent_trade_manwon','recent_trade_date','recent_trade_source',
                      'molit_apt_name','trade_match_method'):
                row[k]=None
            row['listing_refresh_status']='representative_area_changed'
            row['trade_refresh_status']='unmatched'
    aid=int(row.get('area_id') or 0)
    kt=kb_exact.get((cid,aid))
    if kt:
        row['kb_general_check_manwon']=kt.get('general_price_manwon')
        row['kb_price_date']=kt.get('price_date')
        row['type_label']=kt.get('type_label') or row.get('type_label')
        exact_kb+=1
    d=detail_idx.get((cid,aid))
    if d:
        for k in ('avg_ask_manwon','lowest_ask_manwon','listing_count','page_count','kb_price_date'):
            if d.get(k) is not None:row[k]=d[k]
        matched_detail+=1
    tr=trade_idx.get((cid,aid))
    if tr and tr.get('recent_trade_manwon') is not None:
        row['recent_trade_manwon']=tr.get('recent_trade_manwon')
        row['recent_trade_date']=tr.get('recent_trade_date')
        row['recent_trade_source']='MOLIT'
        row['molit_apt_name']=tr.get('molit_apt_name')
        row['trade_match_method']=tr.get('match_method')
        row['trade_refresh_status']=tr.get('trade_refresh_status') or 'connected'
        matched_trade+=1
    else:
        # The latest exact-area trade snapshot is authoritative for identity.
        # Never keep a previously mis-matched complex trade just because the
        # refreshed collector found no verified candidate.
        row['recent_trade_manwon']=None
        row['recent_trade_date']=None
        row['recent_trade_source']=None
        row['molit_apt_name']=None
        row['trade_match_method']=None
        row['trade_refresh_status']='unmatched'
    row['detail_quality']='exact_area_id'

market['items']=rows
market['listing_collected_at']=market.get('listing_collected_at') or market.get('collected_at')
market['kb_detail_collected_at']=detail.get('collected_at')
market['molit_trade_collected_at']=trades.get('collected_at')
market['kb_detail_matched_rows']=matched_detail
market['molit_trade_matched_rows']=matched_trade
market['exact_kb_rows']=exact_kb
market['supported_target_rows']=len(supported)
market['known_unavailable_targets']=known_unavailable
text=json.dumps(market,ensure_ascii=False,indent=2)+'\n'
market_path.write_text(text,encoding='utf-8');dist_path.write_text(text,encoding='utf-8')
print(json.dumps({'market_rows':len(rows),'supported_targets':len(supported),'exact_kb':exact_kb,'detail_matched':matched_detail,'trade_matched':matched_trade,'known_unavailable':known_unavailable},ensure_ascii=False))
if len(rows)<len(supported):raise SystemExit('watchlist market row coverage incomplete')
