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
 connected=(credit.get('status')=='connected' and len(credit.get('series') or [])>=36)
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

def price_tier_feature(market,tier_history=None):
 sig=market.get('signal_matched_period') or {};cur=sig.get('current') or {};prev=sig.get('previous') or {}
 cc=cur.get('counts') or {};pc=prev.get('counts') or {}
 keys=[('<=9eok','≤9억'),('9-15eok','9~15억'),('15-25eok','15~25억'),('25eok+','25억+')]
 out=[];ct=f(cur.get('total'));pt=f(prev.get('total'));market_change=f((sig.get('changes') or {}).get('trade_count_pct'))
 for key,label in keys:
  a=f(cc.get(key));b=f(pc.get(key))
  cp=(a/b-1)*100 if a is not None and b not in (None,0) else None
  cs=a/ct*100 if a is not None and ct else None;ps=b/pt*100 if b is not None and pt else None
  out.append({'id':key,'label':label,'current_count':a,'previous_count':b,'count_change_pct':round(cp,2) if cp is not None else None,
              'current_share_pct':round(cs,2) if cs is not None else None,'previous_share_pct':round(ps,2) if ps is not None else None,
              'share_change_pp':round(cs-ps,2) if cs is not None and ps is not None else None,
              'relative_volume_vs_market_pp':round(cp-market_change,2) if cp is not None and market_change is not None else None})
 high=next((x for x in out if x['id']=='25eok+'),{})
 return {
  'status':'current_diagnostic_only','production_applied':False,
  'scope':{'data_scope':(market.get('scope') or {}).get('data_scope','Seoul'),'price_tier_mode':'absolute_configured_bands'},
  'signal_period':cur.get('period'),'previous_period':prev.get('period'),'aggregate_trade_change_pct':market_change,
  'bands':out,'high_tier_relative_volume_pp':high.get('relative_volume_vs_market_pp'),
  'relative_quantile_tiers':{'status':'not_connected','reason':'long-enough transaction-level history for market-relative quantiles is not retained yet'},
  'validation':{'status':'insufficient_history','available_band_months':len(((tier_history or {}).get('months') or (market.get('price_bands') or {}).get('months') or [])),'required_for_model':36}
 }

def lead_lag_feature(raw):
 try:
  lead=(((raw.get('targets') or {}).get('leading50') or {}).get('payload') or {}).get('dataBody',{}).get('data',{})
  med=(((raw.get('targets') or {}).get('median') or {}).get('payload') or {}).get('dataBody',{}).get('data',{})
  dates=[str(x) for x in lead.get('날짜리스트') or []];lr=[f(x) for x in lead.get('전월대비증감률리스트') or []]
  seoul=next(x for x in (med.get('데이터리스트') or []) if str(x.get('지역코드'))=='1100000000' or str(x.get('지역명'))=='서울')
  vals=[f(x) for x in seoul.get('dataList') or []];md=[str(x) for x in med.get('날짜리스트') or dates[-len(vals):]]
  byv={d:v for d,v in zip(md,vals) if v is not None};sr={}
  prev=None
  for d in md:
   v=byv.get(d)
   if v is not None and prev not in (None,0):sr[d]=(v/prev-1)*100
   if v is not None:prev=v
  leadret={d:v for d,v in zip(dates,lr) if v is not None}
  stats=[]
  for lag in range(4):
   xs=[];ys=[]
   for i,d in enumerate(dates):
    if i+lag>=len(dates):break
    td=dates[i+lag]
    if d in leadret and td in sr:xs.append(leadret[d]);ys.append(sr[td])
   stats.append({'lag_months':lag,'n':len(xs),'corr_leader_to_future_market':pearson(xs,ys)})
  maxn=max((x['n'] for x in stats),default=0)
  return {'status':'research_small_sample' if maxn<36 else 'research_candidate','production_applied':False,
          'leader_definition':'KB 선도아파트 50지수','market_definition':'KB 서울 아파트 중위가격',
          'period_start':dates[0] if dates else None,'period_end':dates[-1] if dates else None,'lag_tests':stats,
          'validation':{'sufficient_for_model':maxn>=36,'minimum_required':36,'reason':'lead-lag is descriptive until longer same-definition history is available'}}
 except Exception as e:
  return {'status':'not_connected','production_applied':False,'reason':repr(e)[:240]}

def selling_pressure_feature(watch):
 items=watch.get('items') or [];deltas=[];gaps=[];soft=0;usable=0
 for x in items:
  d=f(x.get('sale_listing_week_delta'));a=f(x.get('avg_ask_manwon'));t=f(x.get('recent_trade_manwon'));ad=f(x.get('avg_ask_week_delta_manwon'))
  if d is not None:deltas.append(d)
  if a is not None and t not in (None,0):gaps.append((a/t-1)*100)
  if d is not None and ad is not None:
   usable+=1
   if d>0 and ad<0:soft+=1
 return {'status':'local_watchlist_context','production_applied':False,'representative_market_sample':False,
         'scope':'configured watchlist complexes/areas','n_items':len(items),'n_listing_delta':len(deltas),
         'listing_increase_share_pct':round(100*sum(x>0 for x in deltas)/len(deltas),1) if deltas else None,
         'median_listing_week_delta':round(statistics.median(deltas),2) if deltas else None,
         'median_ask_vs_recent_trade_gap_pct':round(statistics.median(gaps),2) if gaps else None,
         'listing_up_and_ask_down_share_pct':round(100*soft/usable,1) if usable else None,
         'forced_selling':{'status':'not_connected','reason':'leverage/forced-sale identity is not observable from current authoritative sources; no inference is made'}}

def policy_feature(raw):
 events=raw.get('events') or []
 effective=sum(bool(x.get('effective_date')) for x in events);quant=sum(bool(x.get('quantitative_terms')) for x in events)
 return {'status':'not_connected_for_model','production_applied':False,'event_count':len(events),
         'announcement_date_coverage':sum(bool(x.get('date') or x.get('announcement_date')) for x in events),
         'effective_date_coverage':effective,'quantitative_terms_coverage':quant,
         'reason':'historical file has announcement events but lacks complete effective-date and quantitative DSR/LTV/loan-limit lineage; narrative intensity is not used as a model input'}

def rental_supply_feature(market):
 s=market.get('kb_sentiment') or {};u=market.get('unsold_seoul') or {}
 return {'status':'semantic_split','production_applied':False,'rental_market_balance':{'status':'connected' if s.get('jeonse_score_0_100') is not None else 'not_connected',
          'score_0_100':s.get('jeonse_score_0_100'),'meaning':'KB 전세수급·전세거래 기반 단기 임대시장 균형','legacy_component_key':'supply'},
         'structural_supply':{'status':'partial_context','unsold_units':u.get('seoul_units'),'unsold_period':u.get('period'),
          'completion_inventory_series_status':'not_connected','meaning':'미분양은 보조 재고지표이며 신규 입주물량과 동일하게 취급하지 않음'}}

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
 leading=read(SRC/'kb_leading50_median.json');watch=read(ROOT/'data/buy_watchlist_market.json');policy=read(SRC/'housing_policy_events.json')
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
  'price_tier_liquidity':price_tier_feature(market,tier_history),
  'leader_lag':lead_lag_feature(leading),
  'selling_pressure':selling_pressure_feature(watch),
  'policy_credit_regime':policy_feature(policy),
  'rental_vs_structural_supply':rental_supply_feature(market),
 }
 decisions={k:{'status':v.get('status'),'production_applied':bool(v.get('production_applied'))} for k,v in features.items() if isinstance(v,dict)}
 payload={
  'status':'research_only','version':'common_feature_layer_v2','architecture':'Common Feature Layer -> Current State / Buy Condition / Forward Scenario',
  'scope':{'dimensions':['region','market_scope','district','complex','price_tier'],'active_data_scope':(market.get('scope') or {}).get('data_scope','Seoul'),
           'rule':'source scope is metadata/configuration; model formulas contain no city/district names'},
  'production_baseline':{'buy_weights':{'finance':25,'sentiment':20,'demand':20,'value':20,'supply':15},
    'value_composite_weights':{'pir':.4,'rent_ratio':.3,'trend_gap':.3},'unchanged':True},
  'features':features,'production_decision':{'integrated_engine_changed':False,'candidate_decisions':decisions,
    'reason':'candidate features stay research-only unless adequate history, leakage-safe validation, and integrated certified-model comparison all pass'},
  'lineage':{'market':'dist/market_indicators.json','final_backtest':'dist/final_backtest.json','mortgage_rate':'data_sources/ecos_mortgage_rate.json',
             'housing_credit':'data_sources/ecos_housing_credit.json','leading_segment':'data_sources/kb_leading50_median.json','policy':'data_sources/housing_policy_events.json','integrated_validation':'dist/market_judgment_validation.json'},
  'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()
 }
 validation={'version':'common_feature_layer_v2_validation','no_future_leakage':True,
   'finance_v2':finance_val,'valuation_rate_stress':vr_val,
   'price_tier_history_sufficient':features['price_tier_liquidity']['validation']['sufficient_for_model'] if 'sufficient_for_model' in features['price_tier_liquidity']['validation'] else False,
   'leader_lag_history_sufficient':features['leader_lag'].get('validation',{}).get('sufficient_for_model',False),
   'integrated_production_replacement_recommended':False,
   'integrated_reason':'No candidate is allowed to replace certified production logic until it has adequate history and integrated forecast validation.',
   'research_rows':{'finance':finance_rows,'valuation_rate_stress':vr_rows},
   'generated_at':payload['generated_at']}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 VAL.write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'finance_v2':finance_val.get('apply_recommended'),'finance_n':finance_val.get('candidate',{}).get('n_fwd3'),
   'valuation_rate':vr_val.get('apply_recommended'),'leader':features['leader_lag'].get('status'),'price_tier':features['price_tier_liquidity'].get('status')},ensure_ascii=False))

if __name__=='__main__':main()
