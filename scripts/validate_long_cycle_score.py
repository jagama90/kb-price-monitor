#!/usr/bin/env python3
"""Train-only selection of a score signal, then untouched 2018+ holdout validation.\nTrigger score validation run.\n"""
import json,pathlib,statistics,itertools
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'dist/long_cycle_score_validation.json'
def pct(a,b): return (a/b-1)*100 if b else None
def avg(v): return round(sum(v)/len(v),2) if v else None
def med(v): return round(statistics.median(v),2) if v else None
def metrics(a):
 z={'signals':len(a)}
 for h in (3,6,12):
  v=[x[f'fwd_{h}'] for x in a if x.get(f'fwd_{h}') is not None]
  z[f'fwd_{h}m_mean_pct']=avg(v); z[f'fwd_{h}m_median_pct']=med(v)
  z[f'fwd_{h}m_positive_rate_pct']=round(100*sum(q>0 for q in v)/len(v),1) if v else None
 return z
def main():
 src=json.loads((R/'dist/long_cycle_master.json').read_text())['rows']; P=[float(x['price']['value']) for x in src]; T=[float(x['trade']['value']) for x in src]
 rows=[]
 for i,r in enumerate(src):
  if i<12: continue
  m1=pct(P[i],P[i-1]); m3=pct(P[i],P[i-3]); m6=pct(P[i],P[i-6]); tv=pct(T[i],sum(T[i-3:i])/3)
  m2=float(r['m2'].get('yoy_pct') or 0)
  x={'ym':r['ym'],'split':'train' if r['ym']<'201801' else 'holdout','m1':m1,'m3':m3,'m6':m6,'trade':tv,'m2':m2}
  for h in (3,6,12): x[f'fwd_{h}']=pct(P[i+h],P[i]) if i+h<len(P) else None
  rows.append(x)
 # Candidate family is declared here and selected using train only. Price weakness is required;
 # trade/liquidity can contribute points rather than hard-gating the signal.
 candidates=[]
 for minscore in (2,3):
  for tcut in (-10,0,10):
   for m2cut in (0,5,8):
    def hit(x,ms=minscore,tc=tcut,mc=m2cut):
     if not (-4<=x['m3']<=1.5): return False
     score=(1 if x['m1']>=0 else 0)+(1 if x['trade']>=tc else 0)+(1 if x['m2']>=mc else 0)+(1 if x['m6']<=1 else 0)
     return score>=ms
    a=[x for x in rows if x['split']=='train' and hit(x)]
    v=[x['fwd_6'] for x in a if x['fwd_6'] is not None]
    if len(v)>=5:
     # train-only objective balances return, hit rate and enough observations
     objective=(sum(v)/len(v)) + 0.03*(100*sum(q>0 for q in v)/len(v)) + min(len(v),12)*0.03
     candidates.append((objective,minscore,tcut,m2cut))
 candidates.sort(reverse=True); _,ms,tc,mc=candidates[0]
 def scorehit(x):
  if not (-4<=x['m3']<=1.5): return False
  score=(x['m1']>=0)+(x['trade']>=tc)+(x['m2']>=mc)+(x['m6']<=1)
  return score>=ms
 for x in rows:
  x['baseline']=x['m3']<=0 and x['m1']>=0; x['score_signal']=scorehit(x)
 summary={}
 for split in ('train','holdout','all'):
  rr=[x for x in rows if split=='all' or x['split']==split]
  summary[split]={'baseline':metrics([x for x in rr if x['baseline']]),'score_signal':metrics([x for x in rr if x['score_signal']])}
 OUT.write_text(json.dumps({'status':'research_only','no_future_leakage':True,'selection':'candidate parameters selected on pre-2018 train only; holdout untouched',
  'selected':{'min_score':ms,'trade_cut_pct':tc,'m2_yoy_cut_pct':mc,'price_m3_band':[-4,1.5]},'summary':summary,'rows':rows},ensure_ascii=False,indent=2))
 print(json.dumps({'selected':{'min_score':ms,'trade_cut_pct':tc,'m2_yoy_cut_pct':mc},'summary':summary},ensure_ascii=False))
if __name__=='__main__': main()
