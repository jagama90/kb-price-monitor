#!/usr/bin/env python3
"""Daily finance/sentiment/trade upside-probability SHADOW candidate.

Never promote by a better-looking current value. Fit the adjustment using only
a predeclared historical selection window; measure an untouched later holdout.
Archived historical feature vintages are unavailable, so even good retrospective
metrics would NOT certify this candidate for production.
"""
from __future__ import annotations
import datetime as dt
import json
import math
from pathlib import Path

import build_upside_probability_engine as base

ROOT=Path(__file__).resolve().parents[1]
LONG=ROOT/'dist/long_cycle_master.json'
FEATURES=ROOT/'dist/engine_feature_research.json'
MARKET=ROOT/'dist/market_indicators.json'
JUDGMENT=ROOT/'dist/market_judgment.json'
CERTIFIED=ROOT/'dist/upside_probability_engine.json'
OUT=ROOT/'dist/upside_daily_candidate.json'
NAMES=('finance','sentiment','demand')
SELECT_END='202412'
HOLD_START='202501'
LAMBDA=10.0  # frozen ridge penalty; no selection on holdout results
MIN_SELECTION=36
MIN_HOLDOUT=24
EPS=1e-6

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sigmoid(x):
    if x>=0:
        return 1/(1+math.exp(-min(x,700)))
    z=math.exp(max(x,-700))
    return z/(1+z)

def logit(p):
    return math.log(max(EPS,min(1-EPS,p))/(1-max(EPS,min(1-EPS,p))))

def vector(components):
    if not isinstance(components,dict):
        return None
    values=[base.finite(components.get(k)) for k in NAMES]
    if any(x is None or not 0<=x<=100 for x in values):
        return None
    return values

def features_at_selection(rows,src):
    """Monthly research snapshots, NOT authentic date-stamped vintages."""
    present={r['ym']:r for r in rows}
    out=[]
    for feat in src.get('rows') or []:
        ym=str(feat.get('ym') or '')
        row=present.get(ym)
        values=vector(feat.get('components'))
        if row is None or values is None or ym<'202209':
            continue
        fwd=base.finite(row.get('fwd_1m_pct'))
        if fwd is None or not row.get('ym') or base.ym_ord(ym)+1>base.ym_ord(rows[-1]['ym']):
            continue
        out.append({'ym':ym,'v':values,'outcome':base.klass(fwd,0),
                    'fwd_1m_pct':fwd})
    return out

def fit(selection, offset):
    """Ridge-penalized logistic residual on top of frozen KNN logits."""
    assert len(selection)>=18
    means=[sum(row['v'][i] for row in selection)/len(selection) for i in range(3)]
    # 20 score points = one feature unit; fixed independent of holdout.
    features=[[(row['v'][j]-means[j])/20 for j in range(3)] for row in selection]
    co=[0.0,0.0,0.0]
    for _ in range(900):
        grad=[2*LAMBDA*c for c in co]
        for x,row in zip(features,selection):
            p=sigmoid(offset[row['ym']]+sum(a*b for a,b in zip(co,x)))
            y=1 if row['outcome']=='up' else 0
            for j in range(3):grad[j]+=(p-y)*x[j]
        lr=0.08/max(1,len(selection))
        co=[max(-1.5,min(1.5,co[j]-lr*grad[j])) for j in range(3)]
    return means,co

def all_metrics(preds):
    if not preds:return None
    brier=sum(sum((p[c]-(1 if y==c else 0))**2 for c in ('up','flat','down')) for p,y in preds)/len(preds)
    ece=0
    for lo,hi in zip([0,.2,.4,.6,.8],[.2,.4,.6,.8,1.001]):
        xs=[(p['up'],y=='up') for p,y in preds if lo<=p['up']<hi]
        if xs:ece+=len(xs)/len(preds)*abs(sum(q for q,_ in xs)/len(xs)-sum(y for _,y in xs)/len(xs))
    auc=base.auc_up([{'probabilities':p,'target':y} for p,y in preds])
    return {'n':len(preds),'multiclass_brier':round(brier,4),
            'up_auc':None if auc is None else round(auc,4),'up_ece':round(ece,4)}

def adjust(prob,offset):
    p0=prob['up']
    p=sigmoid(logit(p0)+offset)
    rest=1-p0
    if rest<=0:return None
    return {'up':p,'flat':(1-p)*prob['flat']/rest,'down':(1-p)*prob['down']/rest}

def live_inputs(market,judgment,engine):
    if judgment.get('status') not in ('validated','validated_unified_judgment','ok','connected','validated_market_judgment'):
        # The top-level judgment uses "validated_market_judgment" in production;
        # trust component presence + matching scope instead of inventing scores.
        pass
    scope=(engine.get('scope') or {}).get('market_scope_id')
    jscope=((judgment.get('feature_layer') or {}).get('scope') or {}).get('market_scope_id')
    if scope and jscope and scope!=jscope:
        raise ValueError('probability/feature-layer market scope mismatch')
    comps=(judgment.get('feature_layer') or {}).get('components') or {}
    v=vector(comps)
    if v is None:return {'status':'data_check','reason':'finance/sentiment/trade feature unavailable'}
    kb=market.get('kb_sentiment') or {}
    rr=(market.get('refresh_run') or {}).get('sources') or {}
    signal=market.get('signal_matched_period') or {}
    tradeperiod=(signal.get('current') or {}).get('period')
    sentiment_date=((kb.get('latest') or {}).get('매수우위') or {}).get('date')
    mortgage_period=(market.get('mortgage_rate_official') or {}).get('period')
    base_day=((market.get('base_rate_official') or {}).get('latest') or {}).get('date')
    if kb.get('status')!='connected' or not sentiment_date or not mortgage_period or not tradeperiod:
        return {'status':'data_check','reason':'required source observation date unavailable'}
    # MOLIT "fallback_last_good" is allowed for a research-only comparison,
    # but must NOT be presented as fresh or as a new trading observation.
    trade_state=rr.get('molit') or 'unknown'
    if trade_state not in ('connected','fallback_last_good'):
        return {'status':'data_check','reason':'MOLIT trade source status unavailable'}
    if base_day is None:return {'status':'data_check','reason':'finance base-rate date unavailable'}
    return {'status':'ok','values':v,'components':{k:round(v[j],2) for j,k in enumerate(NAMES)},
            'vintages':{'finance_mortgage_month':mortgage_period,'finance_base_rate_day':base_day,
                        'sentiment_week':sentiment_date,'trade_completed_month':tradeperiod},
            'source_status':{'finance':rr.get('ecos'),'sentiment':rr.get('kb_sentiment'),
                             'trade':trade_state},
            'as_of':judgment.get('as_of')}

def main():
    historical=read(LONG)
    research=read(FEATURES)
    market=read(MARKET)
    judgment=read(JUDGMENT)
    certified=read(CERTIFIED)
    rows=base.monthly_rows(historical)
    pre=[r for r in rows if r['ym']<'201201']
    band=base.quantile([abs(x['fwd_1m_pct']) for x in pre if x['fwd_1m_pct'] is not None],.25)
    if certified['model']['selected_k']['1']!=10 or band is None:
        raise RuntimeError('certified 1m baseline changed; re-audit candidate')
    matched=[]
    for row in features_at_selection(rows,research):
        ref=base.point_in_time(rows,row['ym'],1,band,10)
        if ref is None:continue
        row['outcome']=base.klass(row['fwd_1m_pct'],band)
        row['baseline']={k:float(v)/100 for k,v in ref['probabilities'].items()}
        matched.append(row)
    selection=[r for r in matched if r['ym']<=SELECT_END]
    holdout=[r for r in matched if r['ym']>=HOLD_START]
    estimated=bool(len(selection)>=18)
    means=coeff=None
    if estimated:
        means,coeff=fit(selection,{r['ym']:logit(r['baseline']['up']) for r in selection})
    def results(data,apply):
        if not data:return None
        return all_metrics([(adjust(r['baseline'],sum(coeff[i]*(r['v'][i]-means[i])/20 for i in range(3))) if apply else r['baseline'],r['outcome']) for r in data])
    metrics={'selection':{'baseline':results(selection,False),'candidate':results(selection,True) if estimated else None},
             'holdout':{'baseline':results(holdout,False),'candidate':results(holdout,True) if estimated else None}}
    # The source is a revised historical series, not real historical vintages.
    # Prospective independence and mature sample/class coverage are absent.
    gate_reasons=[]
    if len(selection)<MIN_SELECTION:gate_reasons.append('selection below 36 point-in-time observations')
    if len(holdout)<MIN_HOLDOUT:gate_reasons.append('holdout below 24 observations')
    gate_reasons.append('historical finance/sentiment/trade feature vintages not verified')
    gate_reasons.append('independent prospective three-signal evaluation not yet certified')
    live=live_inputs(market,judgment,certified)
    current=certified.get('current') or {}
    basep=base.finite((current.get('probabilities') or {}).get('up'))
    if basep is None or current.get('status')!='ok' or not 0<=basep<=100:
        live={'status':'data_check','reason':'certified probability is unavailable'}
    elif live['status']=='ok' and estimated:
        p0={k:v/100 for k,v in current['probabilities'].items()}
        v=live['values']
        contributions={k:coeff[i]*(v[i]-means[i])/20 for i,k in enumerate(NAMES)}
        result=adjust(p0,sum(contributions.values()))
        if result is not None:
            probs={k:round(100*p,1) for k,p in result.items()}
            live['probabilities']=probs
            live['reference_probability_up_pct']=basep
            live['difference_pp']=round(probs['up']-basep,1)
            live['log_odds_contributions']={k:round(val,4) for k,val in contributions.items()}
            live['meaning']='research-only probability candidate; not certified observed event frequency'
            live['source_price_as_of']=current.get('as_of')
        else:live={'status':'data_check','reason':'certified class probabilities invalid'}
    else:
        live={'status':'data_check','reason':live.get('reason') or 'candidate training unavailable'}
    payload={'status':'research_only_not_certified','version':'daily_multisignal_research_v1',
             'production_applied':False,
             'scope':certified.get('scope'),
             'inputs':['finance','sentiment','demand'],
             'training':{'selection_from':'202209','selection_through':SELECT_END,
                         'holdout_from':HOLD_START,'label':'certified forward 1m REB monthly price direction',
                         'target_maturity_rule':'t+1 <= historical source end; training parameters estimated on selection only',
                         'model':'ridge logistic correction over unchanged certified KNN prior',
                         'ridge_lambda':LAMBDA,
                         'selection_n':len(selection),'holdout_n':len(holdout),
                         'historical_vintage_confirmed':False,
                         'minimum_certification_selection_n':MIN_SELECTION,
                         'minimum_certification_holdout_n':MIN_HOLDOUT},
             'metrics':metrics,'coefficients':None if coeff is None else {k:round(coef,5) for k,coef in zip(NAMES,coeff)},
             'selection_feature_means':None if means is None else {k:round(val,4) for k,val in zip(NAMES,means)},
             'certification':{'eligible':False,'blocking_reasons':gate_reasons,
                              'policy':'existing certified probability remains primary until true point-in-time plus independent prospective certification'},
             'current':live,
             'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
             'lineage':{'certified_model':str(CERTIFIED.relative_to(ROOT)),
                        'monthly_history':str(LONG.relative_to(ROOT)),
                        'revised_research_features':str(FEATURES.relative_to(ROOT)),
                        'daily_market':str(MARKET.relative_to(ROOT)),
                        'daily_common_feature_layer':str(JUDGMENT.relative_to(ROOT))}}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'production_applied':False,
                      'selection_n':len(selection),'holdout_n':len(holdout),
                      'selection':metrics['selection'],'holdout':metrics['holdout'],
                      'current':live},ensure_ascii=False))
if __name__=='__main__':
    main()
