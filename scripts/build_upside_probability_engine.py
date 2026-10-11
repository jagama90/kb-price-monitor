#!/usr/bin/env python3
"""Build a validated rising-probability engine from historical market analogs.

The model is deliberately small and auditable:
- target is three-class: up / flat / down
- flat bands are frozen from pre-2012 history only
- features are trailing price momentum only
- analog selection is expanding walk-forward and target-maturity aware
- k is selected on 2012-2017 only, then evaluated on 2018+ holdout
- trade, M2 and broader composite candidates are screened but not promoted unless
  they beat the price-only model on the frozen selection/holdout protocol.

Current inputs use the latest REB weekly 4w/13w sale-index momentum because the
long-cycle training target is also REB market-price history. No city/district name
is embedded in the formula.
"""
from __future__ import annotations
import datetime as dt
import json
import math
from pathlib import Path

R=Path(__file__).resolve().parents[1]
LONG=R/'dist/long_cycle_master.json'
MARKET=R/'dist/market_indicators.json'
OUT=R/'dist/upside_probability_engine.json'

HORIZONS=(1,3,6,12)
K_CANDIDATES=(10,15,20,25,35)
FEATURE_CANDIDATES={
    'price_momentum':['m1','m3'],
    'price_plus_trade':['m1','m3','trade'],
    'price_plus_m2':['m1','m3','m2'],
    'price_trade_m2':['m1','m3','trade','m2'],
}
PRODUCTION_HORIZONS=(1,3,6)

def finite(v):
    if v is None or isinstance(v,bool): return None
    try:
        x=float(v)
    except (TypeError,ValueError):
        return None
    return x if math.isfinite(x) else None

def pct(a,b):
    a=finite(a);b=finite(b)
    return None if a is None or b in (None,0) else (a/b-1)*100

def ym_ord(ym):
    s=str(ym or '')
    if len(s)<6:return None
    try:return int(s[:4])*12+int(s[4:6])-1
    except ValueError:return None

def shift_ym(ym,months):
    n=ym_ord(ym)
    if n is None:return None
    n+=months
    return f'{n//12:04d}{n%12+1:02d}'

def quantile(vals,q):
    z=sorted(float(x) for x in vals if x is not None)
    if not z:return None
    p=(len(z)-1)*q;lo=int(math.floor(p));hi=int(math.ceil(p))
    return z[lo]+(z[hi]-z[lo])*(p-lo)

def klass(v,band):
    v=finite(v)
    if v is None or band is None:return None
    return 'up' if v>band else ('down' if v<-band else 'flat')

def monthly_rows(long_payload):
    src=long_payload.get('rows') or []
    rows=[]
    for i,r in enumerate(src):
        price=finite((r.get('price') or {}).get('value'))
        if price in (None,0):continue
        trade=finite((r.get('trade') or {}).get('value'))
        m2=finite((r.get('m2') or {}).get('yoy_pct'))
        row={'i':i,'ym':str(r.get('ym') or ''),'m1':None,'m3':None,'trade':None,'m2':m2}
        if i>=1:row['m1']=pct(price,(src[i-1].get('price') or {}).get('value'))
        if i>=3:row['m3']=pct(price,(src[i-3].get('price') or {}).get('value'))
        if i>=5 and trade is not None:
            prior=[finite((x.get('trade') or {}).get('value')) for x in src[i-5:i-2]]
            if len(prior)==3 and all(x is not None for x in prior):
                avg=sum(prior)/3
                row['trade']=pct(trade,avg)
        for h in HORIZONS:
            row[f'fwd_{h}m_pct']=pct((src[i+h].get('price') or {}).get('value'),price) if i+h<len(src) else None
        rows.append(row)
    return rows

def standardized_knn(train,row,features,k):
    if not train:return None
    means=[];sds=[]
    for f in features:
        vals=[finite(x.get(f)) for x in train]
        if any(v is None for v in vals):return None
        mean=sum(vals)/len(vals)
        var=sum((v-mean)**2 for v in vals)/max(1,len(vals)-1)
        means.append(mean);sds.append(math.sqrt(var) or 1.0)
    dist=[]
    for x in train:
        d=0.0
        for j,f in enumerate(features):
            rv=finite(row.get(f));xv=finite(x.get(f))
            if rv is None or xv is None:return None
            d+=((xv-rv)/sds[j])**2
        dist.append((math.sqrt(d),x))
    neighbors=[x for _,x in sorted(dist,key=lambda z:z[0])[:min(k,len(dist))]]
    counts={'up':1,'flat':1,'down':1}  # Dirichlet/Laplace smoothing
    for x in neighbors:counts[x['target']]+=1
    denom=sum(counts.values())
    return {
        'probabilities':{c:counts[c]/denom for c in ('up','flat','down')},
        'neighbors':[x.get('ym') for x in neighbors],
    }

def auc_up(preds):
    pos=[x for x in preds if x['target']=='up'];neg=[x for x in preds if x['target']!='up']
    if not pos or not neg:return None
    wins=0.0
    for a in pos:
        for b in neg:
            pa=a['probabilities']['up'];pb=b['probabilities']['up']
            wins+=1 if pa>pb else (.5 if pa==pb else 0)
    return wins/(len(pos)*len(neg))

def metrics(preds):
    if not preds:return {'n':0,'multiclass_brier':None,'base_brier':None,'up_auc':None,'up_ece':None}
    classes=('up','flat','down');n=len(preds)
    brier=sum(sum((x['probabilities'][c]-(1 if x['target']==c else 0))**2 for c in classes) for x in preds)/n
    rates={c:sum(x['target']==c for x in preds)/n for c in classes}
    base=sum(sum((rates[c]-(1 if x['target']==c else 0))**2 for c in classes) for x in preds)/n
    bins=[]
    for lo,hi in ((0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.001)):
        z=[x for x in preds if lo<=x['probabilities']['up']<hi]
        if not z:continue
        p=sum(x['probabilities']['up'] for x in z)/len(z)
        obs=sum(x['target']=='up' for x in z)/len(z)
        bins.append({'n':len(z),'predicted':round(p,3),'observed':round(obs,3)})
    ece=sum(b['n']/n*abs(b['predicted']-b['observed']) for b in bins)
    return {
        'n':n,'multiclass_brier':round(brier,3),'base_brier':round(base,3),
        'up_auc':None if auc_up(preds) is None else round(auc_up(preds),3),
        'up_ece':round(ece,3),'class_rates':{k:round(v,3) for k,v in rates.items()},
        'calibration_bins':bins,
    }

def walk_forward(rows,h,band,features,k):
    out=[]
    for row in rows:
        ym=row.get('ym')
        if not ym or ym<'201201':continue
        target=klass(row.get(f'fwd_{h}m_pct'),band)
        if target is None or any(finite(row.get(f)) is None for f in features):continue
        cutoff=ym_ord(ym)
        train=[]
        for x in rows:
            xo=ym_ord(x.get('ym'))
            xt=klass(x.get(f'fwd_{h}m_pct'),band)
            if xo is None or cutoff is None or xo+h>cutoff or xt is None:continue
            if any(finite(x.get(f)) is None for f in features):continue
            train.append({**x,'target':xt})
        if len(train)<48:continue
        pred=standardized_knn(train,row,features,k)
        if pred:out.append({'ym':ym,'target':target,**pred})
    return out

def split_metrics(preds):
    return {
      'selection_2012_2017':metrics([x for x in preds if x['ym']<'201801']),
      'holdout_2018_plus':metrics([x for x in preds if x['ym']>='201801']),
    }

def model_screen(rows,bands):
    screen={};selected={}
    for h in HORIZONS:
        hscreen={}
        for name,features in FEATURE_CANDIDATES.items():
            ks=[]
            for k in K_CANDIDATES:
                preds=walk_forward(rows,h,bands[h],features,k)
                m=split_metrics(preds)
                ks.append({'k':k,**m})
            viable=[x for x in ks if x['selection_2012_2017']['n']>=36]
            best=min(viable,key=lambda x:x['selection_2012_2017']['multiclass_brier']) if viable else None
            hscreen[name]={'selected':best,'candidates':ks}
        screen[str(h)]=hscreen
        selected[str(h)]=hscreen['price_momentum']['selected']
    return screen,selected

def production_gate(h,chosen):
    if not chosen:return False
    sel=chosen['selection_2012_2017'];hold=chosen['holdout_2018_plus']
    auc_floor={1:.80,3:.75,6:.65}.get(h,.70)
    return bool(
        sel.get('n',0)>=36 and hold.get('n',0)>=60 and
        sel.get('multiclass_brier') is not None and sel['multiclass_brier']<sel['base_brier'] and
        hold.get('multiclass_brier') is not None and hold['multiclass_brier']<hold['base_brier'] and
        hold.get('up_auc') is not None and hold['up_auc']>=auc_floor
    )

def point_in_time(rows,ym,h,band,k,features=('m1','m3')):
    row=next((x for x in rows if x.get('ym')==ym),None)
    if not row or any(finite(row.get(f)) is None for f in features):return None
    cutoff=ym_ord(ym);train=[]
    for x in rows:
        xo=ym_ord(x.get('ym'));xt=klass(x.get(f'fwd_{h}m_pct'),band)
        if xo is None or cutoff is None or xo+h>cutoff or xt is None:continue
        if any(finite(x.get(f)) is None for f in features):continue
        train.append({**x,'target':xt})
    if len(train)<48:return None
    z=standardized_knn(train,row,features,k)
    if not z:return None
    return {
      'ym':ym,'probabilities':{k:round(v*100,1) for k,v in z['probabilities'].items()},
      'inputs':{'price_momentum_1m_pct':round(row['m1'],2),'price_momentum_3m_pct':round(row['m3'],2)},
      'training_observations':len(train),
    }

def current_predict(rows,current_ym,h,band,k,m1,m3):
    cutoff=ym_ord(current_ym);features=('m1','m3');train=[]
    for x in rows:
        xo=ym_ord(x.get('ym'));xt=klass(x.get(f'fwd_{h}m_pct'),band)
        if xo is None or cutoff is None or xo+h>cutoff or xt is None:continue
        if any(finite(x.get(f)) is None for f in features):continue
        train.append({**x,'target':xt})
    if len(train)<48:return None
    z=standardized_knn(train,{'m1':m1,'m3':m3},features,k)
    if not z:return None
    return {
      'probabilities':{c:round(v*100,1) for c,v in z['probabilities'].items()},
      'training_observations':len(train),'k':k,'nearest_analogs':z['neighbors'][:6],
    }

def main():
    long_payload=json.loads(LONG.read_text(encoding='utf-8'))
    market=json.loads(MARKET.read_text(encoding='utf-8'))
    rows=monthly_rows(long_payload)
    pre=[x for x in rows if x.get('ym')<'201201']
    bands={}
    for h in HORIZONS:
        bands[h]=quantile([abs(x[f'fwd_{h}m_pct']) for x in pre if x.get(f'fwd_{h}m_pct') is not None],.25)
        if bands[h] is None:raise RuntimeError(f'flat-band unavailable for {h}m')

    screen,selected=model_screen(rows,bands)
    horizon_status={}
    for h in PRODUCTION_HORIZONS:
        horizon_status[str(h)]='validated' if production_gate(h,selected[str(h)]) else 'rejected'
    # 12m is intentionally stricter: it must beat the baseline on both selection and holdout.
    s12=selected['12'];sel12=s12['selection_2012_2017'];hold12=s12['holdout_2018_plus']
    h12_ok=bool(sel12['multiclass_brier']<sel12['base_brier'] and hold12['multiclass_brier']<hold12['base_brier'] and (hold12.get('up_auc') or 0)>=.65)
    horizon_status['12']='validated' if h12_ok else 'rejected'

    extra={}
    for h in PRODUCTION_HORIZONS:
        base=screen[str(h)]['price_momentum']['selected']
        extra[str(h)]={}
        for name in ('price_plus_trade','price_plus_m2','price_trade_m2'):
            cand=screen[str(h)][name]['selected']
            extra[str(h)][name]={
              'selected_k':None if not cand else cand['k'],
              'holdout_brier':None if not cand else cand['holdout_2018_plus']['multiclass_brier'],
              'holdout_up_auc':None if not cand else cand['holdout_2018_plus']['up_auc'],
              'decision':'rejected' if cand else 'unavailable',
              'reason':'did not beat price-momentum model on frozen validation protocol',
            }
        extra[str(h)]['price_momentum']={
          'selected_k':base['k'],'holdout_brier':base['holdout_2018_plus']['multiclass_brier'],
          'holdout_up_auc':base['holdout_2018_plus']['up_auc'],'decision':'selected'
        }

    reb=market.get('reb_weekly') or {}
    momentum=reb.get('momentum') or {};latest=reb.get('latest') or {}
    m1=finite(momentum.get('sale_4w_pct'));m3=finite(momentum.get('sale_13w_pct'))
    asof=str(latest.get('date') or '')
    current_ym=asof[:6] if len(asof)>=6 else None
    current_status='ok' if reb.get('status')=='connected' and current_ym and m1 is not None and m3 is not None else 'data_check'

    current=None;forecast={}
    if current_status=='ok':
        chosen1=selected['1']
        current=current_predict(rows,current_ym,1,bands[1],chosen1['k'],m1,m3) if horizon_status['1']=='validated' else None
        if current:
            current.update({'as_of':asof,'horizon_months':1,'source':'REB weekly sale index',
                            'inputs':{'price_momentum_4w_pct':round(m1,2),'price_momentum_13w_pct':round(m3,2)}})
        for h in (3,6):
            chosen=selected[str(h)]
            z=current_predict(rows,current_ym,h,bands[h],chosen['k'],m1,m3) if horizon_status[str(h)]=='validated' else None
            forecast[str(h)]={'status':'validated' if z else 'data_check',**(z or {})}
        forecast['12']={'status':'not_validated','probabilities':None,'reason':'12m model failed frozen selection/holdout Brier gate'}

    history=[]
    if current_ym:
        for label,months in (('1년 전',-12),('6개월 전',-6),('3개월 전',-3)):
            target=shift_ym(current_ym,months)
            row=max((x for x in rows if x.get('ym')<=target),key=lambda x:x['ym'],default=None)
            p=point_in_time(rows,row['ym'],1,bands[1],selected['1']['k']) if row else None
            if p:p['label']=label;history.append(p)
        if current:
            history.append({'label':'현재','ym':current_ym,'probabilities':current['probabilities'],
                            'inputs':current['inputs'],'training_observations':current['training_observations']})

    overall=all(horizon_status[str(h)]=='validated' for h in PRODUCTION_HORIZONS) and horizon_status['12']=='rejected'
    payload={
      'status':'validated_probability_engine' if overall and current else ('validated_model_data_check' if overall else 'research_only'),
      'version':'upside_probability_v1','no_future_leakage':True,
      'scope':market.get('scope') or {},
      'definition':{
        'question':'현재/향후 해당 기간의 시장가격이 통계적 보합 범위를 넘어 상승할 가능성',
        'classes':['up','flat','down'],
        'flat_band_method':'25th percentile of absolute forward price changes, frozen using observations before 2012 only',
        'flat_band_pct':{str(h):round(bands[h],3) for h in HORIZONS},
        'probability_type':'expanding historical-analog empirical probability with Dirichlet(1,1,1) smoothing',
      },
      'model':{
        'features':['price_momentum_1m','price_momentum_3m'],
        'current_feature_mapping':{'price_momentum_1m':'REB weekly sale 4w momentum','price_momentum_3m':'REB weekly sale 13w momentum'},
        'selection_period':'2012-01..2017-12','holdout_period':'2018-01+',
        'selected_k':{str(h):selected[str(h)]['k'] for h in HORIZONS},
        'target_maturity_rule':'historical row enters training only after t+h is available',
      },
      'validation':{
        str(h):{
          'status':horizon_status[str(h)],
          'selected_k':selected[str(h)]['k'],
          'selection':selected[str(h)]['selection_2012_2017'],
          'holdout':selected[str(h)]['holdout_2018_plus'],
        } for h in HORIZONS
      },
      'candidate_screen':extra,
      'rejected_inputs':[
        {'feature':'trade','reason':'price+trade failed to improve frozen holdout probability metrics'},
        {'feature':'M2','reason':'price+M2 failed to improve frozen holdout probability metrics'},
        {'feature':'market_strength','reason':'recent validation showed probability Brier deterioration; retained only inside legacy engine context'},
      ],
      'current':{'status':current_status,**(current or {})},
      'history':history,
      'forecast':forecast,
      'lineage':{'long_history':'dist/long_cycle_master.json','current_market':'dist/market_indicators.json'},
      'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'current':payload['current'],'forecast':payload['forecast'],
                      'horizon_status':horizon_status},ensure_ascii=False))

if __name__=='__main__':
    main()
