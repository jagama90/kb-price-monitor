#!/usr/bin/env python3
"""Build value score only from a verified historical KB weekly sale-index series."""
import json,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];SRC=ROOT/'data_sources/kb_weekly_sale_index.json';OUT=ROOT/'data_sources/kb_value_score.json'
def main():
 d=json.loads(SRC.read_text()) if SRC.exists() else {};series=d.get('series_values') or []
 vals=[float(x['value']) for x in series if isinstance(x,dict) and x.get('value') is not None]
 out={'status':'pending_history','score_0_100':None,'source':'KB부동산 주간 아파트 매매가격지수','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 if len(vals)>=52:
  cur=vals[-1];peak=max(vals[-156:]);low=min(vals[-156:]);rng=max(peak-low,1e-9)
  # Lower position within the 3y range improves valuation, but price decline alone is capped.
  position=(cur-low)/rng
  out.update(status='connected',score_0_100=round(max(25,min(75,75-position*50)),1),current=cur,peak_3y=peak,low_3y=low,observations=len(vals),method='3y range position, capped 25..75; requires >=52 verified weekly observations')
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
