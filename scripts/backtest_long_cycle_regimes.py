#!/usr/bin/env python3
"""Research-only state-machine scaffold for long-cycle buy-window validation."""
import json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]; SRC=R/'dist/long_cycle_master.json'; OUT=R/'dist/long_cycle_regime_backtest.json'
def main():
 d=json.loads(SRC.read_text()); rows=d.get('rows',[]); out=[]
 vals=[]
 for i,r in enumerate(rows):
  p=float(r['price'].get('value',0) or 0); vals.append(p)
  m1=(p/vals[i-1]-1)*100 if i and vals[i-1] else None
  m3=(p/vals[i-3]-1)*100 if i>=3 and vals[i-3] else None
  if m3 is None: state='warmup'
  elif m3<-3: state='decline'
  elif m3<=0 and (m1 or 0)>=0: state='bottom_watch'
  elif m3>0 and (m1 or 0)>0: state='recovery'
  else: state='observe'
  out.append({'ym':r['ym'],'state':state,'price_mom_1m':m1,'price_mom_3m':m3})
 OUT.write_text(json.dumps({'status':'research_only','thresholds_provisional':True,'rows':out},ensure_ascii=False,indent=2));print(len(out))
if __name__=='__main__':main()
