#!/usr/bin/env python3
"""Backfill the exact historical demand inputs used by the buy-condition index.

For completed historical months the dashboard's matched-period comparison becomes
full calendar month vs the preceding full calendar month.  This preserves the
same formula without the current-month reporting-lag problem.
"""
import json,os,pathlib,datetime,time
from collect_molit_trades import SEOUL,fetch_all,summarize

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/molit_historical_backtest.json'\nCACHE=ROOT/'dist/molit_historical_month_cache.json'
START='202209'; END='202306'

def months(a,b):
 y,m=map(int,(a[:4],a[4:])); ey,em=map(int,(b[:4],b[4:]))
 out=[]
 while (y,m)<=(ey,em):
  out.append(f'{y:04d}{m:02d}');m+=1
  if m==13:y+=1;m=1
 return out

def pct(a,b): return round((a/b-1)*100,4) if b else None

def main():
 key=os.getenv('MOLIT_SERVICE_KEY')
 if not key: raise SystemExit('MOLIT_SERVICE_KEY secret is required')
 all_months=months(START,END)
 summaries={}
 for ym in all_months:
  rows=[]
  for code in SEOUL:
   rows.extend(fetch_all(code,ym,key))
   time.sleep(.03)
  summaries[ym]=summarize(rows)
  print(ym,summaries[ym]['total'])
 out=[]
 for ym in all_months[1:]:
  cur,prev=summaries[ym],summaries[all_months[all_months.index(ym)-1]]
  out.append({'ym':ym,'total':cur['total'],'under15_share':cur['under15_share'],
   'trade_count_pct':pct(cur['total'],prev['total']),
   'under15_share_pp':round(cur['under15_share']-prev['under15_share'],4)
      if cur['under15_share'] is not None and prev['under15_share'] is not None else None})
 payload={'status':'connected','source':'MOLIT apartment trade OpenAPI',
  'method':'completed_month_vs_previous_completed_month; same demand formula inputs as live dashboard',
  'start':START,'end':END,'rows':out,
  'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 print(json.dumps({'status':'connected','rows':len(out)},ensure_ascii=False))
if __name__=='__main__':main()
