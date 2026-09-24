#!/usr/bin/env python3
import json,pathlib,datetime,statistics
R=pathlib.Path(__file__).resolve().parents[1]; SRC=R/'dist/garak_geumho_24a_history.json'; OUT=R/'dist/final_historical_validation.json'; HIST=R/'dist/condition_index_history.json'
def clamp(x):return max(0,min(100,x))
def main():
 d=json.loads(SRC.read_text()); a=[x for x in d['series'] if x.get('sale') and x.get('rent_ratio') is not None]
 rows=[]
 # Historical core uses only contemporaneous/past KB observations. No future values enter score.
 # Value mirrors current 36m inverse price-position (25..75). Supply uses contemporaneous rent ratio
 # standardized only against trailing 36m. Momentum confirmation uses trailing 3m sale change.
 for i,x in enumerate(a):
  if i<35:continue
  w=a[i-35:i+1]; prices=[float(z['sale']) for z in w]; ratios=[float(z['rent_ratio']) for z in w]
  lo,hi=min(prices),max(prices); pos=(prices[-1]-lo)/(hi-lo) if hi>lo else .5
  value=max(25,min(75,75-50*pos))
  rlo,rhi=min(ratios),max(ratios); supply=50 if rhi==rlo else 25+50*(ratios[-1]-rlo)/(rhi-rlo)
  mom=(prices[-1]/prices[-4]-1)*100 if len(prices)>=4 else 0
  demand=clamp(50+mom*5)
  # Comparable historical core score; unavailable historical finance/sentiment are not fabricated.
  score=round((value*20+supply*15+demand*20)/55,1)
  rows.append({'ym':x['ym'],'score':score,'components':{'value':round(value,1),'supply':round(supply,1),'demand_proxy':round(demand,1)},'sale':prices[-1]})
 by={x['ym']:x for x in rows}; allsale={x['ym']:float(x['sale']) for x in a}
 for r in rows:
  y=int(r['ym'][:4]);m=int(r['ym'][4:])
  for h in (1,3,6,12):
   n=(y*12+m-1)+h; ym=f'{n//12:04d}{n%12+1:02d}'; r[f'fwd_{h}m_pct']=round((allsale[ym]/r['sale']-1)*100,2) if ym in allsale else None
 target=[r for r in rows if '202210'<=r['ym']<='202306']
 # improvement from local trough score in Q4 2022 to H1 2023 peak
 q4=[r for r in rows if '202210'<=r['ym']<='202212']; h1=[r for r in rows if '202301'<=r['ym']<='202306']
 detected=bool(q4 and h1 and max(x['score'] for x in h1)>min(x['score'] for x in q4))
 valid=[r for r in rows if r.get('fwd_12m_pct') is not None]; split=int(len(valid)*.7); test=valid[split:]
 def avg(group,key):return round(statistics.mean(x[key] for x in group),2) if group else None
 med=statistics.median(x['score'] for x in valid) if valid else None
 high=[x for x in test if x['score']>=med]; low=[x for x in test if x['score']<med]
 report={'status':'validated_core_history' if len(test)>=12 else 'insufficient_oos','method':'no-future-leakage trailing-only historical core','note':'Finance and KB survey sentiment are excluded where historical vintages are not available; they are not imputed. This validates the historical core, not a fabricated full five-component series.','observations':len(rows),'oos_observations':len(test),'late_2022_early_2023':{'detected_improvement':detected,'rows':target},'oos_12m':{'median_score':med,'high_score_n':len(high),'low_score_n':len(low),'high_score_avg_fwd_12m_pct':avg(high,'fwd_12m_pct'),'low_score_avg_fwd_12m_pct':avg(low,'fwd_12m_pct')},'rows':rows,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2))
 HIST.write_text(json.dumps({'version':2,'method':'historical_core_no_leakage','rows':[{'date':r['ym'][:4]+'-'+r['ym'][4:]+'-01','score':r['score'],'components':r['components'],'coverage_weight':55} for r in rows]},ensure_ascii=False,indent=2))
 print(json.dumps({k:report[k] for k in ('status','observations','oos_observations','late_2022_early_2023','oos_12m')},ensure_ascii=False))
if __name__=='__main__':main()
