#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]; O=R/'data_sources/kb_remaining_sources.json'; D=R/'dist/kb_remaining_sources.json'
BASE='https://data-api.kbland.kr/bfmstat/statusBoard/'
EPS={'sale_index':'weeklyAptPrcIndx','rent_index':'weeklyAptYrpayPrcIndx','sale_price':'weeklyAptPrice','rent_price':'weeklyAptYrpayPrice','dctr':'weeklyAptDctr'}
def get(ep,dt):
 q=urllib.parse.urlencode({'기준년월일':dt,'법정동코드':'0000000000'});u=BASE+ep+'?'+q
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/','Origin':'https://data.kbland.kr'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
def walk(x,path=''):
 out=[]
 if isinstance(x,dict):
  for k,v in x.items():out+=walk(v,path+'/'+str(k))
 elif isinstance(x,list):
  for i,v in enumerate(x):out+=walk(v,path+'/'+str(i))
 elif isinstance(x,(int,float)) and not isinstance(x,bool):out.append((path,x))
 return out
def main():
 today=datetime.date.today();today-=datetime.timedelta(days=today.weekday()); dates=[(today-datetime.timedelta(days=7*i)).strftime('%Y%m%d') for i in range(8)]
 out={'source':'KB부동산 데이터허브 statusBoard','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'targets':{}}
 for k,ep in EPS.items():
  for dt in dates:
   try:
    raw=get(ep,dt); nums=walk(raw)
    if nums:
     out['targets'][k]={'status':'connected','endpoint':ep,'requested_date':dt,'numeric_count':len(nums),'payload':raw};break
   except Exception:pass
  out['targets'].setdefault(k,{'status':'not_connected','endpoint':ep})
 txt=json.dumps(out,ensure_ascii=False,indent=2);O.parent.mkdir(exist_ok=True);O.write_text(txt);D.write_text(txt);print(json.dumps({k:v['status'] for k,v in out['targets'].items()},ensure_ascii=False))
if __name__=='__main__':main()
