#!/usr/bin/env python3
"""Small ECOS connectivity/storage smoke test: discover candidate tables by official names, fetch only a few rows."""
import os,json,urllib.request,urllib.parse,pathlib,datetime,time
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'data_sources/ecos_smoke.json'
TARGETS=['주택담보대출','가계대출금리','가계신용']
def get(url):
 for n in range(4):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'kb-price-monitor/1.0'})
   with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
  except Exception:
   if n==3: raise
   time.sleep(2**n)
def main():
 key=os.getenv('BOK_ECOS_KEY')
 if not key: raise SystemExit('BOK_ECOS_KEY secret is required')
 # ECOS StatisticTableList is used for discovery so table codes are never guessed.
 url=f'https://ecos.bok.or.kr/api/StatisticTableList/{key}/json/kr/1/1000/'
 rows=get(url).get('StatisticTableList',{}).get('row',[])
 result=[]
 for target in TARGETS:
  hits=[r for r in rows if target in str(r.get('STAT_NAME',''))]
  result.append({'target':target,'table_hits':[{'stat_code':h.get('STAT_CODE'),'stat_name':h.get('STAT_NAME'),'cycle':h.get('CYCLE')} for h in hits[:5]],'communication_ok':True,'stored_ok':True})
 out={'source':'한국은행 ECOS','mode':'smoke_test','targets':result,'table_rows_seen':len(rows),'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
