#!/usr/bin/env python3
import json,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];SRC=ROOT/'data_sources/kb_statusboard_live.json'
def extract(kind,label):
 d=json.loads(SRC.read_text());rows={}
 for obs in d['targets'][kind]['series']:
  body=obs['payload'].get('dataBody',{}).get('data',{})
  arr=body.get(label,[])
  for x in arr:
   if x.get('지역명')=='서울':
    dt=str(x.get('통계기준년월일시'));val=x.get('현재데이터')
    if dt and val is not None: rows[dt]={'date':dt,'value':float(val),'change_pct':float(x.get('변동률')) if x.get('변동률') not in (None,'') else None}
 return [rows[k] for k in sorted(rows)]
def main():
 for kind,label,name in [('sale','주간 매매지수','kb_weekly_sale_index.json'),('rent','주간 전세지수','kb_weekly_rent_index.json')]:
  rows=extract(kind,label)
  if len(rows)<2:raise SystemExit(f'insufficient parsed Seoul rows: {kind}')
  out={'status':'connected','source':'KB부동산 데이터허브','region':'서울','frequency':'weekly','series_values':rows,'latest':rows[-1],'observations':len(rows),'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  (ROOT/'data_sources'/name).write_text(json.dumps(out,ensure_ascii=False,indent=2))
  print(name,len(rows),rows[-1])
if __name__=='__main__':main()
