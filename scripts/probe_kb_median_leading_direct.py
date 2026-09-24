#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1];O=R/'data_sources/kb_median_leading_direct.json'
BASE='https://data-api.kbland.kr'
CAND={
'sale_median':['/bfmstat/weekMnthlyHuseTrnd/medianPrice','/bfmstat/statusBoard/mnthlyAptMedianPrice','/bfmstat/statusBoard/weeklyAptMedianPrice'],
'rent_median':['/bfmstat/weekMnthlyHuseTrnd/medianYrpayPrice','/bfmstat/statusBoard/mnthlyAptYrpayMedianPrice','/bfmstat/statusBoard/weeklyAptYrpayMedianPrice'],
'leading50':['/bfmstat/weekMnthlyHuseTrnd/leadingApt50PriceInx','/bfmstat/statusBoard/mnthlyLeadingApt50PrcIndx','/bfmstat/statusBoard/leadingApt50PrcIndx']}
def get(path,params):
 u=BASE+path+'?'+urllib.parse.urlencode(params);req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/','Origin':'https://data.kbland.kr'})
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
def nums(x):
 if isinstance(x,dict):return sum(nums(v) for v in x.values())
 if isinstance(x,list):return sum(nums(v) for v in x)
 return int(isinstance(x,(int,float)) and not isinstance(x,bool))
def main():
 out={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'targets':{}}
 paramslist=[{'기간':'2'},{'기준년월일':'20260914','법정동코드':'0000000000'},{'메뉴코드':'01','기간':'2','월간주간구분코드':'01'}]
 for k,paths in CAND.items():
  tries=[];hit=None
  for p in paths:
   for q in paramslist:
    try:
     d=get(p,q);n=nums(d);tries.append({'endpoint':p,'params':q,'numeric_count':n})
     if n and hit is None:hit={'status':'connected_candidate','endpoint':p,'params':q,'numeric_count':n,'payload':d}
    except Exception as e:tries.append({'endpoint':p,'params':q,'error':str(e)[:100]})
  out['targets'][k]=hit or {'status':'not_connected','tries':tries}
  if hit:out['targets'][k]['tries']=tries
 O.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({k:v['status'] for k,v in out['targets'].items()}))
if __name__=='__main__':main()
