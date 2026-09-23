#!/usr/bin/env python3
"""Append a compact daily market-condition history from already verified official inputs."""
import json,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'dist/market_indicators.json'; OUT=ROOT/'data_sources/condition_index_history.json'; DIST=ROOT/'dist/condition_index_history.json'
def clamp(v): return max(0,min(100,v))
def main():
 d=json.loads(SRC.read_text()); m=d.get('m2_official') or d.get('m2') or {}; mp=d.get('matched_period')
 finance=None; demand=None
 if m.get('mom_pct') is not None and m.get('yoy_pct') is not None: finance=clamp(50+float(m['mom_pct'])*8+float(m['yoy_pct'])*1.5)
 if mp and mp.get('changes',{}).get('trade_count_pct') is not None and mp.get('changes',{}).get('under15_share_pp') is not None:
  c=mp['changes']; demand=clamp(50+float(c['trade_count_pct'])*.35+float(c['under15_share_pp'])*1.5)
 else:
  a=d.get('price_bands',{}).get('months',[])
  if len(a)>=2:
   p,c=a[-2],a[-1]; demand=clamp(50+((c['total']/p['total'])-1)*35+(c['under15_share']-p['under15_share'])*1.5)
 weights={'finance':25,'demand':20}; vals={'finance':finance,'demand':demand}; avail=[k for k,v in vals.items() if v is not None]; coverage=sum(weights[k] for k in avail)
 score=round(sum(vals[k]*weights[k] for k in avail)/coverage,1) if coverage>=60 else None
 row={'date':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat(),'coverage_weight':coverage,'score':score,'components':vals,'source_updated_at':d.get('updated_at')}
 hist=json.loads(OUT.read_text()) if OUT.exists() else {'version':1,'rows':[]}; hist['rows']=[x for x in hist.get('rows',[]) if x.get('date')!=row['date']]+[row]; hist['rows']=hist['rows'][-730:]
 OUT.parent.mkdir(exist_ok=True); txt=json.dumps(hist,ensure_ascii=False,indent=2); OUT.write_text(txt); DIST.write_text(txt); print(json.dumps(row,ensure_ascii=False))
if __name__=='__main__': main()
