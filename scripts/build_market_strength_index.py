#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, datetime
R=pathlib.Path(__file__).resolve().parents[1]
def pct(hist,x): return 100*sum(v<=x for v in hist)/len(hist) if hist else 50.0
def main():
 t=json.loads((R/'dist/turning_signal_research.json').read_text())
 b=json.loads((R/'dist/final_backtest.json').read_text())
 j=json.loads((R/'dist/market_judgment.json').read_text())
 tm={x['ym']:x for x in t.get('rows',[]) if not x.get('source_provisional')}
 rows=[]
 for x in b.get('rows',[]):
  if x.get('provisional') or x.get('ym') not in tm or x.get('fwd_3m_pct') is None: continue
  z=tm[x['ym']]; c=x.get('components') or {}
  vals=[z.get('momentum_3m_pct'),z.get('breadth'),z.get('reaccel'),c.get('finance'),c.get('sentiment'),c.get('demand'),c.get('value'),c.get('supply')]
  if any(v is None for v in vals): continue
  rows.append({'ym':x['ym'],'y':x['fwd_3m_pct'],'x':vals})
 rows.sort(key=lambda r:r['ym']); scored=[]
 for i,r in enumerate(rows):
  mp=pct([z['x'][0] for z in rows[:i+1]],r['x'][0]); vals=sorted([mp]+r['x'][1:])
  scored.append({'ym':r['ym'],'y':r['y'],'score':sum(vals[1:-1])/6})
 ss=sorted(z['score'] for z in scored); q=lambda p:ss[int((len(ss)-1)*p)]
 def stats(g): return {'n':len(g),'index_avg':round(sum(z['score'] for z in g)/len(g),1),'fwd3_avg_pct':round(sum(z['y'] for z in g)/len(g),2),'fwd3_positive_pct':round(100*sum(z['y']>0 for z in g)/len(g),1)}
 order=sorted(scored,key=lambda z:z['score']); a=len(order)//3; bb=2*len(order)//3
 groups={'low':stats(order[:a]),'mid':stats(order[a:bb]),'high':stats(order[bb:])}
 fl=j['feature_layer']; mp=pct([z['x'][0] for z in rows],fl['price_momentum']['m3_pct'])
 comps={'price_momentum':mp,'breadth':fl['signals']['breadth'],'reaccel':fl['signals']['reaccel'],'finance':fl['components']['finance'],'sentiment':fl['components']['sentiment'],'demand':fl['components']['demand'],'value':fl['components']['value'],'supply':fl['components']['supply']}
 names={'price_momentum':'가격 흐름','breadth':'시장 확산','reaccel':'재가속','finance':'금융','sentiment':'심리','demand':'거래','value':'가격·밸류','supply':'전세·공급'}
 ordered=sorted(comps.items(),key=lambda z:z[1]); core=ordered[1:-1]; score=sum(v for _,v in core)/6
 lo,hi=q(1/3),q(2/3); label='약함' if score<lo else '보통' if score<hi else '강함'; rank=100*sum(v<=score for v in ss)/len(ss)
 summary='가격 흐름은 강하지만 거래·금융·심리·시장 확산이 충분히 받쳐주지 못해, 현재 상승의 내부 힘은 약한 편입니다.' if label=='약함' else ('가격 흐름과 내부 신호가 일부 엇갈려 시장 힘은 중간 수준입니다.' if label=='보통' else '가격 흐름과 거래·금융·시장 확산이 함께 받쳐 시장 힘이 강한 편입니다.')
 engine=((fl.get('engine_features') or {}).get('market_strength') or {})
 applied=bool((engine.get('forecast_overlay') or {}).get('applied'))
 if engine.get('score_0_100') is not None:
  score=float(engine['score_0_100']);label=str(engine.get('label') or label);lo=float(engine.get('low_cut') or lo);hi=float(engine.get('high_cut') or hi)
 out={'status':'validated_engine_feature' if applied else 'validated_research_index','version':'market_strength_index_v2','production_formula_changed':applied,
 'index_role':'current_state_quality_and_short_horizon_forecast_support' if applied else 'explanatory_support_index','as_of':j.get('as_of'),'snapshot_id':fl.get('snapshot_id'),
 'current':{'score_0_100':round(score,1),'display_score':round(score),'label':label,'historical_percentile':round(rank,1),'low_cut':round(lo,1),'high_cut':round(hi,1),'strongest':{'key':ordered[-1][0],'label':names[ordered[-1][0]],'value':round(ordered[-1][1],1),'excluded_from_trim':True},'weakest':{'key':ordered[0][0],'label':names[ordered[0][0]],'value':round(ordered[0][1],1),'excluded_from_trim':True},'components':{k:{'label':names[k],'value':round(v,1),'used_in_index':k in dict(core)} for k,v in comps.items()},'summary':summary},
 'method':{'formula':'8개 0~100 신호를 동일 취급하고 최고·최저 1개를 제외한 가운데 6개 평균','hand_tuned_weights':False,'signals':['price_momentum_percentile','breadth','reaccel','finance','sentiment','demand','value','supply'],'threshold_source':'certified historical terciles','future_leakage_guard':'historical momentum percentile uses observations available through each month only'},
 'validation':{'period':[rows[0]['ym'],rows[-1]['ym']],'n':len(rows),'groups':groups,'monotonic':groups['low']['fwd3_avg_pct']<groups['mid']['fwd3_avg_pct']<groups['high']['fwd3_avg_pct'],
 'forecast_overlay':engine.get('forecast_overlay') or {},'note':'과거 구간의 평균 관계이며 미래 수익률이나 확률을 보장하지 않음'},
 'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (R/'dist/market_strength_index.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__': main()
