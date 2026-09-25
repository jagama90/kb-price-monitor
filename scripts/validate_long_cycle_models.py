#!/usr/bin/env python3
"""Compare price-only vs price+trade+M2 long-cycle signals without future leakage."""
import json,pathlib,statistics
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'dist/long_cycle_model_validation.json'
def pct(a,b): return (a/b-1)*100 if b else None
def med(v): return round(statistics.median(v),2) if v else None
def avg(v): return round(sum(v)/len(v),2) if v else None
def stats(rows,flag,subset):
 a=[x for x in rows if x[flag] and (subset=='all' or x['split']==subset)]
 z={'signals':len(a)}
 for h in (3,6,12):
  v=[x[f'fwd_{h}m_pct'] for x in a if x[f'fwd_{h}m_pct'] is not None]
  z[f'fwd_{h}m_mean_pct']=avg(v); z[f'fwd_{h}m_median_pct']=med(v)
  z[f'fwd_{h}m_positive_rate_pct']=round(100*sum(q>0 for q in v)/len(v),1) if v else None
 return z
def main():
 src=json.loads((R/'dist/long_cycle_master.json').read_text())['rows']
 P=[float(x['price']['value']) for x in src]; T=[float(x['trade']['value']) for x in src]
 out=[]
 for i,r in enumerate(src):
  if i<6: continue
  m1=pct(P[i],P[i-1]); m3=pct(P[i],P[i-3]); m6=pct(P[i],P[i-6])
  prior3=sum(T[i-3:i])/3; trade=pct(T[i],prior3)
  m2=float(r['m2'].get('yoy_pct') or 0)
  # Fixed ex-ante rules. Enhanced model confirms a price bottom-watch with demand/liquidity evidence.
  price_only=(m3<=0 and m1>=0)
  enhanced=price_only and trade>=0 and m2>0
  out.append({'ym':r['ym'],'split':'train' if r['ym']<'201801' else 'holdout',
    'price_only':price_only,'enhanced':enhanced,'price_mom_1m':m1,'price_mom_3m':m3,
    'price_mom_6m':m6,'trade_vs_prior3_pct':trade,'m2_yoy_pct':m2})
 for x in out:
  i=next(j for j,r in enumerate(src) if r['ym']==x['ym'])
  for h in (3,6,12): x[f'fwd_{h}m_pct']=pct(P[i+h],P[i]) if i+h<len(P) else None
 summary={}
 for subset in ('train','holdout','all'):
  summary[subset]={'price_only':stats(out,'price_only',subset),'enhanced':stats(out,'enhanced',subset)}
 OUT.write_text(json.dumps({'status':'research_only','no_future_leakage':True,
  'split_rule':'train < 2018-01; holdout >= 2018-01; fixed rules applied unchanged',
  'baseline_rule':'m3<=0 and m1>=0',
  'enhanced_rule':'baseline AND current trade >= prior-3m average AND M2 YoY > 0',
  'summary':summary,'rows':out},ensure_ascii=False,indent=2))
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__': main()
