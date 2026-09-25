#!/usr/bin/env python3
"""Validate long-cycle inputs before regime backtest."""
import json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'dist/long_cycle_validation.json'
def load(p):
 q=R/p
 if not q.exists(): return None
 try:return json.loads(q.read_text())
 except:return None
def main():
 reb=load('data_sources/reb_long_cycle.json'); m2=load('data_sources/ecos_m2.json'); pol=load('data_sources/housing_policy_events.json')
 checks={
  'reb_file':bool(reb),
  'reb_price_series':bool(reb and reb.get('series',{}).get('price')),
  'reb_trade_series':bool(reb and reb.get('series',{}).get('trade')),
  'm2_2005_start':bool(m2 and m2.get('series') and str(m2['series'][0].get('period',''))<='200501'),
  'policy_started':bool(pol and len(pol.get('events',[]))>0)
 }
 payload={'status':'ready' if all(checks.values()) else 'waiting_inputs','checks':checks}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2));print(json.dumps(payload,ensure_ascii=False))
if __name__=='__main__':main()
