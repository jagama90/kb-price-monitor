#!/usr/bin/env python3
"""Freeze long-cycle rule and test agreement/conflict with the unchanged 2022+ precision research model."""
import json,pathlib,statistics
R=pathlib.Path(__file__).resolve().parents[1];OUT=R/'dist/integrated_model_validation.json'
def pct(a,b):return (a/b-1)*100 if b else None
def main():
 m=json.loads((R/'dist/long_cycle_master.json').read_text())['rows']; q=json.loads((R/'dist/turning_signal_research.json').read_text())['rows']
 P=[float(x['price']['value']) for x in m]; long={}
 for i,x in enumerate(m):
  if i<12:continue
  m1=pct(P[i],P[i-1]);m3=pct(P[i],P[i-3]);m12=pct(P[i],P[i-12]);ma=sum(P[i-11:i+1])/12;above=pct(P[i],ma);dd=pct(P[i],max(P[i-11:i+1]))
  base=m3<=0 and m1>=0; confirmed=base and m12>=-5 and above>=-3 and dd>=-4
  long[x['ym']]={'base':base,'confirmed':confirmed,'m1':round(m1,2),'m3':round(m3,2),'m12':round(m12,2)}
 out=[]
 for x in q:
  l=long.get(x['ym']); 
  if not l:continue
  # precision states are existing research outputs, not retuned here.
  precision_bottom=bool(x.get('bottom_zone')); precision_momentum=bool(x.get('momentum_zone'))
  if l['confirmed'] and precision_bottom: state='strong_bottom'
  elif l['confirmed']: state='long_cycle_only'
  elif precision_bottom: state='precision_early'
  elif precision_momentum: state='momentum_reaccel'
  else: state='observe'
  out.append({'ym':x['ym'],'state':state,'long_confirmed':l['confirmed'],'precision_bottom':precision_bottom,'precision_momentum':precision_momentum,
    'opportunity':x.get('opportunity'),'fwd_3m_pct':x.get('fwd_3m_pct'),'fwd_6m_pct':x.get('fwd_6m_pct'),'fwd_12m_pct':x.get('fwd_12m_pct')})
 def met(state):
  a=[x for x in out if x['state']==state];z={'months':len(a)}
  for h in (3,6,12):
   v=[x[f'fwd_{h}m_pct'] for x in a if x[f'fwd_{h}m_pct'] is not None]
   z[f'fwd_{h}m_mean_pct']=round(sum(v)/len(v),2) if v else None;z[f'fwd_{h}m_positive_pct']=round(100*sum(y>0 for y in v)/len(v),1) if v else None
  return z
 states={s:met(s) for s in ('strong_bottom','long_cycle_only','precision_early','momentum_reaccel','observe')}
 conflicts=[x for x in out if x['long_confirmed'] != x['precision_bottom']]
 payload={'status':'research_only','production_formula_unchanged':True,'long_rule_frozen':{'base':'m3<=0 and m1>=0','m12_min':-5,'above_ma12_min':-3,'drawdown12_min':-4},
 'integration_rule_candidate':{'strong_bottom':'long confirmed AND precision bottom','precision_early':'precision bottom before long confirmation','momentum_reaccel':'existing precision momentum zone','observe':'otherwise'},
 'summary':states,'overlap_months':len(out),'conflict_months':len(conflicts),'conflicts':conflicts,'rows':out}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2));print(json.dumps({'summary':states,'overlap':len(out),'conflicts':len(conflicts)},ensure_ascii=False))
if __name__=='__main__':main()
