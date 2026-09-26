#!/usr/bin/env python3
import json,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]
B=R/'data_sources/kb_regional_breadth.json';A=R/'dist/affordability_engine.json';T=R/'dist/regional_temperature_history.json';V=R/'dist/market_extension_validation.json';O=R/'dist/market_extensions.json'
def load(p):return json.loads(p.read_text())
def main():
 b,a,t,v=map(load,(B,A,T,V))
 latest=a.get('latest') or {};temp=t.get('latest') or {};diag=(v.get('holdout_feature_diagnostics') or {})
 stress=diag.get('breadth_threshold_stress') or {}
 breadth_robust=all((z.get('high_6m') or {}).get('mean') is not None and (z.get('low_6m') or {}).get('mean') is not None and z['high_6m']['mean']>z['low_6m']['mean'] for z in stress.values()) if stress else False
 payload={'status':'research_only','current':{
   'breadth':{'date':b.get('date'),'seoul_25':(b.get('groups') or {}).get('seoul_25'),'gangnam3':(b.get('groups') or {}).get('gangnam3'),
              'non_gangnam3':(b.get('groups') or {}).get('non_gangnam3'),'songpa':b.get('songpa')},
   'affordability':latest,
   'temperature':temp},
  'validation':{
   'breadth_role':'confidence_context' if breadth_robust else 'research_only',
   'breadth_robust_across_nearby_thresholds':breadth_robust,
   'affordability_role':'purchase_power_context',
   'local_temperature_role':'local_relative_strength_context',
   'production_price_turn_formula_changed':False,
   'reason':'breadth improves holdout discrimination but hard filtering leaves too few entry signals; affordability timing effect is inconsistent; Songpa relative strength is local rather than Seoul-wide.'},
  'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 O.write_text(json.dumps(payload,ensure_ascii=False,indent=2));print(json.dumps(payload,ensure_ascii=False))
if __name__=='__main__':main()
