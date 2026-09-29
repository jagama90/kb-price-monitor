#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1];O=R/'data_sources/kb_valuation_source_probe2.json'
BASE='https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/'
TESTS={
 'mortgage_pir':('husScurlnPir',[
   {'메뉴코드':'01'},
   {'기간':'1','메뉴코드':'01'},
   {'기간':'2','메뉴코드':'01'},
 ]),
 'avg_price_full':('avgPrc',[
   {'매매전세코드':'01','매물종별구분':'01','면적별코드':'02','월간주간구분코드':'01'},
   {'기간':'all','매매전세코드':'01','매물종별구분':'01','면적별코드':'02','월간주간구분코드':'01'},
 ]),
}
def get(ep,p):
 u=BASE+ep+'?'+urllib.parse.urlencode(p)
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/plain,*/*','Referer':'https://data.kbland.kr/'})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def summary(raw):
 body=(raw or {}).get('dataBody') or raw
 data=(body or {}).get('data') or body
 if not isinstance(data,dict):return {'type':type(data).__name__}
 dates=data.get('날짜리스트') or []
 rows=data.get('데이터리스트') or []
 seoul=next((x for x in rows if isinstance(x,dict) and (x.get('지역명')=='서울' or str(x.get('지역코드'))=='1100000000')),None)
 return {'keys':list(data.keys()),'update':data.get('업데이트일자'),'dates_n':len(dates),'dates_head':dates[:4],'dates_tail':dates[-4:],
         'seoul':seoul}
def main():
 out={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':{}}
 for k,(ep,plist) in TESTS.items():
  z=[]
  for p in plist:
   try:z.append({'params':p,'ok':True,'summary':summary(get(ep,p))})
   except Exception as e:z.append({'params':p,'ok':False,'error':str(e)[:300]})
  out['tests'][k]={'endpoint':BASE+ep,'tries':z}
 O.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps(out,ensure_ascii=False)[:10000])
if __name__=='__main__':main()
