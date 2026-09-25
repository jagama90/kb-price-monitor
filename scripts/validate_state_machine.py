#!/usr/bin/env python3
"""Validate staged entry: precision early warning -> price turn -> long-trend confirmation."""
import json,pathlib,statistics
R=pathlib.Path(__file__).resolve().parents[1];OUT=R/'dist/state_machine_validation.json'
def pct(a,b):return (a/b-1)*100 if b else None
def met(a):
 z={'entries':len(a)}
 for h in (3,6,12):
  v=[x[f'f{h}'] for x in a if x.get(f'f{h}') is not None]
  z[f'fwd_{h}m_mean_pct']=round(sum(v)/len(v),2) if v else None
  z[f'positive_{h}m_pct']=round(100*sum(q>0 for q in v)/len(v),1) if v else None
  lows=[x[f'low{h}'] for x in a if x.get(f'low{h}') is not None]
  z[f'renew_low_{h}m_pct']=round(100*sum(lows)/len(lows),1) if lows else None
 return z
def main():
 m=json.loads((R/'dist/long_cycle_master.json').read_text())['rows'];q=json.loads((R/'dist/turning_signal_research.json').read_text())['rows']
 qm={x['ym']:x for x in q};P=[float(x['price']['value']) for x in m];events=[]
 for i,x in enumerate(m):
  if i<12 or x['ym'] not in qm:continue
  z=qm[x['ym']];m1=pct(P[i],P[i-1]);m3=pct(P[i],P[i-3]);m12=pct(P[i],P[i-12]);ma=sum(P[i-11:i+1])/12
  early=bool(z.get('bottom_zone'))
  price_turn=(m3<=0 and m1>=0)
  long_ok=price_turn and m12>=-5 and pct(P[i],ma)>=-3 and pct(P[i],max(P[i-11:i+1]))>=-4
  row={'i':i,'ym':x['ym'],'early':early,'price_turn':price_turn,'long_confirmed':long_ok}
  for h in (3,6,12):
   row[f'f{h}']=pct(P[i+h],P[i]) if i+h<len(P) else None
   row[f'low{h}']=(min(P[i+1:i+h+1])<P[i]) if i+h<len(P) else None
  events.append(row)
 # Entry events: first month entering each stage, avoiding repeated monthly counting.
 stages={}
 for key in ('early','price_turn','long_confirmed'):
  a=[];prev=False
  for x in events:
   cur=x[key]
   if cur and not prev:a.append(x)
   prev=cur
  stages[key]=a
 # Cohorts beginning with a new early-warning episode; measure first subsequent turn within 12m.
 cohorts=[]
 starts=stages['early']
 idx={x['ym']:n for n,x in enumerate(events)}
 for s in starts:
  k=idx[s['ym']];future=events[k:min(len(events),k+13)]
  pt=next((x for x in future if x['price_turn']),None);lc=next((x for x in future if x['long_confirmed']),None)
  cohorts.append({'early_ym':s['ym'],'price_turn_ym':pt['ym'] if pt else None,'months_to_price_turn':future.index(pt) if pt else None,
   'long_confirmed_ym':lc['ym'] if lc else None,'months_to_long_confirmed':future.index(lc) if lc else None})
 payload={'status':'research_only','no_future_leakage':True,
 'state_machine':['observe','precision_early_warning','price_turn_confirmed','long_trend_confirmed','recovery_or_reacceleration'],
 'entry_metrics':{k:met(v) for k,v in stages.items()},'entry_events':{k:[x['ym'] for x in v] for k,v in stages.items()},
 'early_warning_cohorts':cohorts}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2));print(json.dumps(payload,ensure_ascii=False))
if __name__=='__main__':main()
