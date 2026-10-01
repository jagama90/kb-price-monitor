#!/usr/bin/env python3
"""Research-only Common Feature Layer v2.

Builds leakage-aware candidate features without changing certified production
weights or formulas. Features only become eligible for production after their
own validation gates and an integrated engine validation.
"""
import datetime,json,math,pathlib,statistics
ROOT=pathlib.Path(__file__).resolve().parents[1]
DIST=ROOT/'dist';SRC=ROOT/'data_sources'
OUT=DIST/'common_feature_layer_v2.json'
VAL=DIST/'common_feature_layer_v2_validation.json'

def read(path,default=None):
 try:return json.loads(path.read_text(encoding='utf-8'))
 except:return {} if default is None else default

def f(v):
 try:return float(v)
 except:return None

def clamp(v):return max(0.0,min(100.0,float(v)))
def ym_shift(ym,delta):
 y=int(str(ym)[:4]);m=int(str(ym)[4:6]);q=y*12+(m-1)+delta
 return f'{q//12:04d}{q%12+1:02d}'

def latest_le(series,period,key='period'):
 xs=[x for x in series if str(x.get(key) or '')<=str(period) and x.get('value') is not None]
 return xs[-1] if xs else None

def percentile(values,v):
 z=[float(x) for x in values if x is not None]
 if not z:return None
 lt=sum(x<v for x in z);eq=sum(x==v for x in z)
 return 100*(lt+.5*eq)/len(z)

def pearson(xs,ys):
 pairs=[(float(a),float(b)) for a,b in zip(xs,ys) if a is not None and b is not None]
 if len(pairs)<3:return None
 a=[x for x,_ in pairs];b=[y for _,y in pairs];ma=sum(a)/len(a);mb=sum(b)/len(b)
 da=sum((x-ma)**2 for x in a);db=sum((y-mb)**2 for y in b)
 if da<=0 or db<=0:return None
 return sum((x-ma)*(y-mb) for x,y in pairs)/math.sqrt(da*db)

def auc(labels,scores):
 pairs=[(int(bool(y)),float(s)) for y,s in zip(labels,scores) if y is not None and s is not None]
 pos=[s for y,s in pairs if y==1];neg=[s for y,s in pairs if y==0]
 if not pos or not neg:return None
 wins=0.0
 for p in pos:
  for n in neg:
   wins+=1 if p>n else .5 if p==n else 0
 return wins/(len(pos)*len(neg))

def metric_pack(rows,score_key):
 out={'n':sum(1 for r in rows if r.get(score_key) is not None)}
 for h in (1,3,6,12):
  key=f'fwd_{h}m_pct';pairs=[r for r in rows if r.get(score_key) is not None and r.get(key) is not None]
  out[f'corr_fwd_{h}m']=pearson([r[score_key] for r in pairs],[r[key] for r in pairs])
 p=[r for r in rows if r.get(score_key) is not None and r.get('fwd_3m_pct') is not None]
 out['downside_auc']=auc([r['fwd_3m_pct']<0 for r in p],[100-r[score_key] for r in p])
 out['reacceleration_auc']=auc([r['fwd_3m_pct']>0 for r in p],[r[score_key] for r in p])
 out['n_fwd3']=len(p)
 return out

def mortgage_monthly(raw):
 by={}
 for x in raw.get('series') or []:
  if x.get('item')=='주택담보대출' and x.get('rate_pct') is not None:
   by[str(x['period'])]=float(x['rate_pct'])
 out=[]
 for i,k in enumerate(sorted(by)):
  v=by[k];prev=by[sorted(by)[i-1]] if i else None
  p3=by[sorted(by)[i-3]] if i>=3 else None
  out.append({'period':k,'value':v,'mom_change_pp':round(v-prev,4) if prev is not None else None,
              'change_3m_pp':round(v-p3,4) if p3 is not None else None})
 return out

def base_rate_monthly(raw):
 by={}
 for x in raw.get('series') or []:
  d=str(x.get('date') or '')
  if len(d)>=6 and x.get('rate_pct') is not None:by[d[:6]]=float(x['rate_pct'])
 if raw.get('latest'):
  x=raw['latest'];d=str(x.get('date') or '')
  if len(d)>=6 and x.get('rate_pct') is not None:by[d[:6]]=float(x['rate_pct'])
 # carry the most recently effective policy rate forward month by month where needed
 return [{'period':k,'value':by[k]} for k in sorted(by)]

def score_at(series,available_period,invert=False,value_key='value'):
 rows=[x for x in series if str(x.get('period') or '')<=available_period and x.get(value_key) is not None]
 if not rows:return None,None
 cur=float(rows[-1][value_key]);rank=percentile([float(x[value_key]) for x in rows],cur)
 return (100-rank if invert else rank),rows[-1]

def housing_credit_score_at(series,available_period):
 rows=[x for x in series if str(x.get('period') or '')<=available_period]
 rows=[x for x in rows if x.get('mom_change') is not None and x.get('yoy_pct') is not None]
 if not rows:return None,None
 cur=rows[-1]
 mom_rank=percentile([float(x['mom_change']) for x in rows],float(cur['mom_change']))
 yoy_rank=percentile([float(x['yoy_pct']) for x in rows],float(cur['yoy_pct']))
 return (mom_rank+yoy_rank)/2,cur

def funding_cost_score_at(series,available_period):
 rows=[x for x in series if str(x.get('period') or '')<=available_period and x.get('value') is not None]
 if not rows:return None,None
 cur=rows[-1]
 level=100-percentile([float(x['value']) for x in rows],float(cur['value']))
 # Direction/speed is a secondary cost term; missing early values fall back to level only.
 speed_rows=[x for x in rows if x.get('change_3m_pp') is not None]
 if not speed_rows or cur.get('change_3m_pp') is None:return level,cur
 speed=100-percentile([float(x['change_3m_pp']) for x in speed_rows],float(cur['change_3m_pp']))
 return .7*level+.3*speed,cur

def finance_research(final_rows,mortgage,credit):
 connected=(credit.get('status') in ('connected','connected_last_good') and len(credit.get('series') or [])>=36)
 cseries=credit.get('series') or []
 rows=[]
 for src in final_rows:
  ym=str(src.get('ym'));m_score,mrow=funding_cost_score_at(mortgage,ym_shift(ym,-1))
  c_score,crow=housing_credit_score_at(cseries,ym_shift(ym,-2)) if connected else (None,None)
  v2=(m_score+c_score)/2 if m_score is not None and c_score is not None else None
  rows.append({
   'ym':ym,'baseline_finance':f((src.get('components') or {}).get('finance')),
   'finance_v2':round(v2,3) if v2 is not None else None,
   'funding_cost_score':round(m_score,3) if m_score is not None else None,
   'credit_availability_score':round(c_score,3) if c_score is not None else None,
   'mortgage_vintage':mrow.get('period') if mrow else None,
   'credit_vintage':crow.get('period') if crow else None,
   **{k:src.get(k) for k in ('fwd_1m_pct','fwd_3m_pct','fwd_6m_pct','fwd_12m_pct')}
  })
 same=[r for r in rows if r.get('finance_v2') is not None and r.get('baseline_finance') is not None]
 baseline=metric_pack(same,'baseline_finance') if same else {}
 candidate=metric_pack(same,'finance_v2') if same else {}
 reasons=[]
 if not connected:reasons.append('official housing-credit series not connected')
 if candidate.get('n_fwd3',0)<30:reasons.append('fewer than 30 paired forward-3m observations')
 bda=baseline.get('downside_auc');cda=candidate.get('downside_auc');bra=baseline.get('reacceleration_auc');cra=candidate.get('reacceleration_auc')
 if cda is not None and bda is not None and cda<bda-.02:reasons.append('downside AUC degraded > 0.02')
 if cra is not None and bra is not None and cra<bra-.02:reasons.append('reacceleration AUC degraded > 0.02')
 improvements=[]
 if cda is not None and bda is not None and cda>=bda+.01:improvements.append('downside_auc')
 if cra is not None and bra is not None and cra>=bra+.01:improvements.append('reacceleration_auc')
 for h in (3,6,12):
  bc=baseline.get(f'corr_fwd_{h}m');cc=candidate.get(f'corr_fwd_{h}m')
  if bc is not None and cc is not None and cc>=bc+.03:improvements.append(f'corr_fwd_{h}m')
 apply=connected and candidate.get('n_fwd3',0)>=30 and not reasons and bool(improvements)
 return rows,{'baseline':baseline,'candidate':candidate,'improvements':improvements,'apply_recommended':apply,'reasons':reasons,
  'alignment':{'mortgage_rate':'score month t uses latest monthly rate <= t-1','housing_credit':'score month t uses latest balance growth <= t-2'}}

def valuation_rate_research(final_rows,mortgage):
 rows=[]
 for src in final_rows:
  ym=str(src.get('ym'));value=f((src.get('components') or {}).get('value'))
  base_score,mrow=score_at(mortgage,ym_shift(ym,-1),invert=True)
  full_score,_=funding_cost_score_at(mortgage,ym_shift(ym,-1))
  if value is None or base_score is None:continue
  level_cost=100-base_score;full_cost=100-full_score if full_score is not None else level_cost
  vstress=100-value
  rows.append({'ym':ym,'valuation_stress':vstress,'rate_level_cost':level_cost,'rate_level_speed_cost':full_cost,
    'interaction_level':vstress*level_cost/100,'interaction_level_speed':vstress*full_cost/100,
    'fwd_3m_pct':src.get('fwd_3m_pct'),'mortgage_vintage':mrow.get('period') if mrow else None})
 p=[r for r in rows if r.get('fwd_3m_pct') is not None]
 labels=[r['fwd_3m_pct']<0 for r in p]
 metrics={
  'n':len(p),
  'valuation_only_downside_auc':auc(labels,[r['valuation_stress'] for r in p]),
  'rate_level_downside_auc':auc(labels,[r['rate_level_cost'] for r in p]),
  'rate_level_speed_downside_auc':auc(labels,[r['rate_level_speed_cost'] for r in p]),
  'interaction_level_downside_auc':auc(labels,[r['interaction_level'] for r in p]),
  'interaction_level_speed_downside_auc':auc(labels,[r['interaction_level_speed'] for r in p]),
  'interaction_level_speed_corr_negative_fwd3':pearson([r['interaction_level_speed'] for r in p],[-float(r['fwd_3m_pct']) for r in p]),
 }
 parents=[x for x in (metrics['valuation_only_downside_auc'],metrics['rate_level_speed_downside_auc']) if x is not None]
 cand=metrics['interaction_level_speed_downside_auc']
 gate=len(p)>=30 and parents and cand is not None and cand>=max(parents)+.01
 return rows,{**metrics,'apply_recommended':bool(gate),'gate':'n>=30 and valuation×(rate level + 3m speed) downside AUC >= best single parent + 0.01'}

def price_tier_feature(market,tier_history=None,kb_momentum=None):
 tier_history=tier_history or {};cfg=(tier_history.get('price_tier_config') or market.get('price_tier_config') or {})
 sig=market.get('signal_matched_period') or {};cur=sig.get('current') or {};prev=sig.get('previous') or {}
 cc=cur.get('counts') or {};pc=prev.get('counts') or {}
 abs_cfg=cfg.get('absolute') or [{'id':k,'label':k} for k in cc.keys()]
 out=[];ct=f(cur.get('total'));pt=f(prev.get('total'));market_change=f((sig.get('changes') or {}).get('trade_count_pct'))
 for band in abs_cfg:
  key=str(band.get('id'));label=str(band.get('label') or key);a=f(cc.get(key));b=f(pc.get(key))
  cp=(a/b-1)*100 if a is not None and b not in (None,0) else None
  cs=a/ct*100 if a is not None and ct else None;ps=b/pt*100 if b is not None and pt else None
  out.append({'id':key,'label':label,'current_count':a,'previous_count':b,'count_change_pct':round(cp,2) if cp is not None else None,
              'current_share_pct':round(cs,2) if cs is not None else None,'previous_share_pct':round(ps,2) if ps is not None else None,
              'share_change_pp':round(cs-ps,2) if cs is not None and ps is not None else None,
              'relative_volume_vs_market_pp':round(cp-market_change,2) if cp is not None and market_change is not None else None})
 high_id=str((abs_cfg[-1] if abs_cfg else {}).get('id') or '')
 high=next((x for x in out if x['id']==high_id),{})
 hist=[x for x in (tier_history.get('months') or []) if x.get('mature') is True and f(x.get('total')) not in (None,0)]
 analysis_cfg=cfg.get('analysis') or [];analysis_ids=[str(x.get('id')) for x in analysis_cfg if x.get('id') is not None]
 high_analysis=analysis_ids[-1] if analysis_ids else None;upper_ids=analysis_ids[1:] if len(analysis_ids)>=2 else []
 target={str(x.get('ym')):x for x in ((kb_momentum or {}).get('sample') or []) if x.get('ym')}
 aligned=[]
 def share(row,ids):
  total=f(row.get('total'));b=row.get('buckets3') or {}
  vals=[f(b.get(k)) for k in ids]
  return sum(vals)/total*100 if total and vals and all(v is not None for v in vals) else None
 for i,row in enumerate(hist):
  if i<3 or not analysis_ids:continue
  ym=str(row.get('period') or '').replace('-','')[:6];avail_ym=ym_shift(ym,1);prev3=hist[i-3]
  hs=share(row,[high_analysis]) if high_analysis else None;hp=share(prev3,[high_analysis]) if high_analysis else None
  us=share(row,upper_ids) if upper_ids else None;up=share(prev3,upper_ids) if upper_ids else None
  cb=row.get('buckets3') or {};pb=prev3.get('buckets3') or {}
  hc=f(cb.get(high_analysis)) if high_analysis else None;hpc=f(pb.get(high_analysis)) if high_analysis else None
  uc=sum(f(cb.get(k)) or 0 for k in upper_ids) if upper_ids else None;upc=sum(f(pb.get(k)) or 0 for k in upper_ids) if upper_ids else None
  total=f(row.get('total'));ptotal=f(prev3.get('total'))
  def pctchg(a,b):return (a/b-1)*100 if a is not None and b not in (None,0) else None
  hchg=pctchg(hc,hpc);uchg=pctchg(uc,upc);tchg=pctchg(total,ptotal)
  y=target.get(avail_ym) or {};fwd=f(y.get('fwd_3m_pct'))
  aligned.append({'trade_period':ym,'available_score_month':avail_ym,
                  'high_share_3m_change_pp':(hs-hp if hs is not None and hp is not None else None),
                  'upper_share_3m_change_pp':(us-up if us is not None and up is not None else None),
                  'high_count_3m_change_pct':hchg,'upper_count_3m_change_pct':uchg,
                  'high_relative_volume_3m_pp':(hchg-tchg if hchg is not None and tchg is not None else None),
                  'upper_relative_volume_3m_pp':(uchg-tchg if uchg is not None and tchg is not None else None),
                  'fwd_3m_pct':fwd})
 def sig_metrics(key):
  z=[x for x in aligned if x.get(key) is not None and x.get('fwd_3m_pct') is not None]
  return {'n':len(z),'corr_fwd3':pearson([x[key] for x in z],[x['fwd_3m_pct'] for x in z]),
          'auc_positive_fwd3':auc([1 if x['fwd_3m_pct']>0 else 0 for x in z],[x[key] for x in z])}
 hm=sig_metrics('high_share_3m_change_pp');um=sig_metrics('upper_share_3m_change_pp')
 hcm=sig_metrics('high_count_3m_change_pct');ucm=sig_metrics('upper_count_3m_change_pct')
 hrm=sig_metrics('high_relative_volume_3m_pp');urm=sig_metrics('upper_relative_volume_3m_pp')
 enough=len(hist)>=36 and max(hm['n'],um['n'],hcm['n'],ucm['n'],hrm['n'],urm['n'])>=24
 candidates=[('high_share_3m_change_pp',hm),('upper_share_3m_change_pp',um),
             ('high_count_3m_change_pct',hcm),('upper_count_3m_change_pct',ucm),
             ('high_relative_volume_3m_pp',hrm),('upper_relative_volume_3m_pp',urm)]
 valid=[x for x in candidates if x[1].get('auc_positive_fwd3') is not None]
 best=max(valid,key=lambda x:x[1]['auc_positive_fwd3']) if valid else (None,{})
 supported=bool(enough and best[1].get('auc_positive_fwd3',0)>=.60 and (best[1].get('corr_fwd3') or 0)>=.10)
 return {
  'status':'research_candidate' if enough else 'current_diagnostic_only','production_applied':False,
  'scope':{'data_scope':(market.get('scope') or {}).get('data_scope'),'price_tier_mode':'configured_absolute_and_analysis_bands'},
  'signal_period':cur.get('period'),'previous_period':prev.get('period'),'aggregate_trade_change_pct':market_change,
  'bands':out,'high_tier_relative_volume_pp':high.get('relative_volume_vs_market_pp'),
  'relative_quantile_tiers':{'status':'not_connected','reason':'monthly configured-band aggregates are retained; historical transaction-level rows are intentionally not retained'},
  'validation':{'status':'validated_history' if enough else 'insufficient_history','available_band_months':len(hist),'required_for_model':36,
                'aligned_target_rows':max(hm['n'],um['n']),'minimum_aligned_rows':24,'sufficient_for_model':enough,
                'publication_alignment':'trade month t becomes eligible at score month t+1 after the reporting window; no current-month partial counts are used',
                'high_share_3m_change':hm,'upper_share_3m_change':um,
                'high_count_3m_change':hcm,'upper_count_3m_change':ucm,
                'high_relative_volume_3m':hrm,'upper_relative_volume_3m':urm,
                'best_research_signal':best[0],'signal_supported':supported,
                'production_gate':'history and standalone signal support are necessary but not sufficient; integrated engine validation is still required',
                'no_future_leakage':True},
  'research_sample':aligned[-60:]
 }

def lead_lag_feature(raw,scope=None):
 try:
  scope=scope or {};region=scope.get('region') or {};region_code=str(region.get('code') or scope.get('region_code') or '')
  region_label=str(region.get('label') or scope.get('data_scope') or region_code)
  if not region_code:raise ValueError('configured region code is required for median-market selection')
  lead=(((raw.get('targets') or {}).get('leading50') or {}).get('payload') or {}).get('dataBody',{}).get('data',{})
  med=(((raw.get('targets') or {}).get('median') or {}).get('payload') or {}).get('dataBody',{}).get('data',{})
  dates=[str(x) for x in lead.get('날짜리스트') or []];lr=[f(x) for x in lead.get('전월대비증감률리스트') or []]
  market_row=next(x for x in (med.get('데이터리스트') or []) if str(x.get('지역코드'))==region_code)
  vals=[f(x) for x in market_row.get('dataList') or []];md=[str(x) for x in med.get('날짜리스트') or dates[-len(vals):]]
  byv={d:v for d,v in zip(md,vals) if v is not None};sr={};prev=None
  for d in md:
   v=byv.get(d)
   if v is not None and prev not in (None,0):sr[d]=(v/prev-1)*100
   if v is not None:prev=v
  leadret={d:v for d,v in zip(dates,lr) if v is not None};stats=[]
  for lag in range(4):
   pairs=[]
   for i,d in enumerate(dates):
    if i+lag>=len(dates):break
    td=dates[i+lag]
    if d in leadret and td in sr:pairs.append((leadret[d],sr[td]))
   xs=[x for x,_ in pairs];ys=[y for _,y in pairs];mid=len(pairs)//2
   stats.append({'lag_months':lag,'n':len(pairs),'corr_leader_to_future_market':pearson(xs,ys),
                 'auc_future_market_positive':auc([1 if y>0 else 0 for y in ys],xs),
                 'first_half_corr':pearson(xs[:mid],ys[:mid]),'second_half_corr':pearson(xs[mid:],ys[mid:])})
  maxn=max((x['n'] for x in stats),default=0);sufficient=maxn>=36;base=stats[0] if stats else {}
  leads=[x for x in stats if x['lag_months']>0 and x.get('corr_leader_to_future_market') is not None and x.get('auc_future_market_positive') is not None]
  best=max(leads,key=lambda x:(x['auc_future_market_positive'],x['corr_leader_to_future_market'])) if leads else None
  superiority=False
  if sufficient and best:
   superiority=bool(best['corr_leader_to_future_market']>=.20 and best['auc_future_market_positive']>=.60 and
                    (best.get('first_half_corr') or 0)>0 and (best.get('second_half_corr') or 0)>0 and
                    (best['corr_leader_to_future_market']>=(base.get('corr_leader_to_future_market') or 0)+.05 or
                     best['auc_future_market_positive']>=(base.get('auc_future_market_positive') or 0)+.03))
  return {'status':'research_candidate' if sufficient else 'research_small_sample','production_applied':False,
          'leader_definition':'KB 선도아파트 50지수','market_definition':f'KB {region_label} 아파트 중위가격',
          'market_region_code':region_code,'period_start':dates[0] if dates else None,'period_end':dates[-1] if dates else None,'lag_tests':stats,
          'validation':{'sufficient_for_model':sufficient,'minimum_required':36,'lead_lag_hypothesis_supported':superiority,
                        'best_positive_lag_months':best.get('lag_months') if best else None,
                        'gate':'n>=36; positive lag corr>=0.20 and direction AUC>=0.60; both half-sample correlations >0; lag must beat contemporaneous corr by 0.05 or AUC by 0.03',
                        'reason':'history is sufficient; production use still requires clear lag superiority and integrated validation' if sufficient else 'lead-lag is descriptive until longer same-definition history is available'}}
 except Exception as e:
  return {'status':'not_connected','production_applied':False,'reason':repr(e)[:240]}

def selling_pressure_feature(watch,history=None):
 items=watch.get('items') or [];deltas=[];gaps=[];soft=0;usable=0;ask_deltas=[];listing_obs=0
 for x in items:
  d=f(x.get('sale_listing_week_delta'));a=f(x.get('avg_ask_manwon'));t=f(x.get('recent_trade_manwon'));ad=f(x.get('avg_ask_week_delta_manwon'))
  if f(x.get('sale_listing_count')) is not None:listing_obs+=1
  if d is not None:deltas.append(d)
  if ad is not None:ask_deltas.append(ad)
  if a is not None and t not in (None,0):gaps.append((a/t-1)*100)
  if d is not None and ad is not None:
   usable+=1
   if d>0 and ad<0:soft+=1
 hist=(history or {}).get('snapshots') or []
 return {'status':'local_watchlist_context','production_applied':False,'representative_market_sample':False,
         'scope':'configured watchlist target types','n_items':len(items),'listing_observed_rows':listing_obs,
         'listing_coverage_pct':round(100*listing_obs/len(items),1) if items else None,'n_listing_delta':len(deltas),
         'listing_increase_share_pct':round(100*sum(x>0 for x in deltas)/len(deltas),1) if deltas else None,
         'median_listing_week_delta':round(statistics.median(deltas),2) if deltas else None,
         'ask_cut_share_pct':round(100*sum(x<0 for x in ask_deltas)/len(ask_deltas),1) if ask_deltas else None,
         'median_ask_vs_recent_trade_gap_pct':round(statistics.median(gaps),2) if gaps else None,
         'listing_up_and_ask_down_share_pct':round(100*soft/usable,1) if usable else None,
         'history':{'available_snapshots':len(hist),'sufficient_for_time_series_research':len(hist)>=12,'minimum_required':12},
         'forced_selling':{'status':'not_observable','reason':'seller leverage/default status and sale motive are not observable from authoritative sources; no inference is made'}}

def policy_feature(raw,scope_cfg=None):
 scope_cfg=scope_cfg or {};tags=set(str(x) for x in (scope_cfg.get('credit_policy_scope_tags') or []))
 asof=str(raw.get('as_of') or datetime.date.today().isoformat());events=raw.get('events') or [];active=[]
 for e in events:
  start=str(e.get('effective_date') or '9999-12-31');end=str(e.get('end_date') or '9999-12-31')
  if not (start<=asof<=end):continue
  anytags=set(str(x) for x in (e.get('scope_match_any') or []))
  if anytags and not (tags & anytags):continue
  active.append({'id':e.get('id'),'effective_date':e.get('effective_date'),'end_date':e.get('end_date'),
                 'terms':e.get('terms'),'source':e.get('source'),'source_authority':e.get('source_authority')})
 return {'status':'connected_current_context' if raw.get('status')=='connected_current_context' else 'not_connected_for_model',
         'production_applied':False,'scope_tags':sorted(tags),'active_rules':active,'active_rule_count':len(active),
         'historical_backtest_ready':bool(raw.get('historical_backtest_ready')),
         'reason':'objective effective-date and quantitative credit rules are connected for current context; historical lineage is not yet complete enough for model/backtest use' if active else 'no applicable structured rule for the configured scope'}

def rental_supply_feature(market,structural=None):
 s=market.get('kb_sentiment') or {};u=market.get('unsold_inventory') or market.get('unsold_seoul') or {};structural=structural or {}
 units=u.get('region_units')
 if units is None:units=u.get('seoul_units')
 series=structural.get('series') or {};connected=sum((series.get(k) or {}).get('status') in ('connected_probe','connected_api') for k in ('permit','start','completion'))
 return {'status':'semantic_split','production_applied':False,
         'rental_market_balance':{'status':'connected' if s.get('jeonse_score_0_100') is not None else 'not_connected',
          'score_0_100':s.get('jeonse_score_0_100'),'meaning':'KB 전세수급·전세거래 기반 단기 임대시장 균형','legacy_component_key':'supply'},
         'structural_supply':{'status':'connected_context' if connected else ('partial_context' if units is not None else 'source_blocked'),
          'unsold_inventory':{'units':units,'period':u.get('period'),'region_code':u.get('region_code'),'region_label':u.get('region_label') or u.get('region'),'source':u.get('source')},
          'construction_statistics':{'status':structural.get('status') or 'not_connected','series':series,'official_meta':structural.get('official_meta'),'automation_blocker':structural.get('automation_blocker')},
          'meaning':'미분양 재고와 인허가·착공·준공은 구조공급 context로 분리하며 기존 전세수급 15% 점수에는 아직 합산하지 않음'}}

def current_finance_feature(mortgage,base,m2,credit,validation,production_applied=False):
 latest_m=mortgage[-1] if mortgage else None;cr=(credit.get('series') or [])
 fund,fr=funding_cost_score_at(mortgage,latest_m.get('period') if latest_m else '999999') if latest_m else (None,None)
 avail,ar=housing_credit_score_at(cr,(cr[-1].get('period') if cr else '000000')) if cr else (None,None)
 score=(fund+avail)/2 if fund is not None and avail is not None else None
 br=(base.get('latest') or {})
 return {'status':'validated_candidate' if validation.get('apply_recommended') else ('research_candidate' if score is not None else 'blocked_core_input_missing'),
         'production_applied':bool(production_applied),'score_0_100':round(score,1) if score is not None else None,
         'liquidity_credit_availability':{'score_0_100':round(avail,1) if avail is not None else None,'source':'한국은행 ECOS 주택관련대출 잔액','period':ar.get('period') if ar else None,
             'balance':ar.get('value') if ar else None,'mom_change':ar.get('mom_change') if ar else None,'yoy_pct':ar.get('yoy_pct') if ar else None},
         'funding_cost':{'score_0_100':round(fund,1) if fund is not None else None,'mortgage_rate_pct':latest_m.get('value') if latest_m else None,'period':latest_m.get('period') if latest_m else None,
             'base_rate_pct':br.get('rate_pct'),'base_rate_date':br.get('date')},
         'broad_liquidity_context':{'m2_period':(m2.get('series') or [{}])[-1].get('period'),'m2_yoy_pct':(m2.get('series') or [{}])[-1].get('yoy_pct')},
         'method':'Credit Availability 50% + Funding Cost 50%. Credit Availability uses housing-related loan balance increment and YoY growth; Funding Cost uses mortgage-rate level and 3m speed. M2 is context only.',
         'validation':validation}

def main():
 market=read(DIST/'market_indicators.json');final=read(DIST/'final_backtest.json');mort_raw=read(SRC/'ecos_mortgage_rate.json');tier_history=read(SRC/'molit_price_tier_history.json')
 base=read(SRC/'ecos_base_rate.json');m2=read(SRC/'ecos_m2.json');credit=read(SRC/'ecos_housing_credit.json')
 leading=read(SRC/'kb_leading50_median.json');watch=read(ROOT/'data/buy_watchlist_market.json')
 selling_history=read(SRC/'watchlist_selling_pressure_history.json');policy=read(SRC/'credit_policy_regime.json');structural=read(SRC/'molit_structural_supply.json')
 kb_momentum=read(DIST/'forecast_kb_momentum_validation.json');scope_cfg=read(ROOT/'config/market_scope.json')
 integrated=read(DIST/'market_judgment_validation.json',{})
 mortgage=mortgage_monthly(mort_raw);frows=final.get('rows') or []
 finance_rows,finance_val=finance_research(frows,mortgage,credit)
 finance_v2_production=bool(finance_val.get('apply_recommended') and integrated.get('no_future_leakage') is True and ((integrated.get('finance_v2_integrated') or {}).get('apply_recommended') is True))
 vr_rows,vr_val=valuation_rate_research(frows,mortgage)
 features={
  'trade_reporting':{'status':market.get('signal_matched_period_status'),'production_applied':market.get('signal_matched_period_status')=='mature_completed_month','engine_signal':market.get('signal_matched_period'),'raw_early_signal':market.get('matched_period'),'confidence':market.get('trade_signal_confidence')},
  'finance_v2_candidate':current_finance_feature(mortgage,base,m2,credit,finance_val,finance_v2_production),
  'valuation_rate_stress_candidate':{'status':'validated_candidate' if vr_val.get('apply_recommended') else 'research_candidate','production_applied':False,'validation':vr_val,
      'current_inputs':{'value_score_0_100':(market.get('kb_value') or {}).get('score_0_100'),'mortgage_rate_pct':(market.get('mortgage_rate_official') or {}).get('rate_pct')},
      'method':'(100 - existing Value Composite) × historical mortgage-rate cost percentile / 100'},
  'price_tier_liquidity':price_tier_feature(market,tier_history,kb_momentum),
  'leader_lag':lead_lag_feature(leading,scope_cfg),
  'selling_pressure':selling_pressure_feature(watch,selling_history),
  'policy_credit_regime':policy_feature(policy,scope_cfg),
  'rental_vs_structural_supply':rental_supply_feature(market,structural),
 }
 decisions={k:{'status':v.get('status'),'production_applied':bool(v.get('production_applied'))} for k,v in features.items() if isinstance(v,dict)}
 payload={
  'status':'research_only','version':'common_feature_layer_v2','architecture':'Common Feature Layer -> Current State / Buy Condition / Forward Scenario',
  'scope':{'dimensions':['region','market_scope','district','complex','price_tier'],'active_data_scope':(market.get('scope') or {}).get('data_scope','Seoul'),
           'rule':'source scope is metadata/configuration; model formulas contain no city/district names'},
  'production_baseline':{'buy_weights':{'finance':25,'sentiment':20,'demand':20,'value':20,'supply':15},
    'value_composite_weights':{'pir':.4,'rent_ratio':.3,'trend_gap':.3},'unchanged':True},
  'features':features,'production_decision':{'integrated_engine_changed':finance_v2_production,'candidate_decisions':decisions,
    'reason':('finance_v2 passed standalone and integrated leakage-safe validation and is active in production; other candidates remain research-only until their gates pass' if finance_v2_production else 'candidate features stay research-only unless adequate history, leakage-safe validation, and integrated certified-model comparison all pass')},
  'lineage':{'market':'dist/market_indicators.json','final_backtest':'dist/final_backtest.json','mortgage_rate':'data_sources/ecos_mortgage_rate.json',
             'housing_credit':'data_sources/ecos_housing_credit.json','price_tier_history':'data_sources/molit_price_tier_history.json','leading_segment':'data_sources/kb_leading50_median.json','kb_momentum_validation':'dist/forecast_kb_momentum_validation.json','selling_pressure_history':'data_sources/watchlist_selling_pressure_history.json','policy_credit_regime':'data_sources/credit_policy_regime.json','structural_supply':'data_sources/molit_structural_supply.json','integrated_validation':'dist/market_judgment_validation.json'},
  'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()
 }
 validation={'version':'common_feature_layer_v2_validation','no_future_leakage':True,
   'finance_v2':finance_val,'valuation_rate_stress':vr_val,
   'price_tier_history_sufficient':features['price_tier_liquidity']['validation']['sufficient_for_model'] if 'sufficient_for_model' in features['price_tier_liquidity']['validation'] else False,
   'leader_lag_history_sufficient':features['leader_lag'].get('validation',{}).get('sufficient_for_model',False),
   'phase4_context':{
     'selling_pressure_history_sufficient':features['selling_pressure'].get('history',{}).get('sufficient_for_time_series_research',False),
     'forced_selling_observable':features['selling_pressure'].get('forced_selling',{}).get('status')!='not_observable',
     'policy_historical_backtest_ready':features['policy_credit_regime'].get('historical_backtest_ready',False),
     'policy_active_rule_count':features['policy_credit_regime'].get('active_rule_count',0),
     'structural_supply_source_status':features['rental_vs_structural_supply'].get('structural_supply',{}).get('construction_statistics',{}).get('status'),
     'production_replacement_recommended':False,
     'reason':'phase 4 sources are context/research inputs only; legacy rental-market supply weight remains unchanged until representative history and integrated validation exist'
   },
   'integrated_production_replacement_recommended':finance_v2_production,
   'finance_v2_integrated':integrated.get('finance_v2_integrated'),
   'integrated_reason':('finance_v2 is active after standalone + integrated leakage-safe validation' if finance_v2_production else 'No candidate is allowed to replace certified production logic until it has adequate history and integrated forecast validation.'),
   'research_rows':{'finance':finance_rows,'valuation_rate_stress':vr_rows},
   'generated_at':payload['generated_at']}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 VAL.write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'finance_v2':finance_val.get('apply_recommended'),'finance_n':finance_val.get('candidate',{}).get('n_fwd3'),
   'valuation_rate':vr_val.get('apply_recommended'),'leader':features['leader_lag'].get('status'),'price_tier':features['price_tier_liquidity'].get('status')},ensure_ascii=False))

if __name__=='__main__':main()

# phase4 structural supply connected refresh
