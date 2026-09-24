#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1];O=R/'data_sources/kb_leading50_median.json';D=R/'dist/kb_leading50_median.json'
BASE='https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/'
TARGETS={'leading50':'leadApt50Indx','median':'mdpsPrc'}
PARAMS=[
 {'기간':'2','월간주간구분코드':'01'},
 {'기간':'2','월간주간구분코드':'02'},
 {'기간':'1','월간주간구분코드':'01'},
 {'기간':'2','매매전세코드':'01','매물종별구분':'01','면적별코드':'02','월간주간구분코드':'01'},
 {'기간':'2','매매전세코드':'02','매물종별구분':'01','면적별코드':'02','월간주간구분코드':'01'}]
def get(ep,p):
 u=BASE+ep+'?'+urllib.parse.urlencode(p);req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json','Referer':'https://data.kbland.kr/','Origin':'https://data.kbland.kr'})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def nums(x):
 if isinstance(x,dict):return sum(nums(v) for v in x.values())
 if isinstance(x,list):return sum(nums(v) for v in x)
 return int(isinstance(x,(int,float)) and not isinstance(x,bool))
def strings(x):
 if isinstance(x,dict):
  for k,v in x.items():
   yield str(k)
   yield from strings(v)
 elif isinstance(x,list):
  for v in x: yield from strings(v)
 elif isinstance(x,str):yield x
def main():
 out={'source':'KB부동산 데이터허브 web-app verified endpoints','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'targets':{}}
 for k,ep in TARGETS.items():
  tries=[];best=None
  for p in PARAMS:
   try:
    d=get(ep,p); n=nums(d); labels=list(strings(d)); rec={'params':p,'numeric_count':n,'labels':labels[:80]}
    tries.append(rec)
    if n and (best is None or n>best['numeric_count']):best={'status':'connected','endpoint':ep,'params':p,'numeric_count':n,'payload':d}
   except Exception as e:tries.append({'params':p,'error':str(e)[:160]})
  out['targets'][k]=best or {'status':'not_connected'}
  out['targets'][k]['tries']=tries
 txt=json.dumps(out,ensure_ascii=False,indent=2);O.write_text(txt);D.write_text(txt);print(json.dumps({k:(v['status'],v.get('numeric_count')) for k,v in out['targets'].items()},ensure_ascii=False))
if __name__=='__main__':main()
