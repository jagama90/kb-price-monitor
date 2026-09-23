#!/usr/bin/env python3
"""Quantify reporting revisions between the latest two MOLIT daily vintages."""
import json,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];SRC=ROOT/'data_sources/molit_daily_history.json';OUT=ROOT/'data_sources/molit_vintage_comparison.json'
def main():
 h=json.loads(SRC.read_text()) if SRC.exists() else {'snapshots':[]}; a=h.get('snapshots',[])
 result={'status':'insufficient_vintages','vintage_count':len(a),'comparison':None,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 if len(a)>=2:
  old,new=a[-2],a[-1]; om=old.get('current_month') or {}; nm=new.get('current_month') or {}
  if om.get('period')==nm.get('period'):
   keys=['total','under15_share']; delta={k:(nm.get(k)-om.get(k) if nm.get(k) is not None and om.get(k) is not None else None) for k in keys}
   result={'status':'connected','vintage_count':len(a),'comparison':{'period':nm.get('period'),'older_as_of':old.get('as_of'),'newer_as_of':new.get('as_of'),'older':{k:om.get(k) for k in keys},'newer':{k:nm.get(k) for k in keys},'delta':delta},'generated_at':result['generated_at']}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
