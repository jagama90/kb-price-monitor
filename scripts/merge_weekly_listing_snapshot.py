#!/usr/bin/env python3
"""Merge only weekly listing-owned fields into the newest watchlist market snapshot."""
import argparse, datetime as dt, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/buy_watchlist_market.json'
DIST=ROOT/'dist/buy_watchlist_market.json'
FIELDS=('sale_listing_count','sale_listing_week_delta','avg_ask_manwon','avg_ask_week_delta_manwon')

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def row_key(row):
    try:return (int(row.get('complex_id')),int(row.get('area_id')))
    except:return None

def save(payload):
    text=json.dumps(payload,ensure_ascii=False,indent=2)+'\n'
    DATA.write_text(text,encoding='utf-8')
    DIST.write_text(text,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source')
    ap.add_argument('--mark-failed',action='store_true')
    args=ap.parse_args()
    latest=load(DATA)
    rows=latest.get('items') or []
    attempted=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')

    if args.source:
        weekly=load(args.source)
        stamp=weekly.get('listing_collected_at') or weekly.get('collected_at')
        idx={row_key(x):x for x in weekly.get('items') or [] if row_key(x)}
        matched=0
        for row in rows:
            src=idx.get(row_key(row))
            if src is None:
                if any(row.get(f) is not None for f in FIELDS):
                    row['listing_refresh_status']='fallback_last_good'
                continue
            for f in FIELDS:
                row[f]=src.get(f)
            row['listing_collected_at']=stamp
            row['listing_refresh_status']='connected'
            matched+=1
        latest['listing_collected_at']=stamp or latest.get('listing_collected_at')
        latest['listing_refresh_attempted_at']=attempted
        latest['listing_refresh_matched_rows']=matched
        latest['listing_refresh_status']='connected' if matched==len(rows) else 'partial_last_good'
        latest['listing_source']=weekly.get('source')
        latest.pop('listing_refresh_error',None)
        save(latest)
        print(json.dumps({'status':latest['listing_refresh_status'],'matched':matched,'rows':len(rows)},ensure_ascii=False))
        return

    if args.mark_failed:
        for row in rows:
            if any(row.get(f) is not None for f in FIELDS):
                row['listing_refresh_status']='fallback_last_good'
        latest['listing_refresh_attempted_at']=attempted
        latest['listing_refresh_matched_rows']=0
        latest['listing_refresh_status']='fallback_last_good'
        latest['listing_refresh_error']='weekly KB public-market source unavailable; preserved last-good listing fields'
        save(latest)
        print(json.dumps({'status':'fallback_last_good','rows':len(rows)},ensure_ascii=False))
        return

    raise SystemExit('provide --source or --mark-failed')

if __name__=='__main__':
    main()
