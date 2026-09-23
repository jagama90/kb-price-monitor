#!/usr/bin/env python3
"""Batch-probe KB DataHub official statistics used by the condition dashboard.
Stores only successful JSON responses; never fabricates values.
"""
import json,urllib.request,urllib.parse,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/kb_datahub_batch.json'
BASE='https://data-api.kbland.kr'
TARGETS=[
 ('weekly_sale_index','주간 아파트 매매가격지수','/bfmstat/weekMnthlyHuseTrnd/priceInx',{'메뉴코드':'01','기간':'2','월간주간구분코드':'02'}),
 ('weekly_rent_index','주간 아파트 전세가격지수','/bfmstat/weekMnthlyHuseTrnd/priceInx',{'메뉴코드':'02','기간':'2','월간주간구분코드':'02'}),
 ('rent_to_sale_ratio','아파트 전세가율','/bfmstat/weekMnthlyHuseTrnd/rentRatio',{'기간':'2'}),
 ('pir','PIR','/bfmstat/pir/pir',{'기간':'2'}),
 ('hoi','KB-HOI','/bfmstat/hoi/hoi',{'기간':'2'}),
 ('avg_median_price','평균·중위가격','/bfmstat/weekMnthlyHuseTrnd/avgPrice',{'기간':'2'}),
 ('leading50','KB선도50','/bfmstat/weekMnthlyHuseTrnd/leading50',{'기간':'2'}),
]
def get(path,params):
 u=BASE+path+'?'+urllib.parse.urlencode(params);req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/'})
 with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
def main():
 out={'source':'KB부동산 데이터허브','collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'targets':{}}
 for key,label,path,params in TARGETS:
  try:
   raw=get(path,params);body=raw.get('dataBody') if isinstance(raw,dict) else None
   out['targets'][key]={'label':label,'status':'connected','endpoint':path,'payload':body if body is not None else raw}
  except Exception as e:out['targets'][key]={'label':label,'status':'endpoint_pending','endpoint':path,'error':str(e)[:300]}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({k:v['status'] for k,v in out['targets'].items()},ensure_ascii=False))
if __name__=='__main__':main()
