#!/usr/bin/env python3
"""Merge daily-owned watchlist fields into the newest main snapshot.

Daily refresh owns KB exact price/detail and MOLIT trade fields. Weekly refresh
owns listing/ask fields. This helper prevents an older in-flight daily run from
overwriting a newer weekly listing snapshot after git pull.
"""
import argparse,json
from pathlib import Path

R=Path(__file__).resolve().parents[1]
DATA=R/'data/buy_watchlist_market.json'
DIST=R/'dist/buy_watchlist_market.json'
LISTING_FIELDS=('sale_listing_count','sale_listing_week_delta','avg_ask_manwon','avg_ask_week_delta_manwon',
                'listing_collected_at','listing_refresh_status')
LISTING_META=('listing_collected_at','listing_refresh_attempted_at','listing_refresh_matched_rows',
              'listing_refresh_status','listing_source','listing_refresh_error')

def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def key(x):
    try:return (int(x.get('complex_id')),int(x.get('area_id')))
    except:return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);args=ap.parse_args()
    newest=load(DATA)
    daily=load(args.source)
    newest_rows={key(x):x for x in newest.get('items') or [] if key(x)}
    out=dict(daily)
    rows=[]
    for row in daily.get('items') or []:
        z=dict(row);old=newest_rows.get(key(row))
        if old:
            for f in LISTING_FIELDS:
                if f in old:z[f]=old.get(f)
        else:
            for f in LISTING_FIELDS:z.pop(f,None)
        rows.append(z)
    out['items']=rows
    for f in LISTING_META:
        if f in newest:out[f]=newest.get(f)
        else:out.pop(f,None)
    text=json.dumps(out,ensure_ascii=False,indent=2)+'\n'
    DATA.write_text(text,encoding='utf-8');DIST.write_text(text,encoding='utf-8')
    print(json.dumps({'status':'merged','daily_rows':len(rows),'preserved_listing_rows':sum(key(x) in newest_rows for x in rows)},ensure_ascii=False))

if __name__=='__main__':main()
