#!/usr/bin/env python3
"""Long-cycle state validation with strictly trailing features and forward-only evaluation labels."""
import json,pathlib,statistics
R=pathlib.Path(__file__).resolve().parents[1]; SRC=R/'dist/long_cycle_master.json'; OUT=R/'dist/long_cycle_regime_backtest.json'
def pct(a,b): return (a/b-1)*100 if a is not None and b else None
def mean(v): return round(sum(v)/len(v),2) if v else None
def median(v): return round(statistics.median(v),2) if v else None
def main():
 rows=json.loads(SRC.read_text()).get('rows',[]); out=[]; prices=[]; trades=[]
 for i,r in enumerate(rows):
  p=float(r['price'].get('value') or 0); t=float(r['trade'].get('value') or 0); prices.append(p); trades.append(t)
  m1=pct(p,prices[i-1]) if i>=1 else None; m3=pct(p,prices[i-3]) if i>=3 else None; m6=pct(p,prices[i-6]) if i>=6 else None
  t3=pct(t,sum(trades[max(0,i-5):i-2])/len(trades[max(0,i-5):i-2])) if i>=5 and trades[i-5:i-2] else None
  if m3 is None: state='warmup'
  elif m3<-3: state='decline'
  elif m3<=0 and (m1 or 0)>=0: state='bottom_watch'
  elif m3>0 and (m1 or 0)>0: state='recovery'
  else: state='observe'
  out.append({'ym':r['ym'],'state':state,'price_mom_1m':m1,'price_mom_3m':m3,'price_mom_6m':m6,'trade_vs_prior3_pct':t3})
 for i,x in enumerate(out):
  for h in (3,6,12): x[f'fwd_{h}m_pct']=pct(prices[i+h],prices[i]) if i+h<len(prices) else None
 stats={}
 for st in ('decline','bottom_watch','recovery','observe'):
  a=[x for x in out if x['state']==st]; stats[st]={'months':len(a)}
  for h in (3,6,12):
   v=[x[f'fwd_{h}m_pct'] for x in a if x[f'fwd_{h}m_pct'] is not None]
   stats[st][f'fwd_{h}m_mean_pct']=mean(v); stats[st][f'fwd_{h}m_median_pct']=median(v)
   stats[st][f'fwd_{h}m_positive_rate_pct']=round(100*sum(z>0 for z in v)/len(v),1) if v else None
 OUT.write_text(json.dumps({'status':'research_only','thresholds_provisional':True,'no_future_leakage':True,'feature_rule':'all state features use month t or earlier only; forward returns are labels only','rows':out,'stats':stats},ensure_ascii=False,indent=2))
 print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__': main()
