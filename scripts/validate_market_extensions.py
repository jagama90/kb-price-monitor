#!/usr/bin/env python3
"""Leakage-safe validation of breadth, affordability and local-temperature extensions."""
import json,pathlib,datetime,statistics,math
R=pathlib.Path(__file__).resolve().parents[1]
A=R/'dist/affordability_engine.json';T=R/'dist/regional_temperature_history.json';P=R/'data_sources/reb_long_cycle.json';O=R/'dist/market_extension_validation.json'
def mean(a):return round(sum(a)/len(a),3) if a else None
def med(a):return round(statistics.median(a),3) if a else None
def stats(rows,key):
 vals=[x[key] for x in rows if x.get(key) is not None]
 return {'n':len(vals),'mean':mean(vals),'median':med(vals),'positive_pct':round(100*sum(v>0 for v in vals)/len(vals),1) if vals else None}
def qmedian(vals):
 vals=sorted(v for v in vals if v is not None);return statistics.median(vals) if vals else None
def main():
 a=json.loads(A.read_text());t=json.loads(T.read_text());p=json.loads(P.read_text())
 am={x['ym']:x for x in a.get('rows',[])};tm={x['ym']:x for x in t.get('rows',[])}
 pr={x['ym']:float(x['value']) for x in p.get('series',{}).get('price',[]) if x.get('ym') and x.get('value') is not None}
 months=sorted(set(pr)&set(am)&set(tm)); rows=[]
 for i,ym in enumerate(months):
  idx=months.index(ym)
  def ret_lag(lag):
   if idx<lag:return None
   prev=months[idx-lag]
   # require calendar-contiguous lag, not just observed-row lag
   y=int(ym[:4]);m=int(ym[4:]);q=y*12+m-1-lag;exp=f'{q//12:04d}{q%12+1:02d}'
   return None if prev!=exp else (pr[ym]/pr[prev]-1)*100
  m1=ret_lag(1);m3=ret_lag(3)
  x={'ym':ym,'m1':m1,'m3':m3,
     'afford_impulse':am[ym].get('loan_capacity_change_3m_pct'),
     'payment_pressure':am[ym].get('payment_change_3m_pct'),
     'breadth':tm[ym].get('all_interest_breadth_up_pct'),
     'songpa_breadth':tm[ym].get('songpa_breadth_up_pct'),
     'songpa_gap':tm[ym].get('songpa_vs_seoul_gap_pp'),
     'songpa_fwd_3m':tm[ym].get('songpa_fwd_3m_median_pct'),
     'songpa_fwd_6m':tm[ym].get('songpa_fwd_6m_median_pct'),
     'songpa_fwd_12m':tm[ym].get('songpa_fwd_12m_median_pct')}
  for h in (3,6,12):
   y=int(ym[:4]);m=int(ym[4:]);q=y*12+m-1+h;fy=f'{q//12:04d}{q%12+1:02d}'
   x[f'fwd_{h}m']=(pr[fy]/pr[ym]-1)*100 if fy in pr else None
  x['baseline_turn']=m3 is not None and m1 is not None and m3<=0 and m1>=0
  rows.append(x)
 train=[x for x in rows if x['ym']<'201801'];hold=[x for x in rows if x['ym']>='201801']
 afford_cut=qmedian([x['afford_impulse'] for x in train]);breadth_cut=qmedian([x['breadth'] for x in train]);gap_cut=qmedian([x['songpa_gap'] for x in train])
 for x in rows:
  x['afford_ok']=x.get('afford_impulse') is not None and afford_cut is not None and x['afford_impulse']>=afford_cut
  x['breadth_ok']=x.get('breadth') is not None and breadth_cut is not None and x['breadth']>=breadth_cut
  x['enhanced_both']=x['baseline_turn'] and x['afford_ok'] and x['breadth_ok']
 def entry_report(pool):
  variants={'baseline':lambda x:x['baseline_turn'],
    'baseline_plus_affordability':lambda x:x['baseline_turn'] and x['afford_ok'],
    'baseline_plus_breadth':lambda x:x['baseline_turn'] and x['breadth_ok'],
    'baseline_plus_both':lambda x:x['enhanced_both']}
  return {name:{f'{h}m':stats([x for x in pool if fn(x)],f'fwd_{h}m') for h in (3,6,12)} for name,fn in variants.items()}
 def split_feature(pool,key,cut,target='fwd_6m'):
  hi=[x for x in pool if x.get(key) is not None and x[key]>=cut];lo=[x for x in pool if x.get(key) is not None and x[key]<cut]
  return {'cut_from_train':round(cut,3) if cut is not None else None,'high':stats(hi,target),'low':stats(lo,target)}
 # Local diagnostic: does positive Songpa-vs-Seoul relative strength precede better Songpa returns?
 local={}
 if gap_cut is not None:
  for h in (3,6,12):local[f'{h}m']=split_feature(hold,'songpa_gap',gap_cut,f'songpa_fwd_{h}m')
 result={'status':'research_only','no_future_leakage':True,'train':'<201801','holdout':'>=201801',
   'thresholds_selected_on_train_only':{'afford_impulse_median':round(afford_cut,3) if afford_cut is not None else None,
      'breadth_median':round(breadth_cut,3) if breadth_cut is not None else None,'songpa_gap_median':round(gap_cut,3) if gap_cut is not None else None},
   'entry_validation':{'train':entry_report(train),'holdout':entry_report(hold)},
   'holdout_feature_diagnostics':{
      'affordability_vs_seoul_6m':split_feature(hold,'afford_impulse',afford_cut),
      'breadth_vs_seoul_6m':split_feature(hold,'breadth',breadth_cut),
      'songpa_relative_strength_vs_songpa_forward':local},
   'guardrails':{'historical_breadth_is_watchlist_proxy':True,'standardized_dsr_is_benchmark_not_actual_limit':True,
      'do_not_modify_production_model_unless_holdout_improves_with_adequate_signal_count':True},
   'rows':rows,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 O.write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({'thresholds':result['thresholds_selected_on_train_only'],'holdout':result['entry_validation']['holdout'],'diagnostics':result['holdout_feature_diagnostics']},ensure_ascii=False))
if __name__=='__main__':main()
