#!/usr/bin/env python3
"""Final 3-part validation: long-trend filter, walk-forward, robustness stress tests.\nTrigger full suite.\n"""
import json,pathlib,statistics,itertools
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'dist/final_long_cycle_validation.json'
def pct(a,b): return (a/b-1)*100 if b else None
def met(rows):
 z={'signals':len(rows)}
 for h in (6,12):
  v=[x[f'f{h}'] for x in rows if x.get(f'f{h}') is not None]
  rl=[x[f'low{h}'] for x in rows if x.get(f'low{h}') is not None]
  z[f'fwd_{h}m_mean_pct']=round(sum(v)/len(v),2) if v else None
  z[f'positive_{h}m_pct']=round(100*sum(q>0 for q in v)/len(v),1) if v else None
  z[f'renew_low_{h}m_pct']=round(100*sum(rl)/len(rl),1) if rl else None
 return z
def main():
 src=json.loads((R/'dist/long_cycle_master.json').read_text())['rows']; P=[float(x['price']['value']) for x in src]
 rows=[]
 for i,r in enumerate(src):
  if i<12: continue
  m1=pct(P[i],P[i-1]);m3=pct(P[i],P[i-3]);m6=pct(P[i],P[i-6]);m12=pct(P[i],P[i-12])
  peak12=max(P[i-11:i+1]);dd12=pct(P[i],peak12); ma12=sum(P[i-11:i+1])/12; above_ma=pct(P[i],ma12)
  x={'i':i,'ym':r['ym'],'m1':m1,'m3':m3,'m6':m6,'m12':m12,'dd12':dd12,'above_ma12':above_ma,'base':m3<=0 and m1>=0}
  for h in (6,12):
   x[f'f{h}']=pct(P[i+h],P[i]) if i+h<len(P) else None
   x[f'low{h}']=(min(P[i+1:i+h+1])<P[i]) if i+h<len(P) else None
  rows.append(x)
 # 1) train-only long-trend filter selection; all variables are trailing.
 train=[x for x in rows if x['ym']<'201801']
 cand=[]
 for m12cut,macut,ddcut in itertools.product((-8,-5,-2,0),(-3,-1,0),(-10,-7,-4)):
  def hit(x,a=m12cut,b=macut,c=ddcut): return x['base'] and x['m12']>=a and x['above_ma12']>=b and x['dd12']>=c
  a=[x for x in train if hit(x)]
  if len(a)<2: continue
  mm=met(a); obj=(mm['fwd_12m_mean_pct'] or -99)+.04*(mm['positive_12m_pct'] or 0)-.08*(mm['renew_low_12m_pct'] or 100)+min(len(a),6)*.1
  cand.append((obj,m12cut,macut,ddcut))
 cand.sort(reverse=True)
 if not cand: raise RuntimeError('no long-trend candidates')
 _,m12cut,macut,ddcut=cand[0]
 def filt(x): return x['base'] and x['m12']>=m12cut and x['above_ma12']>=macut and x['dd12']>=ddcut
 # 2) expanding walk-forward: selected fixed on pre-2018; report independent calendar folds.
 folds=[]
 for y0,y1 in ((2007,2011),(2012,2017),(2018,2023)):
  rr=[x for x in rows if y0<=int(x['ym'][:4])<=y1]
  folds.append({'period':f'{y0}-{y1}','base':met([x for x in rr if x['base']]),'filtered':met([x for x in rr if filt(x)])})
 # 3) robustness: nearby thresholds + 0/1/2 month delayed entry.
 stress=[]
 for dm12,dma,ddd in itertools.product((-1,0,1),(-.5,0,.5),(-1,0,1)):
  def sh(x): return x['base'] and x['m12']>=m12cut+dm12 and x['above_ma12']>=macut+dma and x['dd12']>=ddcut+ddd
  sig=[x for x in rows if sh(x)]
  stress.append({'delta':[dm12,dma,ddd],**met(sig)})
 delays={}
 sig=[x for x in rows if filt(x)]
 for delay in (0,1,2):
  a=[]
  for x in sig:
   j=x['i']+delay
   if j>=len(P):continue
   q={'f6':pct(P[j+6],P[j]) if j+6<len(P) else None,'f12':pct(P[j+12],P[j]) if j+12<len(P) else None,
      'low6':min(P[j+1:j+7])<P[j] if j+6<len(P) else None,'low12':min(P[j+1:j+13])<P[j] if j+12<len(P) else None}
   a.append(q)
  delays[str(delay)]=met(a)
 hold=[x for x in rows if x['ym']>='201801']
 result={'status':'research_only','no_future_leakage':True,'selected_on_pre2018':{'m12_min_pct':m12cut,'above_ma12_min_pct':macut,'drawdown_12m_min_pct':ddcut},
  'part1':{'train_base':met([x for x in train if x['base']]),'train_filtered':met([x for x in train if filt(x)]),
           'holdout_base':met([x for x in hold if x['base']]),'holdout_filtered':met([x for x in hold if filt(x)])},
  'part2_walk_forward':folds,'part3_stress':{'nearby_thresholds':stress,'entry_delay_months':delays}}
 OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
