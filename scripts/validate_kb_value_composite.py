#!/usr/bin/env python3
"""Compare the legacy single-complex value component with the composite KB Seoul candidate."""
import json,pathlib,math,statistics,datetime
R=pathlib.Path(__file__).resolve().parents[1]
BASE=R/'dist/final_backtest.json';CAND=R/'dist/kb_value_composite_candidate.json';OUT=R/'dist/kb_value_composite_validation.json'
W={'finance':25,'sentiment':20,'demand':20,'value':20,'supply':15}
def corr(a,b):
    z=[(float(x),float(y)) for x,y in zip(a,b) if x is not None and y is not None]
    if len(z)<3:return None
    ax=sum(x for x,_ in z)/len(z);ay=sum(y for _,y in z)/len(z)
    dx=sum((x-ax)**2 for x,_ in z);dy=sum((y-ay)**2 for _,y in z)
    return sum((x-ax)*(y-ay) for x,y in z)/math.sqrt(dx*dy) if dx and dy else None
def stats(rows,key):
    out={'n':len(rows)}
    for h in (1,3,6,12):
        f=f'fwd_{h}m_pct';out[f'corr_fwd_{h}m']=corr([x.get(key) for x in rows],[x.get(f) for x in rows])
    valid=[x for x in rows if x.get(key) is not None and x.get('fwd_6m_pct') is not None]
    if valid:
        z=sorted(valid,key=lambda x:x[key]);n=max(1,len(z)//3)
        lo=[x['fwd_6m_pct'] for x in z[:n]];hi=[x['fwd_6m_pct'] for x in z[-n:]]
        out['low_third_mean_fwd_6m']=sum(lo)/len(lo);out['high_third_mean_fwd_6m']=sum(hi)/len(hi);out['spread_6m']=out['high_third_mean_fwd_6m']-out['low_third_mean_fwd_6m']
    return out
def main():
    b=json.loads(BASE.read_text());c=json.loads(CAND.read_text())
    cm={x['ym']:x for x in c.get('history',[])}
    rows=[]
    for x in b.get('rows',[]):
        if x.get('provisional') or x['ym'] not in cm or x.get('score') is None:continue
        nv=cm[x['ym']]['score_0_100'];comp=dict(x['components'])
        old=float(x['score']);comp['value']=nv
        new=sum(float(comp[k])*W[k] for k in W)/100
        rows.append({'ym':x['ym'],'old_score':old,'new_score':new,'old_value':x['components']['value'],'new_value':nv,
                     'fwd_1m_pct':x.get('fwd_1m_pct'),'fwd_3m_pct':x.get('fwd_3m_pct'),'fwd_6m_pct':x.get('fwd_6m_pct'),'fwd_12m_pct':x.get('fwd_12m_pct')})
    old=stats(rows,'old_score');new=stats(rows,'new_score')
    oldv=stats(rows,'old_value');newv=stats(rows,'new_value')
    # Gate: preserve predictive direction and avoid material degradation while removing single-complex dependency.
    old6=old.get('corr_fwd_6m');new6=new.get('corr_fwd_6m')
    old3=old.get('corr_fwd_3m');new3=new.get('corr_fwd_3m')
    spread_old=old.get('spread_6m');spread_new=new.get('spread_6m')
    gate=bool(len(rows)>=36 and new6 is not None and old6 is not None and new6>=old6-.05 and
              new3 is not None and old3 is not None and new3>=old3-.05 and
              spread_new is not None and spread_old is not None and spread_new>=spread_old-1.5)
    out={'status':'research_validation','candidate_method':c.get('method'),'certified_through':b.get('certified_through'),
         'rows_compared':len(rows),'overall':{'legacy':old,'composite':new},'value_component':{'legacy':oldv,'composite':newv},
         'apply_recommended':gate,
         'gate':'n>=36; overall 3m and 6m correlations no worse than legacy by >0.05; 6m top-bottom spread no worse by >1.5pp',
         'sample':rows,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('rows_compared','overall','value_component','apply_recommended')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
