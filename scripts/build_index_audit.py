#!/usr/bin/env python3
"""Build auditable score contributions and source/freshness confidence."""
import json,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]; SRC=ROOT/'dist/market_indicators.json'; OUT=ROOT/'dist/index_audit.json'
WEIGHTS={'finance':25,'sentiment':20,'demand':20,'value':20,'supply':15}
def clamp(x): return max(0,min(100,x))
def age_days(date):
 try:return (datetime.date.today()-datetime.date.fromisoformat(str(date)[:10])).days
 except:return None
def main():
 d=json.loads(SRC.read_text()); m=d.get('m2_official') or d.get('m2') or {}; mp=d.get('matched_period'); bands=d.get('price_bands',{}).get('months',[])
 vals={'finance':None,'sentiment':None,'demand':None,'value':None,'supply':None}
 if m.get('mom_pct') is not None and m.get('yoy_pct') is not None: vals['finance']=clamp(50+float(m['mom_pct'])*8+float(m['yoy_pct'])*1.5)
 if mp and mp.get('changes',{}).get('trade_count_pct') is not None and mp.get('changes',{}).get('under15_share_pp') is not None:
  c=mp['changes']; vals['demand']=clamp(50+float(c['trade_count_pct'])*.35+float(c['under15_share_pp'])*1.5)
 elif len(bands)>=2:
  p,c=bands[-2],bands[-1]; vals['demand']=clamp(50+((c['total']/p['total'])-1)*35+(c['under15_share']-p['under15_share'])*1.5)
 coverage=sum(WEIGHTS[k] for k,v in vals.items() if v is not None)
 contributions={k:(round((v-50)*WEIGHTS[k]/100,2) if v is not None else None) for k,v in vals.items()}
 updated=d.get('updated_at'); age=age_days(updated); freshness=100 if age is not None and age<=1 else 85 if age is not None and age<=7 else 60 if age is not None and age<=31 else 30
 provisional=any(bool(x[2]) for x in d.get('seoul_apt_trade_count',[]) if len(x)>2)
 confidence=round(coverage*(freshness/100)*(0.9 if provisional else 1),1)
 out={'as_of':updated,'weights':WEIGHTS,'components':vals,'contribution_vs_neutral':contributions,'coverage_weight':coverage,'freshness_score':freshness,'provisional_input':provisional,'confidence_pct':confidence,'missing':[k for k,v in vals.items() if v is None],'method':'confidence = connected weight × freshness × provisional penalty; missing components are never imputed'}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)); print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
