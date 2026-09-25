#!/usr/bin/env python3
"""Build a no-future-leakage monthly master once independent long-cycle tracks are available."""
import json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'dist/long_cycle_master.json'
def read(p): return json.loads((R/p).read_text())
def main():
 reb=read('data_sources/reb_long_cycle.json'); m2=read('data_sources/ecos_m2.json'); pol=read('data_sources/housing_policy_events.json')
 price={x['ym']:x for x in reb.get('series',{}).get('price',[])}
 trade={x['ym']:x for x in reb.get('series',{}).get('trade',[])}
 mm={x['period']:x for x in m2.get('series',[])}
 months=sorted(set(price)&set(trade)&set(mm))
 rows=[]
 for ym in months:
  events=[e for e in pol.get('events',[]) if e.get('date','')[:7].replace('-','')==ym]
  rows.append({'ym':ym,'price':price[ym],'trade':trade[ym],'m2':mm[ym],'policy_events':events})
 OUT.write_text(json.dumps({'status':'research_only','no_future_leakage':True,'rows':rows},ensure_ascii=False,indent=2))
 print(json.dumps({'months':len(rows),'first':months[0] if months else None,'last':months[-1] if months else None}))
if __name__=='__main__':main()
