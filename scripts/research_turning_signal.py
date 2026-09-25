#!/usr/bin/env python3
"""Compare the production market-state score with a separate turning-point signal.
Research output only: this script does not change the production score."""
import json,pathlib,math,statistics,datetime
R=pathlib.Path(__file__).resolve().parents[1]
SRC=R/'dist/final_backtest.json'; OUT=R/'dist/turning_signal_research.json'; MORT=R/'data_sources/ecos_mortgage_rate.json'
def clamp(x): return max(0,min(100,x))
def corr(a,b):
 z=[(x,y) for x,y in zip(a,b) if x is not None and y is not None]
 if len(z)<3:return None
 ax=sum(x for x,_ in z)/len(z); ay=sum(y for _,y in z)/len(z)
 num=sum((x-ax)*(y-ay) for x,y in z); dx=sum((x-ax)**2 for x,_ in z); dy=sum((y-ay)**2 for _,y in z)
 return round(num/math.sqrt(dx*dy),3) if dx and dy else None
def pct_rank(hist,v):
 if not hist:return 50.0
 return 100*sum(x<=v for x in hist)/len(hist)
def mean_fwd(rows,key,idxs):
 vals=[rows[i].get(key) for i in idxs if rows[i].get(key) is not None]
 return round(sum(vals)/len(vals),2) if vals else None
def main():
 d=json.loads(SRC.read_text()); rows=d['rows']; outrows=[]
 # Turning signal deliberately separates distress/cheapness from evidence that deterioration is ending.
 # All normalisation is expanding-window only, so no future observations leak into a historical score.
 for i,r in enumerate(rows):
  c=r['components']; hist=rows[:i+1]
  cheap=c['value']
  distress=clamp(100-c['sentiment'])
  # Improvements use 1m and 3m deltas. Positive demand/sentiment/finance changes indicate marginal turn.
  def delta(k,n):
   return c[k]-rows[i-n]['components'][k] if i>=n else 0
  turn_raw=.30*delta('demand',1)+.20*delta('sentiment',1)+.15*delta('finance',1)+.15*delta('demand',3)+.10*delta('sentiment',3)+.10*delta('finance',3)
  rawhist=[]
  for j in range(i+1):
   cj=rows[j]['components']
   def dj(k,n): return cj[k]-rows[j-n]['components'][k] if j>=n else 0
   rawhist.append(.30*dj('demand',1)+.20*dj('sentiment',1)+.15*dj('finance',1)+.15*dj('demand',3)+.10*dj('sentiment',3)+.10*dj('finance',3))
  turn=pct_rank(rawhist,turn_raw)
  # Opportunity requires both pain/valuation and a marginal turn; harmonic-style gate prevents one leg dominating.
  setup=.55*cheap+.45*distress
  opportunity=round((setup*turn)/100,1)
  outrows.append({'ym':r['ym'],'market_state':r['score'],'setup':round(setup,1),'turn':round(turn,1),'opportunity':opportunity,
   'cheapness':round(cheap,1),'distress':round(distress,1),'target_price':r['target_price'],
   'fwd_1m_pct':r.get('fwd_1m_pct'),'fwd_3m_pct':r.get('fwd_3m_pct'),'fwd_6m_pct':r.get('fwd_6m_pct'),'fwd_12m_pct':r.get('fwd_12m_pct')})
 metrics={}
 for h in (1,3,6,12):
  key=f'fwd_{h}m_pct'; metrics[f'market_state_vs_fwd_{h}m_corr']=corr([x['market_state'] for x in outrows],[x[key] for x in outrows]); metrics[f'opportunity_vs_fwd_{h}m_corr']=corr([x['opportunity'] for x in outrows],[x[key] for x in outrows])
 valid=[i for i,x in enumerate(outrows) if x['fwd_6m_pct'] is not None]; n=max(1,len(valid)//3)
 low=sorted(valid,key=lambda i:outrows[i]['opportunity'])[:n]; high=sorted(valid,key=lambda i:outrows[i]['opportunity'])[-n:]
 metrics['opportunity_low_third_mean_fwd_6m_pct']=mean_fwd(outrows,'fwd_6m_pct',low)
 metrics['opportunity_high_third_mean_fwd_6m_pct']=mean_fwd(outrows,'fwd_6m_pct',high)
 # Component dispersion/correlation helps diagnose cancellation in the production weighted sum.
 comps=['finance','sentiment','demand','value','supply']; dispersion={}
 for k in comps:
  v=[x['components'][k] for x in rows]; dispersion[k]={'min':round(min(v),1),'max':round(max(v),1),'stdev':round(statistics.pstdev(v),1),'corr_fwd_6m':corr(v,[x.get('fwd_6m_pct') for x in rows])}
 # Mortgage-rate overlay is diagnostic only. Current source starts in 2024, so it is not yet eligible for production weighting.\n mort=[]\n if MORT.exists():\n  md=json.loads(MORT.read_text()); mm={}\n  for x in md.get('series',[]):\n   if x.get('item')=='주택담보대출': mm[x['period']]=x['rate_pct']\n  for i,x in enumerate(outrows):\n   rate=mm.get(x['ym']); prev=mm.get(outrows[i-1]['ym']) if i else None\n   mort.append({'ym':x['ym'],'mortgage_rate_pct':rate,'mom_bp':round((rate-prev)*100,1) if rate is not None and prev is not None else None,'fwd_6m_pct':x['fwd_6m_pct']})\n  paired=[x for x in mort if x['mortgage_rate_pct'] is not None]\n  metrics['mortgage_rate_available_months']=len(paired)\n  metrics['mortgage_rate_level_vs_fwd_6m_corr']=corr([x['mortgage_rate_pct'] for x in paired],[x['fwd_6m_pct'] for x in paired])\n  metrics['mortgage_rate_mom_bp_vs_fwd_6m_corr']=corr([x['mom_bp'] for x in paired],[x['fwd_6m_pct'] for x in paired])\n payload={'status':'research_only','production_formula_unchanged':True,'no_future_leakage':True,
  'method':'setup = 55% cheapness + 45% sentiment distress; turn = expanding-percentile of weighted 1m/3m improvements in demand, sentiment, finance; opportunity = setup * turn / 100',
  'rows':outrows,'mortgage_rate_overlay':mort,'metrics':metrics,'component_dispersion':dispersion,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)); print(json.dumps(metrics,ensure_ascii=False))
if __name__=='__main__': main()
