#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime,itertools
R=pathlib.Path(__file__).resolve().parents[1]
O=R/'data_sources/kb_valuation_endpoint_probe.json'
BASE='https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/'
TARGETS={
 'pir':'pir',
 'rent_ratio':'dealCntstTnantRato',
 'avg_price':'avgPrc'
}
PARAMS=[
 {},
 {'기간':'1'},{'기간':'2'},{'기간':'all'},
 {'월간주간구분코드':'01'},
 {'기간':'1','월간주간구분코드':'01'},
 {'기간':'2','월간주간구분코드':'01'},
 {'기간':'1','매물종별구분':'01','월간주간구분코드':'01'},
 {'기간':'2','매물종별구분':'01','월간주간구분코드':'01'},
 {'기간':'1','매매전세코드':'01','매물종별구분':'01','면적별코드':'02','월간주간구분코드':'01'},
 {'기간':'2','매매전세코드':'01','매물종별구분':'01','면적별코드':'02','월간주간구분코드':'01'}
]
def get(ep,params):
 u=BASE+ep
 if params:u+='?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/plain,*/*','Referer':'https://data.kbland.kr/'})
 with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
def nums(x):
 if isinstance(x,dict):return sum(nums(v) for v in x.values())
 if isinstance(x,list):return sum(nums(v) for v in x)
 return int(isinstance(x,(int,float)) and not isinstance(x,bool))
def shape(x,depth=0):
 if depth>3:return type(x).__name__
 if isinstance(x,dict):return {k:shape(v,depth+1) for k,v in list(x.items())[:25]}
 if isinstance(x,list):return {'list_len':len(x),'sample':shape(x[0],depth+1) if x else None}
 return type(x).__name__
def samples(x,path='root',out=None):
 out=[] if out is None else out
 if len(out)>=30:return out
 if isinstance(x,dict):
  # keep records that look like region/date/value rows
  ks=' '.join(map(str,x.keys()))
  if any(k in ks for k in ['지역','날짜','년월','기준','PIR','전세','가격','평균','중위','데이터']):
   out.append({'path':path,'row':x})
  for k,v in x.items():samples(v,path+'.'+str(k),out)
 elif isinstance(x,list):
  for i,v in enumerate(x[:8]):samples(v,path+f'[{i}]',out)
 return out
def main():
 out={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'targets':{}}
 for key,ep in TARGETS.items():
  tries=[]
  for p in PARAMS:
   try:
    raw=get(ep,p);body=raw.get('dataBody') if isinstance(raw,dict) else raw
    tries.append({'params':p,'ok':True,'numeric_count':nums(body),'shape':shape(body),'samples':samples(body)[:12]})
   except Exception as e:
    tries.append({'params':p,'ok':False,'error':str(e)[:240]})
  out['targets'][key]={'endpoint':BASE+ep,'tries':tries}
 O.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({k:[{'p':x['params'],'ok':x['ok'],'n':x.get('numeric_count')} for x in v['tries'] if x['ok']] for k,v in out['targets'].items()},ensure_ascii=False))
if __name__=='__main__':main()
