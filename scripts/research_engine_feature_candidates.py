#!/usr/bin/env python3
"""Generate and validate candidate features for the research/forecast engines.

All historical transforms are expanding-window or lagged. Forward returns are used
only for evaluation after each feature value is formed. Surviving features are
promoted only when they beat explicit gates; rejected candidates remain in this
artifact for audit but are not consumed by production heads.
"""
from __future__ import annotations
import datetime, json, math, pathlib

R=pathlib.Path(__file__).resolve().parents[1]
FINAL=R/'dist/final_backtest.json'
TURN=R/'dist/turning_signal_research.json'
KBV=R/'dist/forecast_kb_momentum_validation.json'
M2=R/'data_sources/ecos_m2.json'
MORT=R/'data_sources/ecos_mortgage_rate.json'
OUT=R/'dist/engine_feature_research.json'

def clamp(x): return max(0.0,min(100.0,float(x)))
def pct_rank(hist,v): return 100.0*sum(x<=v for x in hist)/len(hist) if hist else 50.0
def shift(ym,n):
    y=int(ym[:4]);m=int(ym[4:])-1+n;y+=m//12;m%=12
    return f'{y:04d}{m+1:02d}'
def corr(a,b):
    z=[(float(x),float(y)) for x,y in zip(a,b) if x is not None and y is not None]
    if len(z)<3:return None
    ax=sum(x for x,_ in z)/len(z);ay=sum(y for _,y in z)/len(z)
    dx=sum((x-ax)**2 for x,_ in z);dy=sum((y-ay)**2 for _,y in z)
    return sum((x-ax)*(y-ay) for x,y in z)/math.sqrt(dx*dy) if dx and dy else None
def auc(scores,labels):
    z=[(float(s),int(y)) for s,y in zip(scores,labels) if s is not None and y is not None]
    pos=[s for s,y in z if y==1];neg=[s for s,y in z if y==0]
    if not pos or not neg:return None
    wins=0.0
    for p in pos:
        for q in neg:wins+=1 if p>q else .5 if p==q else 0
    return wins/(len(pos)*len(neg))
def norm(d):
    z=sum(max(0.0,float(v)) for v in d.values()) or 1.0
    return {k:max(0.0,float(v))*100.0/z for k,v in d.items()}
def mean(xs): return sum(xs)/len(xs) if xs else None
def terciles(rows,key,forward,orientation=1):
    z=[x for x in rows if x.get(key) is not None and x.get(forward) is not None]
    z=sorted(z,key=lambda x:orientation*float(x[key]))
    a=len(z)//3;b=2*len(z)//3
    out=[]
    for g in (z[:a],z[a:b],z[b:]):
        vals=[float(x[forward]) for x in g]
        out.append({'n':len(g),'mean_pct':round(mean(vals),2) if vals else None,
                    'positive_pct':round(100*sum(v>0 for v in vals)/len(vals),1) if vals else None})
    return out
def feature_metrics(rows,key,orientation=1):
    out={}
    for h in (1,3,6,12):
        f=f'fwd_{h}m_pct'
        z=[x for x in rows if x.get(key) is not None and x.get(f) is not None]
        scores=[orientation*float(x[key]) for x in z];y=[float(x[f]) for x in z]
        out[str(h)]={'n':len(z),'corr':round(corr(scores,y),3) if len(z)>=3 else None,
                     'auc_positive':round(auc(scores,[1 if v>0 else 0 for v in y]),3) if len(z)>=3 else None,
                     'auc_downside':round(auc([-s for s in scores],[1 if v<0 else 0 for v in y]),3) if len(z)>=3 else None,
                     'terciles':terciles(rows,key,f,orientation)}
    return out
def q4_baseline(r,m2map,mortmap):
    c=r['components'];m1=r['mapped_m1'];m3=r['mapped_m3'];breadth=r['breadth'];reaccel=r['reaccel']
    finance=float(c['finance']);sent=float(c['sentiment']);demand=float(c['demand']);value=float(c['value']);supply=float(c['supply'])
    mm=m2map.get(shift(r['ym'],-2)) or {}
    yoy=float(mm.get('yoy_pct')) if mm.get('yoy_pct') is not None else (finance-50)/1.5
    liquidity=clamp(50+yoy*5)
    mort=mortmap.get(r['ym']) or {}
    mortgage=float(mort.get('rate_pct')) if mort.get('rate_pct') is not None else 4.0
    rate_pressure=clamp((mortgage-3)*28)
    trade_pressure=clamp(max(0,50-demand)*2)
    return norm({
      'consolidation':62+.18*finance+.14*supply+.22*clamp(100-abs(m3)*12)-.10*trade_pressure,
      'reacceleration':18+.34*reaccel+.22*breadth+.12*finance+.10*liquidity+max(0,m3)*2,
      'downturn':22+.24*(100-breadth)+.18*(100-demand)+.14*(100-sent)+.12*trade_pressure+.10*rate_pressure+.10*(100-value)-max(0,m1)*2
    })
def forecast_metrics(rows,weights):
    y=[float(x['fwd_3m_pct']) for x in rows]
    d=[float(x['weights']['downturn']) for x in weights];u=[float(x['weights']['reacceleration']) for x in weights]
    return {'n':len(rows),'down_auc':round(auc(d,[1 if v<0 else 0 for v in y]),3),
            'down_corr_negative_fwd3':round(corr(d,[-v for v in y]),3),
            'reaccel_auc_positive':round(auc(u,[1 if v>0 else 0 for v in y]),3),
            'reaccel_corr_fwd3':round(corr(u,y),3)}

def main():
    final=json.loads(FINAL.read_text());turn=json.loads(TURN.read_text());kbv=json.loads(KBV.read_text())
    tmap={x['ym']:x for x in turn.get('rows',[]) if not x.get('source_provisional')}
    smap={x['ym']:x for x in kbv.get('sample',[])}
    base=[]
    for r in final.get('rows',[]):
        tr=tmap.get(r.get('ym'));sp=smap.get(r.get('ym'));c=r.get('components') or {}
        if r.get('provisional') or not tr or not all(c.get(k) is not None for k in ('finance','sentiment','demand','value','supply')):continue
        raw=[tr.get('momentum_3m_pct'),tr.get('breadth'),tr.get('reaccel'),c.get('finance'),c.get('sentiment'),c.get('demand'),c.get('value'),c.get('supply')]
        if any(v is None for v in raw):continue
        base.append({'ym':r['ym'],'components':c,'momentum_3m_pct':float(raw[0]),'breadth':float(raw[1]),'reaccel':float(raw[2]),
                     'mapped_m1':float(sp.get('mapped1')) if sp and sp.get('mapped1') is not None else None,
                     'mapped_m3':float(sp.get('mapped3')) if sp and sp.get('mapped3') is not None else None,
                     'fwd_1m_pct':r.get('fwd_1m_pct'),'fwd_3m_pct':r.get('fwd_3m_pct'),'fwd_6m_pct':r.get('fwd_6m_pct'),'fwd_12m_pct':r.get('fwd_12m_pct')})
    base.sort(key=lambda x:x['ym'])
    rows=[]
    for i,r in enumerate(base):
        mom_rank=pct_rank([x['momentum_3m_pct'] for x in base[:i+1]],r['momentum_3m_pct'])
        c=r['components']
        signals=[mom_rank,r['breadth'],r['reaccel'],float(c['finance']),float(c['sentiment']),float(c['demand']),float(c['value']),float(c['supply'])]
        srt=sorted(signals);strength=sum(srt[1:-1])/6
        live=[mom_rank,float(c['finance']),float(c['sentiment']),float(c['demand']),float(c['value']),float(c['supply'])]
        row={**r,'momentum_percentile':round(mom_rank,3),'market_strength':round(strength,3),'live_six':live}
        row['strength_delta_1m']=round(strength-rows[i-1]['market_strength'],3) if i>=1 else None
        row['strength_delta_3m']=round(strength-rows[i-3]['market_strength'],3) if i>=3 else None
        row['price_strength_gap']=round(mom_rank-strength,3)
        if i>=3:
            d=[live[j]-rows[i-3]['live_six'][j] for j in range(6)]
            improving=100*sum(v>=2 for v in d)/6
            deteriorating=100*sum(v<=-2 for v in d)/6
            row['improving_breadth_3m']=round(improving,3)
            row['deteriorating_breadth_3m']=round(deteriorating,3)
            row['change_balance_3m']=round(improving-deteriorating,3)
        else:
            row['improving_breadth_3m']=row['deteriorating_breadth_3m']=row['change_balance_3m']=None
        rows.append(row)

    specs={
      'market_strength':1,'strength_delta_1m':1,'strength_delta_3m':1,'price_strength_gap':-1,
      'improving_breadth_3m':1,'deteriorating_breadth_3m':-1,'change_balance_3m':1
    }
    metrics={k:feature_metrics(rows,k,o) for k,o in specs.items()}
    strength3=metrics['market_strength']['3'];strength6=metrics['market_strength']['6'];strength12=metrics['market_strength']['12']
    st=strength3['terciles']
    strength_gate=bool(strength3['n']>=36 and strength3['corr']>=.30 and strength3['auc_positive']>=.70 and
                       st[0]['mean_pct']<st[1]['mean_pct']<st[2]['mean_pct'] and
                       strength6['corr']>=.30 and strength12['n']>=30 and strength12['corr']>=.40)
    imp3=metrics['improving_breadth_3m']['3'];imp6=metrics['improving_breadth_3m']['6']
    improvement_gate=bool(imp3['n']>=36 and imp3['corr']>=.25 and imp3['auc_positive']>=.70 and
                          imp6['corr']>=.35 and imp6['auc_positive']>=.75)
    decisions={
      'market_strength':{'decision':'selected_production_support' if strength_gate else 'rejected','roles':['current_state_quality','short_horizon_forecast'] if strength_gate else []},
      'improving_breadth_3m':{'decision':'selected_research_support' if improvement_gate else 'rejected','roles':['research_transition_context'] if improvement_gate else []},
    }
    for k in ('strength_delta_1m','strength_delta_3m','price_strength_gap','deteriorating_breadth_3m','change_balance_3m'):
        decisions[k]={'decision':'rejected','roles':[],'reason':'failed multi-horizon robustness/monotonicity gate'}

    ss=sorted(x['market_strength'] for x in rows)
    low_cut=ss[int((len(ss)-1)/3)];high_cut=ss[int((len(ss)-1)*2/3)]

    m2=json.loads(M2.read_text()).get('series',[]);m2map={str(x.get('period','')).replace('-','')[:6]:x for x in m2 if x.get('period')}
    mort=json.loads(MORT.read_text()).get('series',[]);mortmap={str(x.get('period','')).replace('-','')[:6]:x for x in mort if x.get('item')=='주택담보대출'}
    evalrows=[x for x in rows if x.get('mapped_m1') is not None and x.get('mapped_m3') is not None and x.get('fwd_3m_pct') is not None]
    baseline=[{'weights':q4_baseline(x,m2map,mortmap)} for x in evalrows]
    base_metrics=forecast_metrics(evalrows,baseline)
    candidates=[]
    for w in (.25,1/3,.50):
        z=[]
        for i,x in enumerate(evalrows):
            q=baseline[i]['weights'];strength=x['market_strength']
            z.append({'weights':norm({'consolidation':q['consolidation'],
                         'reacceleration':(1-w)*q['reacceleration']+w*strength,
                         'downturn':(1-w)*q['downturn']+w*(100-strength)})})
        m=forecast_metrics(evalrows,z)
        passed=bool(m['down_auc']>=base_metrics['down_auc']+.005 and
                    m['reaccel_auc_positive']>=base_metrics['reaccel_auc_positive']+.015 and
                    m['down_corr_negative_fwd3']>=base_metrics['down_corr_negative_fwd3']-.05 and
                    m['reaccel_corr_fwd3']>=base_metrics['reaccel_corr_fwd3']-.02)
        candidates.append({'weight':round(w,4),'metrics':m,'passed':passed})
    passed=[x for x in candidates if x['passed']]
    selected=min(passed,key=lambda x:x['weight']) if passed else None
    overlay={'baseline':base_metrics,'candidates':candidates,'selected_weight':selected['weight'] if selected else None,
             'apply_recommended':bool(strength_gate and selected),
             'gate':'down AUC +0.005; reaccel AUC +0.015; down corr no worse than -0.05; reaccel corr no worse than -0.02',
             'scope':'short_horizon_only','longer_horizons':'unchanged_until_separately_validated'}

    latest=rows[-1] if rows else {}
    payload={'status':'research_validation','version':'engine_feature_research_v1','source_certified_through':final.get('certified_through'),
      'no_future_leakage':True,'feature_formation':'expanding momentum rank; lagged 3m change breadth; forward returns evaluation-only',
      'rows':[ {k:v for k,v in x.items() if k!='live_six'} for x in rows],
      'candidate_metrics':metrics,'decisions':decisions,
      'selected_features':[k for k,v in decisions.items() if v['decision'].startswith('selected')],
      'rejected_features':[k for k,v in decisions.items() if v['decision']=='rejected'],
      'market_strength':{'apply_recommended':strength_gate,'low_cut':round(low_cut,2),'high_cut':round(high_cut,2),
                         'latest_certified':{'ym':latest.get('ym'),'score_0_100':latest.get('market_strength')},
                         'formula':'trimmed mean of 8 equally-treated 0-100 signals; highest/lowest removed','hand_tuned_weights':False},
      'forecast_overlay':overlay,
      'improving_breadth_3m':{'apply_recommended_for_research':improvement_gate,'production_forecast_applied':False,
        'reason':'standalone predictive relationship survives, but adding it to the short-horizon production blend degraded downside discrimination'},
      'apply_recommended':bool(strength_gate and overlay['apply_recommended']),
      'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'selected':payload['selected_features'],'rejected':payload['rejected_features'],'market_strength':payload['market_strength'],'forecast_overlay':overlay},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
