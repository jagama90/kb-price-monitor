#!/usr/bin/env python3
"""Evaluate categorical buy-opportunity alerts without changing production output."""
import json,pathlib,statistics
R=pathlib.Path(__file__).resolve().parents[1]
SRC=R/'dist/turning_signal_research.json'; OUT=R/'dist/buy_opportunity_evaluation.json'
def med(v): return round(statistics.median(v),2) if v else None
def avg(v): return round(sum(v)/len(v),2) if v else None
def main():
 d=json.loads(SRC.read_text()); rows=d['rows']; out=[]
 for i,r in enumerate(rows):
  # Warm-up prevents edge artifacts. Signals use only values already computed at month t.
  if i<3: state='warmup'
  elif r.get('bottom_zone'): state='bottom_candidate'
  elif r.get('momentum_zone'): state='reaccel_candidate'
  else: state='observe'
  out.append({'ym':r['ym'],'state':state,'fwd_3m_pct':r.get('fwd_3m_pct'),'fwd_6m_pct':r.get('fwd_6m_pct'),'fwd_12m_pct':r.get('fwd_12m_pct')})
 stats={}
 for st in ('bottom_candidate','reaccel_candidate','observe'):
  a=[x for x in out if x['state']==st]
  stats[st]={'months':len(a)}
  for h in (3,6,12):
   v=[x[f'fwd_{h}m_pct'] for x in a if x.get(f'fwd_{h}m_pct') is not None]
   stats[st][f'fwd_{h}m_mean_pct']=avg(v);stats[st][f'fwd_{h}m_median_pct']=med(v)
   stats[st][f'fwd_{h}m_positive_rate_pct']=round(100*sum(x>0 for x in v)/len(v),1) if v else None
 OUT.write_text(json.dumps({'status':'research_only','purpose':'evaluate early buy-opportunity alert quality','rows':out,'stats':stats},ensure_ascii=False,indent=2))
 print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':
 main()
