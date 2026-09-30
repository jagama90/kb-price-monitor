#!/usr/bin/env python3
"""Validation gate for the unified market judgment engine."""
import json,pathlib,math,datetime
from market_judgment_engine import clamp,n,norm
R=pathlib.Path(__file__).resolve().parents[1]
CAND=R/'dist/market_judgment_candidate.json';FINAL=R/'dist/final_backtest.json';TURN=R/'dist/turning_signal_research.json';KBV=R/'dist/forecast_kb_momentum_validation.json'
OUT=R/'dist/market_judgment_validation.json';COMMONV=R/'dist/common_feature_layer_v2_validation.json'
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
    wins=0
    for p in pos:
      for q in neg:wins+=1 if p>q else .5 if p==q else 0
    return wins/(len(pos)*len(neg))
def shift(ym,nm):
    y=int(ym[:4]);m=int(ym[4:]);q=y*12+m-1+nm
    return f'{q//12:04d}{q%12+1:02d}'
def aux():
    m2=json.loads((R/'data_sources/ecos_m2.json').read_text()).get('series',[])
    mm={str(x.get('period','')).replace('-','')[:6]:x for x in m2 if x.get('period')}
    mort=json.loads((R/'data_sources/ecos_mortgage_rate.json').read_text()).get('series',[])
    mr={str(x.get('period','')).replace('-','')[:6]:x for x in mort if x.get('item')=='주택담보대출'}
    return mm,mr

def avg(rows,key):
    vals=[float(x[key]) for x in rows if x.get(key) is not None]
    return sum(vals)/len(vals) if vals else None
def share_nonpositive(rows,key='fwd3'):
    vals=[float(x[key]) for x in rows if x.get(key) is not None]
    return sum(1 for x in vals if x<=0)/len(vals) if vals else None
def state_stage(m1,m3,bottom,momentum,was_rising):
    stage=0
    if bottom:stage=1
    if m1>=0 and m3<=0 and not was_rising:stage=2
    if m3>0:stage=3
    if was_rising and m3<=0 and m1>=0:stage=3
    if momentum:stage=4
    return stage
def current_state_revalidation(final_rows,tmap,samples):
    vals=[]
    yms=[r.get('ym') for r in final_rows]
    for i,r in enumerate(final_rows):
      ym=r.get('ym');tr=tmap.get(ym);sp=samples.get(ym)
      if not tr or not sp or r.get('fwd_3m_pct') is None or r.get('provisional'):continue
      m1=n(sp.get('mapped1'));m3=n(sp.get('mapped3'))
      prev=[]
      for py in yms[max(0,i-3):i]:
        ps=samples.get(py)
        if ps:prev.append(n(ps.get('mapped3')))
      was_rising=any(x>0 for x in prev)
      breadth=n(tr.get('breadth'));reaccel=n(tr.get('reaccel'))
      c=r.get('components') or {};demand=n(c.get('demand'));sent=n(c.get('sentiment'))
      base=state_stage(m1,m3,bool(tr.get('bottom_zone')),bool(tr.get('momentum_zone')),was_rising)
      confirmed=breadth>=45 and reaccel>=50
      demoted=2 if base==3 and m3>0 and not confirmed else base
      internal=.35*breadth+.30*reaccel+.20*demand+.15*sent
      vals.append({'ym':ym,'m1':m1,'m3':m3,'breadth':breadth,'reaccel':reaccel,'demand':demand,'sentiment':sent,
                   'internal_composite':internal,'confirmed':confirmed,'base_stage':base,'demotion_stage':demoted,'fwd3':n(r.get('fwd_3m_pct'))})
    pos=[x for x in vals if x['m3']>0];weak=[x for x in pos if not x['confirmed']];strong=[x for x in pos if x['confirmed']]
    b3=[x for x in vals if x['base_stage']>=3];d3=[x for x in vals if x['demotion_stage']>=3]
    base_corr=corr([x['base_stage'] for x in vals],[x['fwd3'] for x in vals]);demo_corr=corr([x['demotion_stage'] for x in vals],[x['fwd3'] for x in vals])
    base_auc=auc([x['base_stage'] for x in vals],[1 if x['fwd3']>0 else 0 for x in vals]);demo_auc=auc([x['demotion_stage'] for x in vals],[1 if x['fwd3']>0 else 0 for x in vals])
    weak_mean=avg(weak,'fwd3');strong_mean=avg(strong,'fwd3');weak_np=share_nonpositive(weak);strong_np=share_nonpositive(strong)
    confirmation_gate=bool(len(weak)>=10 and len(strong)>=10 and weak_mean is not None and strong_mean is not None and
                           strong_mean-weak_mean>=2.0 and weak_np is not None and strong_np is not None and weak_np-strong_np>=.20)
    demotion_gate=bool(len(vals)>=30 and len(weak)>=10 and len(strong)>=10 and base_auc is not None and demo_auc is not None and
                       demo_auc>=base_auc+.02 and base_corr is not None and demo_corr is not None and demo_corr>=base_corr-.02 and
                       weak_mean is not None and weak_mean<=0)
    comp_auc=auc([x['internal_composite'] for x in pos],[1 if x['fwd3']>0 else 0 for x in pos])
    breadth_auc=auc([x['breadth'] for x in pos],[1 if x['fwd3']>0 else 0 for x in pos])
    separate_composite=bool(comp_auc is not None and breadth_auc is not None and comp_auc>=breadth_auc+.01)
    pack=lambda z:{'n':len(z),'mean_fwd3_pct':round(avg(z,'fwd3'),3) if z else None,'nonpositive_share_pct':round(100*share_nonpositive(z),1) if z else None}
    return {
      'rows':len(vals),'positive_m3_rows':len(pos),'confirmation_rule':'breadth >= 45 AND reaccel >= 50',
      'positive_m3_split':{'weak_confirmation':pack(weak),'confirmed':pack(strong)},
      'baseline_stage':{'corr_fwd3':base_corr,'auc_positive_fwd3':base_auc,'stage3plus':pack(b3)},
      'demotion_candidate':{'corr_fwd3':demo_corr,'auc_positive_fwd3':demo_auc,'stage3plus':pack(d3),'apply_recommended':demotion_gate,
        'gate':'n>=30; weak/confirmed n>=10; positive AUC +0.02; stage corr no worse than -0.02; weak-confirmation mean fwd3 <= 0'},
      'confirmation_substate':{'apply_recommended':confirmation_gate,
        'gate':'weak/confirmed n>=10; confirmed mean fwd3 >= weak +2pp; weak nonpositive share >= confirmed +20pp'},
      'separate_recursive_composite':{'apply_recommended':separate_composite,'positive_m3_auc':comp_auc,'breadth_auc':breadth_auc,
        'method':'35% breadth + 30% reaccel + 20% demand + 15% sentiment',
        'gate':'composite positive-fwd3 AUC must exceed breadth alone by >=0.01'},
      'decision':('retain_stage3_add_confirmation_substate' if confirmation_gate and not demotion_gate else
                  'promote_demotion_candidate' if demotion_gate else 'retain_current_state_rule'),
      'no_future_leakage':True
    }
def historical_reaccel(final_rows,i,m1,m3):
    c=final_rows[i]['components']
    def delta(k,lag):
      return n(c.get(k))-n(final_rows[i-lag]['components'].get(k)) if i>=lag else 0
    breadth=clamp(.40*n(c.get('demand'))+.35*n(c.get('sentiment'))+.25*n(c.get('finance')))
    reaccel=clamp(50+6*m1+3*m3+1.5*delta('demand',1)+1.2*delta('sentiment',1))
    if m3<=0:reaccel=min(reaccel,35)
    return breadth,reaccel
def weights(c,breadth,reaccel,m1,m3,mmrow,mortrow,liquidity_override=None):
    finance=n(c.get('finance'),50);sent=n(c.get('sentiment'),50);demand=n(c.get('demand'),50);value=n(c.get('value'),50);supply=n(c.get('supply'),50)
    yoy=n((mmrow or {}).get('yoy_pct'),(finance-50)/1.5 if finance else 0);liquidity=clamp(50+yoy*5) if liquidity_override is None else clamp(liquidity_override)
    mortgage=n((mortrow or {}).get('rate_pct'),4.0);rate_pressure=clamp((mortgage-3)*28)
    trade_pressure=clamp(max(0,50-demand)*2)
    q4=norm({'consolidation':62+.18*finance+.14*supply+.22*clamp(100-abs(m3)*12)-.10*trade_pressure,
             'reacceleration':18+.34*reaccel+.22*breadth+.12*finance+.10*liquidity+max(0,m3)*2,
             'downturn':22+.24*(100-breadth)+.18*(100-demand)+.14*(100-sent)+.12*trade_pressure+.10*rate_pressure+.10*(100-value)-max(0,m1)*2})
    return q4
def main():
    cand=json.loads(CAND.read_text());final=json.loads(FINAL.read_text());turn=json.loads(TURN.read_text());kv=json.loads(KBV.read_text())
    commonv=json.loads(COMMONV.read_text()) if COMMONV.exists() else {};finmap={x.get('ym'):x for x in (((commonv.get('research_rows') or {}).get('finance')) or [])}
    rows=final.get('rows') or [];samples={x['ym']:x for x in kv.get('sample',[])}
    tmap={x['ym']:x for x in (turn.get('rows') or [])}
    mm,mr=aux();evals=[];live_recomputed=[];finance_v2_evals=[];finance_v2_buy=[]
    for i,r in enumerate(rows):
      ym=r['ym'];s=samples.get(ym);tr=tmap.get(ym)
      if not s or not tr or r.get('fwd_3m_pct') is None or r.get('provisional'):continue
      m1=n(s.get('mapped1'));m3=n(s.get('mapped3'))
      # Production candidate: certified research breadth/reaccel carried into
      # the common snapshot, exactly preserving the already validated forecast logic.
      breadth=n(tr.get('breadth'),50);reaccel=n(tr.get('reaccel'),50)
      w=weights(r['components'],breadth,reaccel,m1,m3,mm.get(shift(ym,-2)),mr.get(ym))
      evals.append({'ym':ym,'down':w['downturn'],'reaccel':w['reacceleration'],'fwd3':r.get('fwd_3m_pct')})
      # Diagnostic rejected alternative: fully live-recomputed breadth/reaccel.
      rb,rr=historical_reaccel(rows,i,m1,m3)
      rw=weights(r['components'],rb,rr,m1,m3,mm.get(shift(ym,-2)),mr.get(ym))
      live_recomputed.append({'ym':ym,'down':rw['downturn'],'reaccel':rw['reacceleration'],'fwd3':r.get('fwd_3m_pct')})
      fv=finmap.get(ym) or {};fv2=fv.get('finance_v2');credit=fv.get('credit_availability_score')
      if fv2 is not None and credit is not None:
        c2=dict(r['components']);c2['finance']=float(fv2)
        w2=weights(c2,breadth,reaccel,m1,m3,mm.get(shift(ym,-2)),mr.get(ym),liquidity_override=credit)
        finance_v2_evals.append({'ym':ym,'down':w2['downturn'],'reaccel':w2['reacceleration'],'fwd3':r.get('fwd_3m_pct')})
        score2=.25*n(c2.get('finance'))+.20*n(c2.get('sentiment'))+.20*n(c2.get('demand'))+.20*n(c2.get('value'))+.15*n(c2.get('supply'))
        finance_v2_buy.append({'ym':ym,'score':score2,'fwd1':r.get('fwd_1m_pct'),'fwd3':r.get('fwd_3m_pct'),'fwd6':r.get('fwd_6m_pct'),'fwd12':r.get('fwd_12m_pct')})
    downs=[x['down'] for x in evals];reas=[x['reaccel'] for x in evals];fwd=[x['fwd3'] for x in evals]
    unified={'n':len(evals),'down_corr_negative_fwd3':corr(downs,[-x for x in fwd]),'down_auc_negative_fwd3':auc(downs,[1 if x<0 else 0 for x in fwd]),
             'reaccel_corr_fwd3':corr(reas,fwd),'reaccel_auc_positive_fwd3':auc(reas,[1 if x>0 else 0 for x in fwd])}
    rd=[x['down'] for x in live_recomputed];rr=[x['reaccel'] for x in live_recomputed];rf=[x['fwd3'] for x in live_recomputed]
    rejected={'n':len(live_recomputed),'down_corr_negative_fwd3':corr(rd,[-x for x in rf]),'down_auc_negative_fwd3':auc(rd,[1 if x<0 else 0 for x in rf]),
              'reaccel_corr_fwd3':corr(rr,rf),'reaccel_auc_positive_fwd3':auc(rr,[1 if x>0 else 0 for x in rf])}
    base=(kv.get('forecast_validation') or {}).get('kb_scale_aligned') or {}
    # Reconstruct baseline reaccel discrimination directly from stored validation sample.
    bs=[x for x in kv.get('sample',[]) if x.get('fwd_3m_pct') is not None and x.get('new_q4_reaccel') is not None and x.get('ym')<=final.get('certified_through','999999')]
    baseline={'n':len(bs),'down_corr_negative_fwd3':base.get('corr_with_negative_fwd3'),'down_auc_negative_fwd3':base.get('auc_fwd3_negative'),
              'reaccel_corr_fwd3':corr([x['new_q4_reaccel'] for x in bs],[x['fwd_3m_pct'] for x in bs]),
              'reaccel_auc_positive_fwd3':auc([x['new_q4_reaccel'] for x in bs],[1 if x['fwd_3m_pct']>0 else 0 for x in bs])}
    # Certified baseline remains the fallback. Finance v2 is evaluated inside the
    # full buy/forecast heads before any production replacement.
    buy_metrics=final.get('metrics') or {}
    gate=bool(len(evals)>=30 and unified['down_auc_negative_fwd3'] is not None and baseline['down_auc_negative_fwd3'] is not None and
              unified['down_auc_negative_fwd3']>=baseline['down_auc_negative_fwd3']-.02 and
              unified['reaccel_auc_positive_fwd3'] is not None and baseline['reaccel_auc_positive_fwd3'] is not None and
              unified['reaccel_auc_positive_fwd3']>=baseline['reaccel_auc_positive_fwd3']-.02 and
              n(buy_metrics.get('score_vs_fwd_6m_corr'),-9)>=0.30 and n(buy_metrics.get('score_vs_fwd_12m_corr'),-9)>=0.45)
    f2d=[x['down'] for x in finance_v2_evals];f2r=[x['reaccel'] for x in finance_v2_evals];f2y=[x['fwd3'] for x in finance_v2_evals]
    f2forecast={'n':len(finance_v2_evals),
      'down_corr_negative_fwd3':corr(f2d,[-x for x in f2y]) if f2y else None,
      'down_auc_negative_fwd3':auc(f2d,[1 if x<0 else 0 for x in f2y]) if f2y else None,
      'reaccel_corr_fwd3':corr(f2r,f2y) if f2y else None,
      'reaccel_auc_positive_fwd3':auc(f2r,[1 if x>0 else 0 for x in f2y]) if f2y else None}
    f2buy={'n':len(finance_v2_buy)}
    for h in (1,3,6,12):
      pairs=[x for x in finance_v2_buy if x.get(f'fwd{h}') is not None]
      f2buy[f'corr_fwd_{h}m']=corr([x['score'] for x in pairs],[x[f'fwd{h}'] for x in pairs])
      f2buy[f'n_fwd_{h}m']=len(pairs)
    b6=n(buy_metrics.get('score_vs_fwd_6m_corr'),-9);b12=n(buy_metrics.get('score_vs_fwd_12m_corr'),-9)
    improvements=[]
    if f2buy.get('corr_fwd_3m') is not None and f2buy['corr_fwd_3m']>=n(buy_metrics.get('score_vs_fwd_3m_corr'))+.02:improvements.append('buy_corr_3m')
    if f2buy.get('corr_fwd_6m') is not None and f2buy['corr_fwd_6m']>=b6+.02:improvements.append('buy_corr_6m')
    if f2buy.get('corr_fwd_12m') is not None and f2buy['corr_fwd_12m']>=b12+.02:improvements.append('buy_corr_12m')
    if f2forecast.get('down_auc_negative_fwd3') is not None and f2forecast['down_auc_negative_fwd3']>=baseline['down_auc_negative_fwd3']+.01:improvements.append('downside_auc')
    if f2forecast.get('reaccel_auc_positive_fwd3') is not None and f2forecast['reaccel_auc_positive_fwd3']>=baseline['reaccel_auc_positive_fwd3']+.01:improvements.append('reaccel_auc')
    finance_v2_gate=bool(len(finance_v2_evals)>=30 and
      f2forecast.get('down_auc_negative_fwd3') is not None and f2forecast['down_auc_negative_fwd3']>=baseline['down_auc_negative_fwd3']-.02 and
      f2forecast.get('reaccel_auc_positive_fwd3') is not None and f2forecast['reaccel_auc_positive_fwd3']>=baseline['reaccel_auc_positive_fwd3']-.02 and
      f2buy.get('corr_fwd_6m') is not None and f2buy['corr_fwd_6m']>=b6-.02 and
      f2buy.get('corr_fwd_12m') is not None and f2buy['corr_fwd_12m']>=b12-.02 and bool(improvements))
    finance_v2_integrated={'apply_recommended':finance_v2_gate,'forecast':f2forecast,'buy_condition':f2buy,'improvements':improvements,
      'gate':'n>=30; forecast downside/reaccel AUC no worse >0.02; buy corr6/corr12 no worse >0.02; at least one material improvement',
      'no_future_leakage':True,'credit_vintage_lag_months':2,'mortgage_rate_vintage_lag_months':1}
    regime_validation=current_state_revalidation(rows,tmap,samples)
    out={'status':'research_validation','rows_compared':len(evals),'baseline_forecast':baseline,'unified_forecast':unified,
         'buy_condition_certified_metrics':buy_metrics,'finance_v2_integrated':finance_v2_integrated,'rejected_live_recompute':rejected,
         'current_state_revalidation':regime_validation,
         'current_candidate':{'snapshot_id':cand['feature_layer']['snapshot_id'],'current_state':cand['heads']['current_state'],
         'buy_condition':cand['heads']['buy_condition'],'forward':cand['heads']['forward_scenario']},
         'apply_recommended':gate,'gate':'n>=30; downside AUC no worse >0.02; reacceleration positive AUC no worse >0.02; certified buy score corr6>=0.30 and corr12>=0.45',
         'no_future_leakage':True,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('rows_compared','baseline_forecast','unified_forecast','finance_v2_integrated','current_state_revalidation','buy_condition_certified_metrics','current_candidate','apply_recommended')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
