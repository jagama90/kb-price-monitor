#!/usr/bin/env python3
"""Validate false-bottom rejection using train-only selection and untouched 2018+ holdout.\nTrigger validation run.\n"""
import json,pathlib,itertools,statistics
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'dist/false_bottom_validation.json'
def pct(a,b): return (a/b-1)*100 if b else None
def met(a):
 z={'signals':len(a)}
 for h in (6,12):
  v=[x[f'fwd_{h}'] for x in a if x[f'fwd_{h}'] is not None]
  z[f'fwd_{h}m_mean_pct']=round(sum(v)/len(v),2) if v else None
  z[f'fwd_{h}m_positive_rate_pct']=round(100*sum(q>0 for q in v)/len(v),1) if v else None
  d=[x[f'renew_low_{h}m'] for x in a if x[f'renew_low_{h}m'] is not None]
  z[f'renew_low_{h}m_rate_pct']=round(100*sum(d)/len(d),1) if d else None
 return z
def main():
 src=json.loads((R/'dist/long_cycle_master.json').read_text())['rows'];P=[float(x['price']['value']) for x in src];T=[float(x['trade']['value']) for x in src]
 a=[]
 for i,r in enumerate(src):
  if i<12: continue
  m1=pct(P[i],P[i-1]);m3=pct(P[i],P[i-3]);m6=pct(P[i],P[i-6]); trade_yoy=pct(T[i],T[i-12]);m2=float(r['m2'].get('yoy_pct') or 0)
  # persistence known at t only: current level vs 2 months ago, plus last two monthly changes
  up2=(P[i]>=P[i-1] and P[i-1]>=P[i-2]); rec2=pct(P[i],P[i-2])
  x={'ym':r['ym'],'split':'train' if r['ym']<'201801' else 'holdout','m1':m1,'m3':m3,'m6':m6,'trade_yoy':trade_yoy,'m2':m2,'up2':up2,'rec2':rec2}
  x['base']=m3<=0 and m1>=0
  for h in (6,12):
   x[f'fwd_{h}']=pct(P[i+h],P[i]) if i+h<len(P) else None
   x[f'renew_low_{h}m']=(min(P[i+1:i+h+1])<P[i]) if i+h<len(P) else None
  a.append(x)
 # Predeclared confirmation family; choose only on train. Penalize renewed lows heavily.
 cand=[]
 for need_up2,rec_cut,trade_cut,m2_cut in itertools.product((False,True),(0,0.3,0.6),(-20,0,20),(0,5,8)):
  def hit(x,nu=need_up2,rc=rec_cut,tc=trade_cut,mc=m2_cut):
   return x['base'] and (not nu or x['up2']) and x['rec2']>=rc and x['trade_yoy']>=tc and x['m2']>=mc
  tr=[x for x in a if x['split']=='train' and hit(x)]
  if len(tr)<3: continue
  m=met(tr); obj=(m['fwd_12m_mean_pct'] or -99)+0.04*(m['fwd_12m_positive_rate_pct'] or 0)-0.06*(m['renew_low_12m_rate_pct'] or 100)+min(len(tr),8)*0.05
  cand.append((obj,need_up2,rec_cut,trade_cut,m2_cut))
 cand.sort(reverse=True);_,nu,rc,tc,mc=cand[0]
 def confirm(x): return x['base'] and (not nu or x['up2']) and x['rec2']>=rc and x['trade_yoy']>=tc and x['m2']>=mc
 for x in a:x['confirmed']=confirm(x)
 summary={}
 for sp in ('train','holdout','all'):
  rr=[x for x in a if sp=='all' or x['split']==sp]
  summary[sp]={'base':met([x for x in rr if x['base']]),'confirmed':met([x for x in rr if x['confirmed']])}
 OUT.write_text(json.dumps({'status':'research_only','no_future_leakage':True,'selection':'confirmation parameters selected on pre-2018 only',
 'selected':{'require_two_consecutive_up_months':nu,'two_month_recovery_cut_pct':rc,'trade_yoy_cut_pct':tc,'m2_yoy_cut_pct':mc},
 'summary':summary,'rows':a},ensure_ascii=False,indent=2));print(json.dumps({'selected':{'up2':nu,'rec2':rc,'trade_yoy':tc,'m2_yoy':mc},'summary':summary},ensure_ascii=False))
if __name__=='__main__':main()
