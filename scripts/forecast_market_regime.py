#!/usr/bin/env python3
"""Research-only forward regime scenario engine.

Combines the validated turning-state research with the freshest live market
snapshot. Scenario weights are evidence weights, not calibrated probabilities.
The engine is intentionally deterministic and transparent so monthly changes
can be audited.
"""
import json, pathlib, datetime, math

R=pathlib.Path(__file__).resolve().parents[1]
TURN=R/'dist/turning_signal_research.json'
MARKET=R/'dist/market_indicators.json'
FINAL=R/'dist/final_backtest.json'
LONG=R/'dist/final_long_cycle_validation.json'
OUT=R/'dist/regime_forecast.json'

def clamp(x): return max(0.0,min(100.0,float(x)))
def n(v,default=0.0):
    try:return float(v)
    except:return default
def rolling_horizons(as_of):
    try:
        y=int(str(as_of)[:4]);m=int(str(as_of)[5:7])
    except Exception:
        d=datetime.date.today();y,m=d.year,d.month
    if m<=3:return [(f'{y}H1',f'{y}년 상반기'),(f'{y}H2',f'{y}년 하반기'),(f'{y+1}H1',f'{y+1}년 상반기')]
    if m<=6:return [(f'{y}H2',f'{y}년 하반기'),(f'{y+1}H1',f'{y+1}년 상반기'),(f'{y+1}H2',f'{y+1}년 하반기')]
    if m<=9:return [(f'{y}Q4',f'{y}년 말'),(f'{y+1}H1',f'{y+1}년 상반기'),(f'{y+1}H2',f'{y+1}년 하반기')]
    return [(f'{y+1}H1',f'{y+1}년 상반기'),(f'{y+1}H2',f'{y+1}년 하반기'),(f'{y+2}H1',f'{y+2}년 상반기')]

def norm(d):
    z=sum(max(0.0,v) for v in d.values()) or 1.0
    q={k:round(max(0.0,v)*100/z,1) for k,v in d.items()}
    # remove rounding drift
    k=max(q,key=q.get); q[k]=round(q[k]+100-sum(q.values()),1)
    return q

def main():
    tr=json.loads(TURN.read_text()); rows=tr.get('rows',[])
    if not rows: raise SystemExit('turning_signal_research has no rows')
    x=rows[-1]; recent=rows[-6:]
    m=json.loads(MARKET.read_text())
    fb=json.loads(FINAL.read_text()) if FINAL.exists() else {}
    lv=json.loads(LONG.read_text()) if LONG.exists() else {}

    sent=n((m.get('kb_sentiment') or {}).get('score_0_100'),50)
    supply=n((m.get('kb_sentiment') or {}).get('jeonse_score_0_100'),50)
    value=n((m.get('kb_value') or {}).get('score_0_100'),50)
    mm=m.get('m2_official') or m.get('m2') or {}
    finance=clamp(50+n(mm.get('mom_pct'))*8+n(mm.get('yoy_pct'))*1.5)
    mp=(m.get('matched_period') or {}).get('changes') or {}
    trade=n(mp.get('trade_count_pct'))
    under=n(mp.get('under15_share_pp'))
    demand=clamp(50+trade*.35+under*1.5) if mp else 50
    mortgage=n((m.get('mortgage_rate_official') or {}).get('rate_pct'),4.0)

    m1=n(x.get('price_mom_pct')); m3=n(x.get('momentum_3m_pct'))
    breadth=n(x.get('breadth'),50); reaccel=n(x.get('reaccel'),50)
    peak_m3=max([n(r.get('momentum_3m_pct')) for r in recent] or [0])
    liquidity=clamp(50+n(mm.get('yoy_pct'))*5)
    trade_pressure=clamp(max(0,-trade)*1.5)
    rate_pressure=clamp((mortgage-3.0)*28)
    cooling=clamp((peak_m3-max(m3,0))*6 + max(0,50-breadth)*.8 + max(0,50-reaccel)*.6)

    # Near term: current momentum/trade matter most.
    q4=norm({
      'consolidation': 62 + .18*finance + .14*supply + .22*clamp(100-abs(m3)*12) - .10*trade_pressure,
      'reacceleration': 18 + .34*reaccel + .22*breadth + .12*finance + .10*liquidity + max(0,m3)*2,
      'downturn': 22 + .24*(100-breadth)+.18*(100-demand)+.14*(100-sent)+.12*trade_pressure+.10*rate_pressure+.10*(100-value)-max(0,m1)*2
    })
    # Medium term: liquidity and financing transmission get more weight.
    h1=norm({
      'consolidation': 55 + .16*finance + .14*supply + .16*clamp(100-cooling) + .08*liquidity,
      'reacceleration': 28 + .20*finance + .18*liquidity + .18*breadth + .14*reaccel + .10*sent,
      'downturn': 24 + .18*(100-demand)+.16*(100-sent)+.14*rate_pressure+.12*trade_pressure+.10*(100-value)-.12*liquidity
    })
    # Longer term: flatten weights because uncertainty rises; sustained liquidity
    # support raises recovery/reacceleration unless price trend has turned negative.
    h2=norm({
      'consolidation': 48 + .14*finance + .12*supply + .10*clamp(100-abs(m3)*10),
      'reacceleration': 34 + .20*liquidity + .16*finance + .14*breadth + .10*sent,
      'downturn': 26 + .14*(100-demand)+.12*(100-sent)+.12*rate_pressure+.10*(100-value)-.14*liquidity + (12 if m3<0 else 0)
    })

    # Historical analogs: strong prior momentum cooling to 0~2%, non-negative m1.
    analog=[]
    for i,r in enumerate(rows[:-1]):
      prev=rows[max(0,i-2):i]
      pp=max([n(z.get('momentum_3m_pct')) for z in prev] or [0])
      if r.get('fwd_6m_pct') is not None and pp>=5 and 0<=n(r.get('momentum_3m_pct'))<=2 and 0<=n(r.get('price_mom_pct'))<=.5 and not r.get('momentum_zone'):
        analog.append({k:r.get(k) for k in ('ym','price_mom_pct','momentum_3m_pct','fwd_3m_pct','fwd_6m_pct','fwd_12m_pct')})

    latest_cert=fb.get('certified_through') or (fb.get('rows') or [{}])[-1].get('ym')
    selected=(lv.get('selected_on_pre2018') or {})
    triggers={
      'reacceleration_confirmation':['3개월 가격모멘텀 > 2%','breadth >= 45','reaccel >= 50','동일기간 거래량 감소폭이 -10% 이내로 회복'],
      'downturn_confirmation':['월간 가격모멘텀 < 0','3개월 가격모멘텀 < 0','거래 위축 지속','M2/금융여건 동반 둔화'],
      'current_check':{
        'price_mom_pct':round(m1,2),'momentum_3m_pct':round(m3,2),'breadth':round(breadth,1),'reaccel':round(reaccel,1),
        'finance':round(finance,1),'sentiment':round(sent,1),'demand':round(demand,1),'value':round(value,1),'supply':round(supply,1),
        'trade_count_pct':round(trade,1),'m2_yoy_pct':mm.get('yoy_pct'),'mortgage_rate_pct':mortgage
      }
    }
    horizon_labels=rolling_horizons(m.get('updated_at'))
    payload={
      'status':'research_only',
      'weights_are_not_calibrated_probabilities':True,
      'method':'transparent scenario-weight engine: certified turning-state research + freshest live market overlay; no future labels are used in current scoring',
      'as_of':m.get('updated_at'),
      'latest_research_month':x.get('ym'),
      'latest_research_provisional':bool(x.get('source_provisional',False)),
      'latest_certified_backtest_month':latest_cert,
      'horizons':[
        {'period':horizon_labels[0][0],'label':horizon_labels[0][1],'weights':q4,'base_case':'consolidation'},
        {'period':horizon_labels[1][0],'label':horizon_labels[1][1],'weights':h1,'base_case':max(h1,key=h1.get)},
        {'period':horizon_labels[2][0],'label':horizon_labels[2][1],'weights':h2,'base_case':max(h2,key=h2.get)}
      ],
      'state':{
        'current_phase':'post_rally_consolidation' if m3<=0 and m1>=0 else ('uptrend' if m3>0 else 'downtrend'),
        'recent_peak_3m_momentum_pct':round(peak_m3,2),
        'cooling_score_0_100':round(cooling,1),
        'liquidity_support_0_100':round(liquidity,1)
      },
      'triggers':triggers,
      'historical_analogs':analog,
      'analog_warning':'small sample; analogs are diagnostic only',
      'long_cycle_guardrail':{'selected_pre2018_only':selected,'sample_is_small':True},
      'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    print(json.dumps({'as_of':payload['as_of'],'horizons':payload['horizons'],'analogs':len(analog)},ensure_ascii=False))

if __name__=='__main__': main()
