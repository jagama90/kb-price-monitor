#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='https://data-api.kbland.kr/bfmstat/statusBoard/'
TARGETS={'sale':'weeklyAptPrcIndx','rent':'weeklyAptYrpayPrcIndx'}
def mondays(n=60):
 d=datetime.date.today()
 d-=datetime.timedelta(days=d.weekday())
 return [(d-datetime.timedelta(days=7*i)).strftime('%Y%m%d') for i in range(n)]
def fetch(ep,dt):
 q=urllib.parse.urlencode({'기준년월일':dt,'법정동코드':'0000000000'})
 req=urllib.request.Request(BASE+ep+'?'+q,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/','Origin':'https://data.kbland.kr'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
def numeric_count(x):
 if isinstance(x,dict):return sum(numeric_count(v) for v in x.values())
 if isinstance(x,list):return sum(numeric_count(v) for v in x)
 return int(isinstance(x,(int,float)) and not isinstance(x,bool))
def main():
 out={}
 for k,ep in TARGETS.items():
  hit=None
  for dt in mondays():
   try:
    data=fetch(ep,dt)
    if numeric_count(data)>0:
     hit={'date':dt,'endpoint':BASE+ep,'numeric_fields':numeric_count(data),'payload':data};break
   except Exception:pass
  if not hit:raise SystemExit(f'no live numeric payload: {k}')
  out[k]=hit
 p=ROOT/'data_sources/kb_statusboard_live.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps({'status':'connected','source':'KB부동산 데이터허브','query':{'법정동코드':'0000000000'},'targets':out,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()},ensure_ascii=False,indent=2))
 print(json.dumps({k:{'date':v['date'],'numeric_fields':v['numeric_fields']} for k,v in out.items()},ensure_ascii=False))
if __name__=='__main__':main()
