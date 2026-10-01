#!/usr/bin/env python3
"""Backfill mature monthly transaction price-tier history for the active market scope.

This is intentionally separate from the fast daily collector: it only stores monthly
aggregates, never raw transaction history, and it excludes months whose reporting
window has not elapsed.
"""
import os,json,datetime,calendar,pathlib,time
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor,as_completed
import collect_molit_trades as base

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data_sources/molit_price_tier_history.json'
HISTORY_MONTHS=max(36,int(os.getenv('PRICE_TIER_BACKFILL_MONTHS','42')))
WORKERS=max(1,min(int(os.getenv('MOLIT_BACKFILL_WORKERS','8')),10))
FAST_TIMEOUT=max(3,float(os.getenv('MOLIT_BACKFILL_TIMEOUT','8')))
RETRY_TIMEOUT=max(FAST_TIMEOUT,float(os.getenv('MOLIT_BACKFILL_RETRY_TIMEOUT','15')))
REPORTING_WINDOW_DAYS=base.REPORTING_WINDOW_DAYS

def shift(y,m,delta):
    q=y*12+(m-1)+delta
    return q//12,q%12+1

def mature_months(as_of,count):
    out=[];delta=-1
    while len(out)<count:
        y,m=shift(as_of.year,as_of.month,delta)
        end=datetime.date(y,m,calendar.monthrange(y,m)[1])
        ready=end+datetime.timedelta(days=REPORTING_WINDOW_DAYS)
        if ready<=as_of:
            out.append((f'{y:04d}{m:02d}',ready))
        delta-=1
    return list(reversed(out))

def fetch_pairs(pairs,key,timeout,workers):
    results={};errors={}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs={pool.submit(base.fetch_all,code,ym,key,timeout):(code,ym) for code,ym in pairs}
        for fut in as_completed(futs):
            pair=futs[fut]
            try: results[pair]=fut.result()
            except Exception as e: errors[pair]=repr(e)
    return results,errors

def fetch_month(ym,key):
    pairs=[(code,ym) for code in base.DISTRICT_CODES]
    first,failed=fetch_pairs(pairs,key,FAST_TIMEOUT,min(WORKERS,len(pairs)))
    recovered={}
    if failed:
        time.sleep(.5)
        recovered,failed2=fetch_pairs(sorted(failed),key,RETRY_TIMEOUT,min(4,len(failed)))
        failed=failed2
    if failed:
        sample='; '.join(f'{c}:{m} {e}' for (c,m),e in list(failed.items())[:3])
        raise RuntimeError(f'backfill failed {ym}: {len(failed)} district pairs; {sample}')
    first.update(recovered)
    rows=[]
    for pair in pairs: rows.extend(first.get(pair) or [])
    summary=base.summarize(rows)
    if sum((summary.get('counts') or {}).values())!=summary.get('total'):
        raise RuntimeError(f'price-tier partition mismatch {ym}')
    return summary

def main():
    key=os.getenv('MOLIT_SERVICE_KEY')
    if not key: raise SystemExit('MOLIT_SERVICE_KEY secret is required')
    now=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date()
    desired=mature_months(now,HISTORY_MONTHS)
    try: old=json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    except Exception: old={}
    existing={str(x.get('period')):x for x in (old.get('months') or []) if x.get('period')}
    fetched=[];reused=[]
    for ym,ready in desired:
        period=ym[:4]+'-'+ym[4:]
        row=existing.get(period)
        if row and row.get('total',0)>0:
            row={**row,'mature':True,'reporting_window_elapsed_on':ready.isoformat()}
            existing[period]=row;reused.append(period);continue
        sm=fetch_month(ym,key)
        existing[period]={'period':period,**sm,'mature':True,'reporting_window_elapsed_on':ready.isoformat()}
        fetched.append(period)
        print(json.dumps({'stage':'price_tier_backfill','period':period,'total':sm['total'],'fetched_months':len(fetched)},ensure_ascii=False),flush=True)
    # Preserve newer diagnostic months but mark their maturity explicitly.
    for period,row in list(existing.items()):
        try:
            y,m=(int(x) for x in period.split('-',1));end=datetime.date(y,m,calendar.monthrange(y,m)[1]);ready=end+datetime.timedelta(days=REPORTING_WINDOW_DAYS)
            existing[period]={**row,'mature':ready<=now,'reporting_window_elapsed_on':ready.isoformat()}
        except Exception: pass
    months=[existing[k] for k in sorted(existing)[-120:]]
    mature=[x for x in months if x.get('mature') and x.get('total',0)>0]
    if len(mature)<36: raise RuntimeError(f'mature price-tier history still too short: {len(mature)}')
    out={
      'version':2,
      'scope':{'data_scope':base.MARKET_SCOPE.get('data_scope'),'market_scope':base.MARKET_SCOPE.get('market_scope'),'region_code':(base.MARKET_SCOPE.get('region') or {}).get('code')},
      'price_tier_config':base.PRICE_TIERS,
      'months':months,
      'backfill_meta':{'requested_mature_months':HISTORY_MONTHS,'mature_months_available':len(mature),'fetched_months':len(fetched),'reused_months':len(reused),
                       'reporting_window_days':REPORTING_WINDOW_DAYS,'raw_transactions_retained':False},
      'updated_at':now.isoformat()
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'ok','mature_months':len(mature),'fetched':len(fetched),'period_start':mature[0]['period'],'period_end':mature[-1]['period']},ensure_ascii=False))

if __name__=='__main__': main()
