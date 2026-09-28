#!/usr/bin/env python3
"""Collect KB weekly market sentiment from KB DataHub's public JSON endpoint."""
import json,urllib.parse,urllib.request,pathlib,datetime,os,time
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/kb_sentiment.json'
URL='https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/maktTrnd'
def get(params,timeout):
 u=URL+'?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/'})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)

def fetch_all(specs):
 fast=max(3,float(os.getenv('KB_SENTIMENT_FAST_TIMEOUT','8')))
 retry=max(fast,float(os.getenv('KB_SENTIMENT_RETRY_TIMEOUT','20')))
 def run(todo,timeout):
  out={};err={};dur={}
  with ThreadPoolExecutor(max_workers=min(4,len(todo))) as pool:
   tasks={}
   for menu,kind in todo:
    started=time.monotonic()
    fut=pool.submit(get,{'메뉴코드':menu,'기간':'5','월간주간구분코드':'02'},timeout)
    tasks[fut]=(menu,kind,started)
   for fut in as_completed(tasks):
    menu,kind,started=tasks[fut];dur[kind]=round(time.monotonic()-started,1)
    try:out[kind]=fut.result()
    except Exception as e:err[kind]=repr(e)
  return out,err,dur
 first,errors,d1=run(specs,fast)
 retried=[x for x in specs if x[1] in errors]
 recovered={};errors2={};d2={}
 if retried:
  time.sleep(1)
  recovered,errors2,d2=run(retried,retry)
 result=dict(first);result.update(recovered)
 if errors2:
  raise RuntimeError('KB sentiment menus failed after retry: '+json.dumps(errors2,ensure_ascii=False))
 print(json.dumps({'collector':'KB sentiment','stage':'parallel_fetch','menus':len(specs),
  'fast_timeout_sec':fast,'first_pass_failed':len(retried),'retry_recovered':len(recovered),
  'durations_first':d1,'durations_retry':d2},ensure_ascii=False),flush=True)
 return [(kind,result[kind]) for _,kind in specs]
def main():
 # HT04 is KB DataHub's market-trend/survey menu; 02 = weekly.
 specs=[('01','매수우위'),('02','매매거래활발'),('03','전세수급'),('04','전세거래활발')]
 responses=fetch_all(specs)
 rows=[]
 for expected,raw in responses:
  data=((raw.get('dataBody') or {}).get('data') or {}).get('데이터리스트') or []
  for region in data:
   name=region.get('지역명');code=region.get('지역코드')
   for z in region.get('dataList') or []:
    kind=expected
    date=z.get('기준날짜')
    # API shapes may expose the index as one of several named result fields.
    vals={k:v for k,v in z.items() if k not in ('설문종류','기준날짜') and isinstance(v,(int,float))}
    rows.append({'region':name,'region_code':code,'date':date,'kind':kind,'values':vals})
 # Keep Seoul and national rows; retain raw response shape for audit.
 keep=[x for x in rows if x['region'] in ('서울','전국')]
 payload={'source':'KB부동산 데이터허브','endpoint':'weekMnthlyHuseTrnd/maktTrnd','frequency':'weekly','rows':keep,'row_count':len(keep),'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 print(json.dumps({'collector':'KB sentiment','rows':len(keep),'regions':sorted(set(x['region'] for x in keep)),'kinds':sorted(set(x['kind'] for x in keep))},ensure_ascii=False))
 if not keep: raise SystemExit('KB sentiment endpoint responded but no Seoul/national sentiment rows parsed')
if __name__=='__main__':main()
