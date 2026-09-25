#!/usr/bin/env python3
"""R-ONE long-cycle collector. Requires RONE_API_KEY for full history."""
import os,json,urllib.parse,urllib.request,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'data_sources/reb_long_cycle.json'
BASE='https://www.reb.or.kr/r-one/openapi/'
def get(endpoint,params):
 q=urllib.parse.urlencode(params); req=urllib.request.Request(BASE+endpoint+'?'+q,headers={'User-Agent':'kb-price-monitor/1.0'})
 with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
def main():
 key=os.getenv('RONE_API_KEY','sample')
 # Discovery-first: persist official table metadata so exact current STATBL/CLS/ITM codes are not guessed.
 tables=get('SttsApiTbl.do',{'KEY':key,'Type':'json','pIndex':1,'pSize':1000})\n # Identify candidate official tables by their returned metadata; do not hard-code unstable IDs.\n raw=json.dumps(tables,ensure_ascii=False)\n candidates=[q for q in ('공동주택 실거래가격지수','부동산거래현황') if q in raw]
 out={'source':'한국부동산원 R-ONE','api_base':BASE,'target_start':'2006-01','key_mode':'full' if key!='sample' else 'sample',
      'purpose':['서울 공동주택 실거래가격지수','서울 부동산 거래현황'],
      'table_catalog':tables,'candidate_topics':candidates,'series':{},'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({'key_mode':out['key_mode'],'catalog_saved':True},ensure_ascii=False))
if __name__=='__main__':main()
