#!/usr/bin/env python3
"""Unified market judgment engine.

One common live feature snapshot feeds three heads:
  1) Current State: where the market is now
  2) Buy Condition: how favorable the buying environment is
  3) Forward Scenario: where the regime may move next

Historical turning research remains the research/backtest substrate. The live
heads never mix different current snapshots.
"""
import json, pathlib, datetime, math

WEIGHTS={'finance':25,'sentiment':20,'demand':20,'value':20,'supply':15}
STAGE_LABELS=['하락','둔화','바닥','상승·보합','가속']
RISK_LABELS=[
  ('상승 우위','0~19%','하방 위험 낮음','very_low'),
  ('재상승 가능성 확대','20~29%','재상승 여지 확대','low'),
  ('혼조·방향 탐색','30~34%','방향성 확인 필요','mixed'),
  ('쉬어가기·하방 경계','35~44%','하방 위험 주의','watch'),
  ('조정 위험 확대','45~54%','조정 위험 우세','high'),
  ('하락 우위','55~100%','하락 시나리오 우세','very_high'),
]
RISK_LOWER=[0,20,30,35,45,55]
EASING_HYSTERESIS_PP=2.0

def clamp(x): return max(0.0,min(100.0,float(x)))
def n(v,default=0.0):
    try:return float(v)
    except:return default
def norm(d):
    z=sum(max(0.0,v) for v in d.values()) or 1.0
    q={k:round(max(0.0,v)*100/z,1) for k,v in d.items()}
    k=max(q,key=q.get);q[k]=round(q[k]+100-sum(q.values()),1)
    return q
def pct_rank(hist,v):
    z=[n(x) for x in hist if x is not None]
    return 100*sum(x<=v for x in z)/len(z) if z else 50.0
def rolling_horizons(asof):
    s=str(asof or '')[:10]
    try:
        d=datetime.date.fromisoformat(s);y=d.year;m=d.month
    except:
        d=datetime.date.today();y=d.year;m=d.month
    if m<=3:return [(f'{y}H1',f'{y}년 상반기'),(f'{y}H2',f'{y}년 하반기'),(f'{y+1}H1',f'{y+1}년 상반기')]
    if m<=6:return [(f'{y}H2',f'{y}년 하반기'),(f'{y+1}H1',f'{y+1}년 상반기'),(f'{y+1}H2',f'{y+1}년 하반기')]
    if m<=9:return [(f'{y}Q4',f'{y}년 말'),(f'{y+1}H1',f'{y+1}년 상반기'),(f'{y+1}H2',f'{y+1}년 하반기')]
    return [(f'{y+1}H1',f'{y+1}년 상반기'),(f'{y+1}H2',f'{y+1}년 하반기'),(f'{y+2}H1',f'{y+2}년 상반기')]

def raw_risk_band(downturn):
    v=round(n(downturn))
    if v<=19:return 0
    if v<=29:return 1
    if v<=34:return 2
    if v<=44:return 3
    if v<=54:return 4
    return 5
def stable_risk_band(downturn,previous_band=None):
    candidate=raw_risk_band(downturn)
    if previous_band is None:return candidate
    try:band=max(0,min(5,int(previous_band)))
    except:return candidate
    if candidate>=band:return candidate
    v=n(downturn)
    while band>candidate and v<=RISK_LOWER[band]-EASING_HYSTERESIS_PP:band-=1
    return band
def display_for(weights,previous=None):
    d=n((weights or {}).get('downturn'));r=n((weights or {}).get('reacceleration'))
    band=stable_risk_band(d,(previous or {}).get('risk_band'))
    headline,rng,_,tone=RISK_LABELS[band]
    if band==0:secondary='재상승 신호 강함' if r>=40 else '하방 위험 낮음'
    elif band==1:secondary='재상승 신호 강화' if r>=35 else ('재상승 여지 확대' if r>=25 else '하방 위험 낮아지는 중')
    elif band==2:secondary='재상승 신호와 하방 위험 경합' if r>=35 else '방향성 확인 필요'
    elif band==3:secondary='하방 경계 속 재상승 신호 공존' if r>=35 else '하방 위험 주의'
    elif band==4:secondary='재상승 신호보다 조정 위험 우세'
    else:secondary='하락 시나리오 우세'
    return {'risk_band':band,'headline':headline,'risk_range':rng,'tone':tone,
            'downturn_weight':round(d,1),'reacceleration_weight':round(r,1),
            'secondary':secondary,'easing_hysteresis_pp':EASING_HYSTERESIS_PP}

def signal_matched_period(market):
    return market.get('signal_matched_period') or market.get('matched_period') or {}

def component_scores(market):
    s=market.get('kb_sentiment') or {};mm=market.get('m2_official') or market.get('m2') or {}
    mp=signal_matched_period(market).get('changes') or {}
    sent=n(s.get('score_0_100'),50);supply=n(s.get('jeonse_score_0_100'),50)
    value=n((market.get('kb_value') or {}).get('score_0_100'),50)
    finance=clamp(50+n(mm.get('mom_pct'))*8+n(mm.get('yoy_pct'))*1.5)
    trade=mp.get('trade_count_pct');under=mp.get('under15_share_pp')
    demand=clamp(50+n(trade)*.35+n(under)*1.5) if trade is not None and under is not None else None
    return {'finance':finance,'sentiment':sent,'demand':demand,'value':value,'supply':supply}

def price_overlay(market,research_last,kbval):
    research_m1=n((research_last or {}).get('price_mom_pct'));research_m3=n((research_last or {}).get('momentum_3m_pct'))
    out={'applied':False,'source':'turning_signal_research','research_m1_pct':round(research_m1,2),'research_m3_pct':round(research_m3,2)}
    m1,m3=research_m1,research_m3
    try:
        km=((market.get('kb_weekly_sale_index') or {}).get('momentum') or {})
        f1=((kbval.get('scale_fit') or {}).get('m1_from_kb4w') or {})
        f3=((kbval.get('scale_fit') or {}).get('m3_from_kb13w') or {})
        kb4=km.get('mom_4w_pct');kb13=km.get('mom_13w_pct')
        valid=bool(kbval.get('apply_recommended')) and kb4 is not None and kb13 is not None and f1.get('slope') is not None and f3.get('slope') is not None
        if valid:
            m1=n(f1.get('intercept'))+n(f1.get('slope'))*n(kb4)
            m3=n(f3.get('intercept'))+n(f3.get('slope'))*n(kb13)
            out={'applied':True,'source':'KB Seoul weekly sale index, scale-aligned to legacy research momentum',
                 'kb_as_of':km.get('as_of'),'kb_4w_pct':round(n(kb4),2),'kb_13w_pct':round(n(kb13),2),
                 'mapped_m1_pct':round(m1,2),'mapped_m3_pct':round(m3,2),
                 'research_m1_pct':round(research_m1,2),'research_m3_pct':round(research_m3,2),
                 'm1_fit_r2':round(n(f1.get('r2')),3),'m3_fit_r2':round(n(f3.get('r2')),3),
                 'validation_apply_recommended':True,'validation_generated_at':kbval.get('generated_at')}
    except Exception as e:
        out['fallback_reason']='overlay error: '+str(e)[:160]
    return m1,m3,out

def _turn_raw_hist(rows):
    out=[]
    for i,r in enumerate(rows):
        c=r.get('components') or {}
        def delta(k,lag):
            return n(c.get(k))-n((rows[i-lag].get('components') or {}).get(k)) if i>=lag else 0
        out.append(.30*delta('demand',1)+.20*delta('sentiment',1)+.15*delta('finance',1)+.15*delta('demand',3)+.10*delta('sentiment',3)+.10*delta('finance',3))
    return out

def live_research_signals(components,m1,m3,final_rows,research_rows):
    hist=[r for r in final_rows if r.get('components') and all((r.get('components') or {}).get(k) is not None for k in WEIGHTS)]
    if not hist:raise RuntimeError('final_backtest component history missing')
    last=hist[-1];prev=hist[-2] if len(hist)>=2 else last;back3=hist[-3] if len(hist)>=3 else hist[0]
    def delta(k,lag):
        ref=last if lag==1 else back3
        return n(components.get(k))-n((ref.get('components') or {}).get(k))
    turn_raw=.30*delta('demand',1)+.20*delta('sentiment',1)+.15*delta('finance',1)+.15*delta('demand',3)+.10*delta('sentiment',3)+.10*delta('finance',3)
    rawhist=_turn_raw_hist(hist)+[turn_raw]
    turn_rank=pct_rank(rawhist,turn_raw)
    research_last=research_rows[-1] if research_rows else {}
    prev_m1=n(research_last.get('price_mom_pct'))
    accel=m1-prev_m1
    price_turn=clamp(50+12*accel+8*m1)
    if m1 < -2:price_turn=min(price_turn,20)
    elif m1 < 0 and accel <= 0:price_turn=min(price_turn,35)
    elif m1 >= 0:price_turn=max(price_turn,65)
    sent1=delta('sentiment',1)
    sent2=n((last.get('components') or {}).get('sentiment'))-n((prev.get('components') or {}).get('sentiment'))
    dem3=delta('demand',3)
    early=clamp(50+8*sent1+5*sent2+1.2*dem3+6*accel)
    if m1 < -4:early=min(early,25)
    turn=.30*turn_rank+.35*price_turn+.35*early
    cheap=n(components.get('value'),50);distress=clamp(100-n(components.get('sentiment'),50))
    setup=.55*cheap+.45*distress
    opportunity=(setup*turn)/100
    breadth=clamp(.40*n(components.get('demand'))+.35*n(components.get('sentiment'))+.25*n(components.get('finance')))
    reaccel=clamp(50+6*m1+3*m3+1.5*delta('demand',1)+1.2*delta('sentiment',1))
    if m3<=0:reaccel=min(reaccel,35)
    bottom_zone=setup>=65 and turn>=35
    momentum_zone=m3>0 and breadth>=45 and reaccel>=50
    return {'setup':round(setup,1),'turn':round(turn,1),'opportunity':round(opportunity,1),
            'cheapness':round(cheap,1),'distress':round(distress,1),'price_turn':round(price_turn,1),
            'price_accel_pp':round(accel,2),'early_turn':round(early,1),'breadth':round(breadth,1),
            'reaccel':round(reaccel,1),'bottom_zone':bottom_zone,'momentum_zone':momentum_zone,
            'turn_rank':round(turn_rank,1),
            'deltas':{'finance_1m':round(delta('finance',1),2),'sentiment_1m':round(delta('sentiment',1),2),
                      'demand_1m':round(delta('demand',1),2),'finance_3m':round(delta('finance',3),2),
                      'sentiment_3m':round(delta('sentiment',3),2),'demand_3m':round(delta('demand',3),2)}}

def build_feature_layer(market,research,final,kbval):
    rows=research.get('rows') or [];x=rows[-1] if rows else {}
    components=component_scores(market)
    m1,m3,overlay=price_overlay(market,x,kbval)
    live_signals=live_research_signals(components,m1,m3,final.get('rows') or [],rows)
    # Do not overwrite historically validated breadth/reaccel/turn with a live
    # recomputation unless that alternative passes an explicit validation gate.
    # The first unified-v1 trial degraded reacceleration discrimination, so the
    # production candidate carries forward the latest certified research signals
    # while all three heads share the same live components and price overlay.
    certified_signals={
      'setup':round(n(x.get('setup'),50),1),'turn':round(n(x.get('turn'),50),1),
      'opportunity':round(n(x.get('opportunity'),25),1),'cheapness':round(n(x.get('cheapness'),components.get('value')),1),
      'distress':round(n(x.get('distress'),100-components.get('sentiment')),1),'price_turn':round(n(x.get('price_turn'),50),1),
      'price_accel_pp':round(n(x.get('price_accel_pp')),2),'early_turn':round(n(x.get('early_turn'),50),1),
      'breadth':round(n(x.get('breadth'),50),1),'reaccel':round(n(x.get('reaccel'),50),1),
      'bottom_zone':bool(x.get('bottom_zone',False)),'momentum_zone':bool(x.get('momentum_zone',False))
    }
    signals=certified_signals
    mm=market.get('m2_official') or market.get('m2') or {}
    signal_mp=signal_matched_period(market)
    mp=signal_mp.get('changes') or {}
    mortgage=n((market.get('mortgage_rate_official') or {}).get('rate_pct'),4.0)
    recent=rows[-6:]
    peak_m3=max([n(r.get('momentum_3m_pct')) for r in recent] or [0])
    liquidity=clamp(50+n(mm.get('yoy_pct'))*5)
    trade_raw=mp.get('trade_count_pct');under_raw=mp.get('under15_share_pp')
    trade=n(trade_raw) if trade_raw is not None else None;under=n(under_raw) if under_raw is not None else None
    trade_pressure=clamp(max(0,-trade)*1.5) if trade is not None else None
    rate_pressure=clamp((mortgage-3.0)*28)
    cooling=clamp((peak_m3-max(m3,0))*6+max(0,50-signals['breadth'])*.8+max(0,50-signals['reaccel'])*.6)
    hist_final=[r for r in (final.get('rows') or []) if r.get('components') and all((r.get('components') or {}).get(k) is not None for k in WEIGHTS)]
    prev_components=(hist_final[-1].get('components') or {}) if hist_final else {}
    component_deltas={k:(round(n(components.get(k))-n(prev_components.get(k)),1) if components.get(k) is not None and prev_components.get(k) is not None else None) for k in WEIGHTS}
    return {
      'snapshot_id':str(market.get('updated_at'))+'|KB'+str(overlay.get('kb_as_of') or '')+'|R'+str(x.get('ym') or ''),
      'as_of':market.get('updated_at'),'research_month':x.get('ym'),'research_provisional':bool(x.get('source_provisional',False)),
      'components':{k:(round(n(v),1) if v is not None else None) for k,v in components.items()},
      'component_deltas_vs_research_month':component_deltas,
      'buy_weights':WEIGHTS,
      'price_momentum':{'m1_pct':round(m1,2),'m3_pct':round(m3,2),'overlay':overlay},
      'signals':signals,
      'signal_policy':{'mode':'certified_research_carry_forward','research_month':x.get('ym'),
                       'reason':'live recomputation is diagnostic only until it passes forecast discrimination validation',
                       'live_recomputed_candidate':live_signals},
      'context':{'trade_count_pct':(round(trade,1) if trade is not None else None),'under15_share_pp':(round(under,1) if under is not None else None),'m2_mom_pct':mm.get('mom_pct'),
                 'm2_yoy_pct':mm.get('yoy_pct'),'mortgage_rate_pct':mortgage,'liquidity_support_0_100':round(liquidity,1),
                 'trade_pressure_0_100':(round(trade_pressure,1) if trade_pressure is not None else None),'rate_pressure_0_100':round(rate_pressure,1),
                 'recent_peak_3m_momentum_pct':round(peak_m3,2),'cooling_score_0_100':round(cooling,1),
                 'trade_signal_status':market.get('signal_matched_period_status','current'),
                 'trade_signal_as_of':signal_mp.get('as_of'),
                 'trade_signal_confidence':market.get('trade_signal_confidence') or {},
                 'raw_matched_as_of':(market.get('matched_period') or {}).get('as_of')},
      'lineage':{'market':'dist/market_indicators.json','research':'dist/turning_signal_research.json',
                 'certified_backtest':'dist/final_backtest.json','price_scale_validation':'dist/forecast_kb_momentum_validation.json'}
    }

def attach_engine_research_features(feature,research_rows,engine_research):
    """Attach only features that survived historical research gates."""
    if not engine_research or not engine_research.get('apply_recommended'):
        feature['engine_features']={'status':'research_not_applied','reason':'validated engine feature artifact missing or gate failed'}
        return
    c=feature.get('components') or {};sig=feature.get('signals') or {}
    m3=n((feature.get('price_momentum') or {}).get('m3_pct'))
    hist=[n(r.get('momentum_3m_pct')) for r in research_rows if r.get('momentum_3m_pct') is not None and not r.get('source_provisional')]
    mom_rank=pct_rank(hist+[m3],m3)
    values={
      'price_momentum':mom_rank,'breadth':sig.get('breadth'),'reaccel':sig.get('reaccel'),
      'finance':c.get('finance'),'sentiment':c.get('sentiment'),'demand':c.get('demand'),
      'value':c.get('value'),'supply':c.get('supply')
    }
    if any(v is None for v in values.values()):
        feature['engine_features']={'status':'data_check','market_strength':{'score_0_100':None,'label':'데이터 확인 중'}}
        return
    ordered=sorted(((k,n(v)) for k,v in values.items()),key=lambda x:x[1])
    core=ordered[1:-1];strength=sum(v for _,v in core)/len(core)
    cfg=engine_research.get('market_strength') or {}
    lo=n(cfg.get('low_cut'),40);hi=n(cfg.get('high_cut'),55)
    label='약함' if strength<lo else '보통' if strength<hi else '강함'
    overlay_cfg=engine_research.get('forecast_overlay') or {}
    weight=n(overlay_cfg.get('selected_weight')) if overlay_cfg.get('apply_recommended') else 0
    feature['engine_features']={
      'status':'validated_features_attached',
      'source':'dist/engine_feature_research.json',
      'market_strength':{
        'score_0_100':round(strength,1),'label':label,'low_cut':round(lo,1),'high_cut':round(hi,1),
        'momentum_percentile':round(mom_rank,1),
        'components':{k:{'value':round(n(v),1),'used_in_index':k in {x[0] for x in core}} for k,v in values.items()},
        'strongest':{'key':ordered[-1][0],'value':round(ordered[-1][1],1)},
        'weakest':{'key':ordered[0][0],'value':round(ordered[0][1],1)},
        'forecast_overlay':{
          'apply_recommended':bool(overlay_cfg.get('apply_recommended') and weight>0),
          'selected_weight':round(weight,4) if weight else None,
          'scope':overlay_cfg.get('scope'),'validation':{
             'baseline':overlay_cfg.get('baseline'),
             'selected':next((x for x in overlay_cfg.get('candidates',[]) if abs(n(x.get('weight'))-weight)<1e-4),None)
          }
        }
      },
      'rejected_features':engine_research.get('rejected_features') or []
    }
    feature.setdefault('lineage',{})['engine_feature_research']='dist/engine_feature_research.json'

def current_state_head(feature,research_rows):
    m1=n(feature['price_momentum']['m1_pct']);m3=n(feature['price_momentum']['m3_pct']);sig=feature['signals']
    recent=(research_rows or [])[-3:];was_rising=any(n(r.get('momentum_3m_pct'))>0 for r in recent)
    breadth=n(sig.get('breadth'));reaccel=n(sig.get('reaccel'))
    breadth_pass=breadth>=45;reaccel_pass=reaccel>=50;internals_confirmed=breadth_pass and reaccel_pass
    stage=0
    if sig.get('bottom_zone'):stage=1
    if m1>=0 and m3<=0 and not was_rising:stage=2
    if m3>0:stage=3
    if was_rising and m3<=0 and m1>=0:stage=3
    if sig.get('momentum_zone'):stage=4
    label=STAGE_LABELS[stage]
    divergence=bool(stage==3 and m3>0 and not internals_confirmed)
    strength=((feature.get('engine_features') or {}).get('market_strength') or {})
    strength_score=strength.get('score_0_100');strength_label=strength.get('label')
    confirmation_status='confirmed' if stage>=3 and internals_confirmed else ('weak' if stage>=3 else 'not_applicable')
    if stage==0:summary='1개월·3개월 가격 모멘텀이 약세여서 하락 국면으로 봅니다.'
    elif stage==1:summary='가격 부담과 심리 위축은 남아 있지만 하락 둔화·반전 신호가 강해지고 있습니다.'
    elif stage==2:summary='가격 하락이 멈추는 신호가 나타나 바닥 여부를 확인하는 구간입니다.'
    elif divergence:
        if strength_label=='약함' and strength_score is not None:
            summary=f'가격 상승은 유지되지만 시장 확산·재가속과 시장 힘({strength_score:.1f}/100)이 약해 상승 내부의 둔화 가능성을 함께 봅니다.'
        else:
            summary='가격 상승 모멘텀은 유지되지만 시장 확산·재가속 확인은 약해 상승·보합 내 확인 전 구간으로 봅니다.'
    elif stage==3:
        summary='가격 상승과 시장 내부확산이 함께 확인됐지만 가속 국면 조건은 아직 완전히 충족되지 않았습니다.'
    else:summary='가격 모멘텀과 시장 확산·재가속 신호가 함께 강해 가속 국면으로 봅니다.'
    next_gate=None
    if stage==3:
        misses=[]
        if not breadth_pass:misses.append('시장 확산 45 이상')
        if not reaccel_pass:misses.append('재가속 50 이상')
        next_gate=' · '.join(misses) if misses else '가속 조건 충족 확인'
    substate=(label+' · 힘 '+strength_label) if strength_label in ('약함','보통','강함') else label
    return {'stage':stage,'label':label,'substate':substate,'summary':summary,'was_rising':was_rising,'next_gate':next_gate,
            'market_strength':{'score_0_100':strength_score,'label':strength_label,'role':'current_state_quality'},
            'confirmation':{'status':confirmation_status,'rule':'breadth >= 45 AND reaccel >= 50',
                            'breadth_pass':breadth_pass,'reaccel_pass':reaccel_pass,'divergence':divergence,
                            'validation':'current_state_revalidation'},
            'evidence':{'m1_pct':m1,'m3_pct':m3,'breadth':sig.get('breadth'),'reaccel':sig.get('reaccel'),
                        'market_strength':strength_score,'turn':sig.get('turn'),'bottom_zone':sig.get('bottom_zone'),'momentum_zone':sig.get('momentum_zone')}}

def buy_condition_head(feature):
    c=feature['components'];available=[k for k in WEIGHTS if c.get(k) is not None]
    covered=sum(WEIGHTS[k] for k in available)
    score=round(sum(n(c[k])*WEIGHTS[k] for k in available)/covered,1) if covered else None
    if score is None:tier='연결 부족';rng='—'
    elif score<30:tier='매우 제약';rng='0~29'
    elif score<45:tier='제약 구간';rng='30~44'
    elif score<55:tier='중립 구간';rng='45~54'
    elif score<70:tier='개선 구간';rng='55~69'
    else:tier='우호 구간';rng='70~100'
    return {'score_0_100':score,'tier':tier,'range':rng,'coverage_weight':covered,'weights':WEIGHTS,'components':c}

def forward_weights(feature):
    c=feature['components'];sig=feature['signals'];ctx=feature['context'];m1=n(feature['price_momentum']['m1_pct']);m3=n(feature['price_momentum']['m3_pct'])
    finance=n(c.get('finance'),50);sent=n(c.get('sentiment'),50);demand=n(c.get('demand'),50);value=n(c.get('value'),50);supply=n(c.get('supply'),50)
    breadth=n(sig.get('breadth'),50);reaccel=n(sig.get('reaccel'),50)
    liquidity=n(ctx.get('liquidity_support_0_100'),50);trade_pressure=n(ctx.get('trade_pressure_0_100'),0);rate_pressure=n(ctx.get('rate_pressure_0_100'),0);cooling=n(ctx.get('cooling_score_0_100'),50)
    q4=norm({
      'consolidation':62+.18*finance+.14*supply+.22*clamp(100-abs(m3)*12)-.10*trade_pressure,
      'reacceleration':18+.34*reaccel+.22*breadth+.12*finance+.10*liquidity+max(0,m3)*2,
      'downturn':22+.24*(100-breadth)+.18*(100-demand)+.14*(100-sent)+.12*trade_pressure+.10*rate_pressure+.10*(100-value)-max(0,m1)*2
    })
    strength=((feature.get('engine_features') or {}).get('market_strength') or {})
    overlay=strength.get('forecast_overlay') or {}
    if overlay.get('apply_recommended') and strength.get('score_0_100') is not None:
        w=n(overlay.get('selected_weight'))
        if 0<w<1:
            baseline={k:round(v,3) for k,v in q4.items()};s=n(strength.get('score_0_100'))
            q4=norm({'consolidation':q4['consolidation'],
                     'reacceleration':(1-w)*q4['reacceleration']+w*s,
                     'downturn':(1-w)*q4['downturn']+w*(100-s)})
            overlay['applied']=True;overlay['baseline_short_horizon']=baseline
            overlay['applied_short_horizon']={k:round(v,3) for k,v in q4.items()}
    h1=norm({
      'consolidation':55+.16*finance+.14*supply+.16*clamp(100-cooling)+.08*liquidity,
      'reacceleration':28+.20*finance+.18*liquidity+.18*breadth+.14*reaccel+.10*sent,
      'downturn':24+.18*(100-demand)+.16*(100-sent)+.14*rate_pressure+.12*trade_pressure+.10*(100-value)-.12*liquidity
    })
    h2=norm({
      'consolidation':48+.14*finance+.12*supply+.10*clamp(100-abs(m3)*10),
      'reacceleration':34+.20*liquidity+.16*finance+.14*breadth+.10*sent,
      'downturn':26+.14*(100-demand)+.12*(100-sent)+.12*rate_pressure+.10*(100-value)-.14*liquidity+(12 if m3<0 else 0)
    })
    return q4,h1,h2

def forward_scenario_head(feature,previous=None):
    previous_display={h.get('period'):h.get('display') or {} for h in ((previous or {}).get('horizons') or [])}
    labels=rolling_horizons(feature.get('as_of'));q4,h1,h2=forward_weights(feature);arr=[]
    for i,w in enumerate((q4,h1,h2)):
        p,l=labels[i];arr.append({'period':p,'label':l,'weights':w,'base_case':('consolidation' if i==0 else max(w,key=w.get)),
                                 'display':display_for(w,previous_display.get(p))})
    return {'horizons':arr,'headline':' → '.join(x['display']['headline'] for x in arr),
            'risk_path':[round(n(x['display']['downturn_weight'])) for x in arr],
            'validated_feature_overlay':(((feature.get('engine_features') or {}).get('market_strength') or {}).get('forecast_overlay') or {}),
            'weights_are_not_calibrated_probabilities':True,
            'display_rules':{'primary':'downturn scenario weight, rounded to visible whole percent',
              'bands':[{'min':0,'max':19,'headline':'상승 우위'},{'min':20,'max':29,'headline':'재상승 가능성 확대'},
                       {'min':30,'max':34,'headline':'혼조·방향 탐색'},{'min':35,'max':44,'headline':'쉬어가기·하방 경계'},
                       {'min':45,'max':54,'headline':'조정 위험 확대'},{'min':55,'max':100,'headline':'하락 우위'}],
              'secondary':'reacceleration weight adjusts supporting phrase','hysteresis':'easing requires 2%p beyond boundary'}}

def build_judgment(root,previous_forecast=None):
    root=pathlib.Path(root)
    market=json.loads((root/'dist/market_indicators.json').read_text())
    research=json.loads((root/'dist/turning_signal_research.json').read_text())
    final=json.loads((root/'dist/final_backtest.json').read_text())
    kbval=json.loads((root/'dist/forecast_kb_momentum_validation.json').read_text()) if (root/'dist/forecast_kb_momentum_validation.json').exists() else {}
    if previous_forecast is None and (root/'dist/regime_forecast.json').exists():
        try:previous_forecast=json.loads((root/'dist/regime_forecast.json').read_text())
        except:previous_forecast={}
    feature=build_feature_layer(market,research,final,kbval)
    common_path=root/'dist/common_feature_layer_v2.json';validation_path=root/'dist/market_judgment_validation.json'
    if common_path.exists():
        try:
            common=json.loads(common_path.read_text(encoding='utf-8'))
            feature['scope']=common.get('scope') or {}
            features=common.get('features') or {};finance_v2=features.get('finance_v2_candidate') or {}
            feature['candidate_research']={
              'artifact':'dist/common_feature_layer_v2.json',
              'version':common.get('version'),
              'features':{k:{'status':v.get('status'),'production_applied':bool(v.get('production_applied'))}
                          for k,v in features.items() if isinstance(v,dict)}
            }
            gate=False
            if validation_path.exists():
                try:
                    mv=json.loads(validation_path.read_text(encoding='utf-8'))
                    gate=bool(((mv.get('finance_v2_integrated') or {}).get('apply_recommended')))
                except Exception:gate=False
            f2=finance_v2.get('score_0_100');credit=(finance_v2.get('liquidity_credit_availability') or {}).get('score_0_100');funding=(finance_v2.get('funding_cost') or {}).get('score_0_100')
            feature['context']['finance_model']='finance_v1_m2'
            feature['context']['finance_v1_score_0_100']=feature['components'].get('finance')
            feature['context']['finance_v2_gate_passed']=gate
            feature['context']['credit_availability_0_100']=credit
            feature['context']['funding_cost_0_100']=funding
            if gate and f2 is not None and credit is not None:
                feature['components']['finance']=round(n(f2),1)
                feature['context']['liquidity_support_0_100']=round(n(credit),1)
                feature['context']['finance_model']='finance_v2_credit_cost'
                feature['component_deltas_vs_research_month']['finance']=None
                feature['candidate_research']['features'].setdefault('finance_v2_candidate',{})['production_applied']=True
            feature['lineage']['common_feature_candidates']='dist/common_feature_layer_v2.json'
            feature['lineage']['finance_v2_validation']='dist/market_judgment_validation.json'
        except Exception as e:
            feature['candidate_research']={'status':'load_error','reason':str(e)[:160]}
    engine_path=root/'dist/engine_feature_research.json'
    engine_research={}
    if engine_path.exists():
        try:engine_research=json.loads(engine_path.read_text(encoding='utf-8'))
        except Exception as e:engine_research={'status':'load_error','reason':str(e)[:160]}
    attach_engine_research_features(feature,research.get('rows') or [],engine_research)
    current=current_state_head(feature,research.get('rows') or [])
    buy=buy_condition_head(feature)
    forward=forward_scenario_head(feature,previous_forecast or {})
    return {'status':'connected','engine_version':'unified_market_judgment_v1','as_of':feature.get('as_of'),
            'architecture':'Common Feature Layer -> Current State / Buy Condition / Forward Scenario',
            'feature_layer':feature,'heads':{'current_state':current,'buy_condition':buy,'forward_scenario':forward},
            'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}

def legacy_forecast_payload(judgment,root):
    root=pathlib.Path(root);research=json.loads((root/'dist/turning_signal_research.json').read_text());final=json.loads((root/'dist/final_backtest.json').read_text())
    rows=research.get('rows') or [];x=rows[-1] if rows else {};feature=judgment['feature_layer'];forward=judgment['heads']['forward_scenario'];state=judgment['heads']['current_state']
    analog=[]
    for i,r in enumerate(rows[:-1]):
        prev=rows[max(0,i-2):i];pp=max([n(z.get('momentum_3m_pct')) for z in prev] or [0])
        if r.get('fwd_6m_pct') is not None and pp>=5 and 0<=n(r.get('momentum_3m_pct'))<=2 and 0<=n(r.get('price_mom_pct'))<=.5 and not r.get('momentum_zone'):
            analog.append({k:r.get(k) for k in ('ym','price_mom_pct','momentum_3m_pct','fwd_3m_pct','fwd_6m_pct','fwd_12m_pct')})
    long={}
    try:long=json.loads((root/'dist/final_long_cycle_validation.json').read_text())
    except:long={}
    selected=(long.get('selected_on_pre2018') or {})
    return {'status':'research_only','weights_are_not_calibrated_probabilities':True,
      'method':'unified market judgment engine; all live heads consume one common feature snapshot',
      'as_of':judgment.get('as_of'),'latest_research_month':feature.get('research_month'),'latest_research_provisional':feature.get('research_provisional'),
      'latest_certified_backtest_month':final.get('certified_through'),'horizons':forward['horizons'],'display_rules':forward['display_rules'],
      'state':{'current_phase':state.get('label'),'forecast_price_phase':'uptrend' if n(feature['price_momentum']['m3_pct'])>0 else ('post_rally_consolidation' if n(feature['price_momentum']['m1_pct'])>=0 else 'downtrend'),
               'recent_peak_3m_momentum_pct':feature['context']['recent_peak_3m_momentum_pct'],'cooling_score_0_100':feature['context']['cooling_score_0_100'],
               'liquidity_support_0_100':feature['context']['liquidity_support_0_100']},
      'triggers':{'reacceleration_confirmation':['3개월 가격모멘텀 > 2%','breadth >= 45','reaccel >= 50','동일기간 거래량 감소폭이 -10% 이내로 회복'],
                  'downturn_confirmation':['월간 가격모멘텀 < 0','3개월 가격모멘텀 < 0','거래 위축 지속','M2/금융여건 동반 둔화'],
                  'current_check':{**feature['components'],'price_mom_pct':feature['price_momentum']['m1_pct'],'momentum_3m_pct':feature['price_momentum']['m3_pct'],
                                   'breadth':feature['signals']['breadth'],'reaccel':feature['signals']['reaccel'],'turn':feature['signals']['turn'],
                                   'market_strength':(((feature.get('engine_features') or {}).get('market_strength') or {}).get('score_0_100')),
                                   'market_strength_label':(((feature.get('engine_features') or {}).get('market_strength') or {}).get('label')),
                                   'trade_count_pct':feature['context']['trade_count_pct'],'m2_yoy_pct':feature['context']['m2_yoy_pct'],'mortgage_rate_pct':feature['context']['mortgage_rate_pct'],
                                   'snapshot_id':feature['snapshot_id']}},
      'price_momentum_overlay':feature['price_momentum']['overlay'],'engine_features':feature.get('engine_features') or {},
      'historical_analogs':analog,'analog_warning':'small sample; analogs are diagnostic only',
      'long_cycle_guardrail':{'selected_pre2018_only':selected,'sample_is_small':True},
      'unified_snapshot_id':feature['snapshot_id'],'generated_at':judgment.get('generated_at')}
