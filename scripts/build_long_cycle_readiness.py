#!/usr/bin/env python3
"""Inventory inputs for a 2006+ long-cycle regime model. Research-only."""
import json,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'dist/long_cycle_readiness.json'
def inspect(path):
 p=R/path
 if not p.exists(): return {'path':path,'exists':False}
 try:d=json.loads(p.read_text())
 except Exception as e:return {'path':path,'exists':True,'error':str(e)}
 seq=d.get('rows') or d.get('series') or []; ps=[]
 for x in seq:
  if isinstance(x,dict):
   v=x.get('ym') or x.get('period') or x.get('date')
   if v: ps.append(str(v))
 return {'path':path,'exists':True,'rows':len(seq),'first':min(ps) if ps else None,'last':max(ps) if ps else None}
def main():
 out={'status':'research_only','goal':'2006+ long-cycle validation parallel to unchanged 2022+ precision model',
 'tracks':{
  'price_trade':{'target_start':'2006-01','preferred':'REB R-ONE monthly apartment real transaction price index + real-estate transaction status','official_api':'https://www.reb.or.kr/r-one/portal/openapi/openApiIntroPage.do','collector':'scripts/collect_reb_long_cycle.py','status':'collector_implemented'},
  'finance':{'target_start':'2006-01','preferred':'BOK base rate + M2','status':'inventory_ready'},
  'policy':{'target_start':'2006-01','schema':['date','category','direction','intensity','scope','announcement_or_effective','source'],'status':'timeline_backfill_required'},
  'regime_test':{'states':['decline','bottom_watch','bottom_turn','recovery','uptrend','reacceleration','slowdown'],'status':'waiting_for_long_inputs'}},
 'existing_source_inventory':{k:inspect(v) for k,v in {'precision_price':'dist/garak_geumho_24a_history.json','m2':'data_sources/ecos_m2.json','kb_sentiment':'data_sources/kb_sentiment.json','precision_demand':'dist/molit_historical_backtest.json'}.items()},
 'guardrails':['no future leakage','no 2023/2025 threshold tuning before long-cycle holdout','encode documented policy actions rather than party/person as directional score','production 2022+ model remains unchanged until validation passes'],
 'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
