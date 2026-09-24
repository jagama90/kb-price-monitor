#!/usr/bin/env python3
"""Backfill historical demand inputs used by the buy-condition index."""
import json,os,pathlib,datetime,time
from collect_molit_trades import SEOUL,fetch_all,summarize

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/molit_historical_backtest.json'
CACHE=ROOT/'dist/molit_historical_month_cache.json'
START='202208'
# Last completed month only; the live dashboard handles the current partial month separately.
today=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date()
END=f'{today.year if today.month>1 else today.year-1:04d}{today.month-1 if today.month>1 else 12:02d}'

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
 for ym in all_months:
  if ym in summaries and summaries[ym].get('total') is not None:
   print(ym,summaries[ym]['total'],'cached'); continue
  rows=[]
  for code in SEOUL:
   rows.extend(fetch_all(code,ym,key)); time.sleep(.03)
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
  'start':all_months[1],'end':END,'rows':out,
  'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 print(json.dumps({'status':'connected','rows':len(out)},ensure_ascii=False))
if __name__=='__main__': main()
