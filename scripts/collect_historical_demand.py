#!/usr/bin/env python3
"""Backfill historical demand inputs used by the buy-condition index."""
import json,os,pathlib,datetime
from concurrent.futures import ThreadPoolExecutor,as_completed
from collect_molit_trades import DISTRICT_CODES,MARKET_SCOPE,fetch_all,summarize

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/molit_historical_backtest.json'
CACHE=ROOT/'dist/molit_historical_month_cache.json'
START='202208'
HISTORY_TIMEOUT=max(10,float(os.getenv('MOLIT_HISTORY_TIMEOUT','30')))
HISTORY_WORKERS=max(1,min(int(os.getenv('MOLIT_HISTORY_WORKERS','8')),12))
# Collect through the previous calendar month, but certify only through t-2 so
# the statutory transaction-reporting window has elapsed.
today=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
def ym_shift(y,m,delta):
 q=y*12+m-1+delta
 return f'{q//12:04d}{q%12+1:02d}'
END=ym_shift(today.year,today.month,-1)
CERTIFIED_THROUGH=ym_shift(today.year,today.month,-2)

def months(a,b):
 y,m=map(int,(a[:4],a[4:])); ey,em=map(int,(b[:4],b[4:])); out=[]
 while (y,m)<=(ey,em):
  out.append(f'{y:04d}{m:02d}'); m+=1
  if m==13: y+=1; m=1
 return out

def pct(a,b): return round((a/b-1)*100,4) if b else None

def main():
 key=os.getenv('MOLIT_SERVICE_KEY')
 if not key: raise SystemExit('MOLIT_SERVICE_KEY secret is required')
 all_months=months(START,END)
 try: summaries=json.loads(CACHE.read_text()).get('summaries',{})
 except Exception: summaries={}
 refresh=set(all_months[-2:])
 for ym in all_months:
  if ym in summaries and summaries[ym].get('total') is not None and ym not in refresh:
   print(ym,summaries[ym]['total'],'cached'); continue
  rows=[]; errors={}
  with ThreadPoolExecutor(max_workers=min(HISTORY_WORKERS,len(DISTRICT_CODES))) as pool:
   tasks={pool.submit(fetch_all,code,ym,key,HISTORY_TIMEOUT):code for code in DISTRICT_CODES}
   for fut in as_completed(tasks):
    code=tasks[fut]
    try: rows.extend(fut.result())
    except Exception as e: errors[code]=repr(e)
  if errors:
   raise RuntimeError(f'MOLIT historical demand failed {ym}: {errors}')
  summaries[ym]=summarize(rows)
  CACHE.parent.mkdir(exist_ok=True)
  CACHE.write_text(json.dumps({'summaries':summaries},ensure_ascii=False,indent=2))
  print(ym,summaries[ym]['total'])
 out=[]
 for i,ym in enumerate(all_months[1:],1):
  cur,prev=summaries[ym],summaries[all_months[i-1]]
  out.append({'ym':ym,'total':cur['total'],'under15_share':cur['under15_share'],
   'trade_count_pct':pct(cur['total'],prev['total']),
   'under15_share_pp':round(cur['under15_share']-prev['under15_share'],4)
    if cur['under15_share'] is not None and prev['under15_share'] is not None else None})
 payload={'status':'connected','source':'MOLIT apartment trade OpenAPI',
  'method':'completed_month_vs_previous_completed_month; same demand formula inputs as live dashboard',
  'scope':{'market_scope_id':MARKET_SCOPE.get('market_scope_id'),'data_scope':MARKET_SCOPE.get('data_scope'),
   'market_scope':MARKET_SCOPE.get('market_scope'),'region':MARKET_SCOPE.get('region'),
   'district_codes':DISTRICT_CODES},
  'start':all_months[1],'end':END,'certified_through':CERTIFIED_THROUGH,'rows':out,
  'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 print(json.dumps({'status':'connected','rows':len(out)},ensure_ascii=False))
if __name__=='__main__': main()
