#!/usr/bin/env python3
import argparse,json,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'data/buy_watchlist_master.json'
BASE=ROOT/'data/kb_watchlist_friday_snapshot.json'
OUT=ROOT/'dist/kb_watchlist_weekly_change.json'

def load(p,default=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8'))
    except:return default if default is not None else {}

def flatten(d):
    out={}
    for c in d.get('items') or []:
        for t in c.get('types') or []:
            if c.get('complex_id') and t.get('area_id') and t.get('general_price_manwon') is not None:
                out[(int(c['complex_id']),int(t['area_id']))]={
                    'complex_id':int(c['complex_id']),'area_id':int(t['area_id']),
                    'name':c.get('user_name') or c.get('kb_name'),'type_label':t.get('type_label'),
                    'general_price_manwon':float(t['general_price_manwon'])
                }
    return out

def current_snapshot(master,as_of=None):
    rows=list(flatten(master).values())
    return {'as_of':as_of or datetime.date.today().isoformat(),
            'source_kb_collected_at':master.get('kb_collected_at'),
            'items':rows}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--roll-baseline',action='store_true')
    ap.add_argument('--as-of')
    a=ap.parse_args()
    # Outside the scheduled Friday roll, keep the last completed week-to-week
    # comparison instead of overwriting it with Monday/weekday same-price data.
    if not a.roll_baseline and OUT.exists():
        old=load(OUT,{})
        print(json.dumps({'weekly_change_preserved':True,'latest_friday':old.get('latest_friday_as_of'),'previous_friday':old.get('previous_friday_as_of')},ensure_ascii=False))
        return
    cur=load(MASTER,{'items':[]});base=load(BASE,{'items':[]})
    ci,bi=flatten(cur),{(int(x['complex_id']),int(x['area_id'])):x for x in base.get('items') or [] if x.get('complex_id') and x.get('area_id')}
    rows=[]
    for key,x in ci.items():
        y=bi.get(key);cp=float(x['general_price_manwon']);pp=None if not y else float(y.get('general_price_manwon'))
        rows.append({**x,'current_manwon':cp,'previous_friday_manwon':pp,
                     'delta_manwon':None if pp is None else cp-pp,
                     'delta_pct':None if not pp else round((cp-pp)*100/pp,2)})
    payload={'status':'connected','basis':'last completed Friday KB general price vs prior Friday',
             'latest_friday_as_of':a.as_of or datetime.date.today().isoformat(),
             'current_kb_collected_at':cur.get('kb_collected_at'),
             'previous_friday_as_of':base.get('as_of'),
             'previous_friday_kb_collected_at':base.get('source_kb_collected_at'),
             'items':rows}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'weekly_change_rows':len(rows),'previous_friday':base.get('as_of')},ensure_ascii=False))
    if a.roll_baseline:
        BASE.write_text(json.dumps(current_snapshot(cur,a.as_of),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'baseline_rolled':True,'as_of':a.as_of},ensure_ascii=False))
if __name__=='__main__':main()
