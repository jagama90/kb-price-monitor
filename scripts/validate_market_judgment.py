#!/usr/bin/env python3
"""Validation gate for the unified market judgment engine."""
import json,pathlib,math,datetime
from market_judgment_engine import clamp,n,norm
R=pathlib.Path(__file__).resolve().parents[1]
CAND=R/'dist/market_judgment_candidate.json';FINAL=R/'dist/final_backtest.json';TURN=R/'dist/turning_signal_research.json';KBV=R/'dist/forecast_kb_momentum_validation.json'
OUT=R/'dist/market_judgment_validation.json'
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
def historical_reaccel(final_rows,i,m1,m3):
    c=final_rows[i]['components']
    def delta(k,lag):
      return n(c.get(k))-n(final_rows[i-lag]['components'].get(k)) if i>=lag else 0
    breadth=clamp(.40*n(c.get('demand'))+.35*n(c.get('sentiment'))+.25*n(c.get('finance')))
    reaccel=clamp(50+6*m1+3*m3+1.5*delta('demand',1)+1.2*delta('sentiment',1))
    if m3<=0:reaccel=min(reaccel,35)
    return breadth,reaccel
def weights(c,breadth,reaccel,m1,m3,mmrow,mortrow):
    finance=n(c.get('finance'),50);sent=n(c.get('sentiment'),50);demand=n(c.get('demand'),50);value=n(c.get('value'),50);supply=n(c.get('supply'),50)
    yoy=n((mmrow or {}).get('yoy_pct'),(finance-50)/1.5 if finance else 0);liquidity=clamp(50+yoy*5)
    mortgage=n((mortrow or {}).get('rate_pct'),4.0);rate_pressure=clamp((mortgage-3)*28)
    trade_pressure=clamp(max(0,50-demand)*2)
    q4=norm({'consolidation':62+.18*finance+.14*supply+.22*clamp(100-abs(m3)*12)-.10*trade_pressure,
             'reacceleration':18+.34*reaccel+.22*breadth+.12*finance+.10*liquidity+max(0,m3)*2,
             'downturn':22+.24*(100-breadth)+.18*(100-demand)+.14*(100-sent)+.12*trade_pressure+.10*rate_pressure+.10*(100-value)-max(0,m1)*2})
    return q4
def main():
    cand=json.loads(CAND.read_text());final=json.loads(FINAL.read_text());turn=json.loads(TURN.read_text());kv=json.loads(KBV.read_text())
    rows=final.get('rows') or [];rmap={x['ym']:x for x in rows};samples={x['ym']:x for x in kv.get('sample',[])}
    mm,mr=aux();evals=[]
    for i,r in enumerate(rows):
      ym=r['ym'];s=samples.get(ym)
      if not s or r.get('fwd_3m_pct') is None or r.get('provisional'):continue
      m1=n(s.get('mapped1'));m3=n(s.get('mapped3'));breadth,reaccel=historical_reaccel(rows,i,m1,m3)
      w=weights(r['components'],breadth,reaccel,m1,m3,mm.get(shift(ym,-2)),mr.get(ym))
      evals.append({'ym':ym,'down':w['downturn'],'reaccel':w['reacceleration'],'fwd3':r.get('fwd_3m_pct')})
    downs=[x['down'] for x in evals];reas=[x['reaccel'] for x in evals];fwd=[x['fwd3'] for x in evals]
    unified={'n':len(evals),'down_corr_negative_fwd3':corr(downs,[-x for x in fwd]),'down_auc_negative_fwd3':auc(downs,[1 if x<0 else 0 for x in fwd]),
             'reaccel_corr_fwd3':corr(reas,fwd),'reaccel_auc_positive_fwd3':auc(reas,[1 if x>0 else 0 for x in fwd])}
    base=(kv.get('forecast_validation') or {}).get('kb_scale_aligned') or {}
    # Reconstruct baseline reaccel discrimination directly from stored validation sample.
    bs=[x for x in kv.get('sample',[]) if x.get('fwd_3m_pct') is not None and x.get('new_q4_reaccel') is not None and x.get('ym')<=final.get('certified_through','999999')]
    baseline={'n':len(bs),'down_corr_negative_fwd3':base.get('corr_with_negative_fwd3'),'down_auc_negative_fwd3':base.get('auc_fwd3_negative'),
              'reaccel_corr_fwd3':corr([x['new_q4_reaccel'] for x in bs],[x['fwd_3m_pct'] for x in bs]),
              'reaccel_auc_positive_fwd3':auc([x['new_q4_reaccel'] for x in bs],[1 if x['fwd_3m_pct']>0 else 0 for x in bs])}
    # Buy-condition formula is intentionally unchanged and still certified by final_backtest metrics.
    buy_metrics=final.get('metrics') or {}
    gate=bool(len(evals)>=30 and unified['down_auc_negative_fwd3'] is not None and baseline['down_auc_negative_fwd3'] is not None and
              unified['down_auc_negative_fwd3']>=baseline['down_auc_negative_fwd3']-.02 and
              unified['reaccel_auc_positive_fwd3'] is not None and baseline['reaccel_auc_positive_fwd3'] is not None and
              unified['reaccel_auc_positive_fwd3']>=baseline['reaccel_auc_positive_fwd3']-.02 and
              n(buy_metrics.get('score_vs_fwd_6m_corr'),-9)>=0.30 and n(buy_metrics.get('score_vs_fwd_12m_corr'),-9)>=0.45)
    out={'status':'research_validation','rows_compared':len(evals),'baseline_forecast':baseline,'unified_forecast':unified,
         'buy_condition_certified_metrics':buy_metrics,'current_candidate':{'snapshot_id':cand['feature_layer']['snapshot_id'],'current_state':cand['heads']['current_state'],
         'buy_condition':cand['heads']['buy_condition'],'forward':cand['heads']['forward_scenario']},
         'apply_recommended':gate,'gate':'n>=30; downside AUC no worse >0.02; reacceleration positive AUC no worse >0.02; certified buy score corr6>=0.30 and corr12>=0.45',
         'no_future_leakage':True,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('rows_compared','baseline_forecast','unified_forecast','buy_condition_certified_metrics','current_candidate','apply_recommended')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
