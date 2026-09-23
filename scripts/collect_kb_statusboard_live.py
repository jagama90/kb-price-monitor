#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='https://data-api.kbland.kr/bfmstat/statusBoard/'
TARGETS={'sale':'weeklyAptPrcIndx','rent':'weeklyAptYrpayPrcIndx','sale_price':'weeklyAptPrice','rent_price':'weeklyAptYrpayPrice','dctr':'weeklyAptDctr'}
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
  rows=[]
  for dt in mondays():
   try:
    data=fetch(ep,dt)
    if numeric_count(data)>0: rows.append({'date':dt,'endpoint':BASE+ep,'numeric_fields':numeric_count(data),'payload':data})
   except Exception:pass
  if not rows:raise SystemExit(f'no live numeric payload: {k}')
  out[k]={'observations':rows,'latest':rows[0],'count':len(rows)}
 p=ROOT/'data_sources/kb_statusboard_live.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps({'status':'connected','source':'KB부동산 데이터허브','query':{'법정동코드':'0000000000'},'targets':out,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()},ensure_ascii=False,indent=2))
 print(json.dumps({k:{'count':v['count'],'latest':v['latest']['date']} for k,v in out.items()},ensure_ascii=False))
if __name__=='__main__':main()
