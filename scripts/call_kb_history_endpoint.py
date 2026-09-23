#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime,itertools
ROOT=pathlib.Path(__file__).resolve().parents[1]; M=ROOT/'data/buy_watchlist_master.json'; O=ROOT/'data_sources/kb_history_live.json'
BASES=['https://api.kbland.kr','https://data-api.kbland.kr']
PATHS=['/land-price/price/PerMn/IntgrationChart','/land-price/price/complex/integrationChart','/land-price/price/ChartBriefInfo','/land-price/price/QuotBaseYear','/land-price/price/WholQuotList']
def req(url):
 r=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json','Referer':'https://kbland.kr/'})
 with urllib.request.urlopen(r,timeout=20) as x:return x.status,x.read().decode('utf-8','ignore')
def main():
 m=json.loads(M.read_text()); x=next(z for z in m['items'] if z.get('complex_id') and z.get('types')); cid=x['complex_id']; aid=x['types'][0]['area_id']
 variants=[
 {'단지기본일련번호':cid,'면적일련번호':aid},
 {'complexId':cid,'areaId':aid},
 {'단지기본일련번호':cid,'면적일련번호':aid,'매물종별구분':'01'},
 {'단지기본일련번호':cid,'면적일련번호':aid,'기간':'3'},
 ]
 out=[]
 for base,path,p in itertools.product(BASES,PATHS,variants):
  url=base+path+'?'+urllib.parse.urlencode(p)
  try:
   st,txt=req(url); payload=json.loads(txt); body=payload.get('dataBody',{}); data=body.get('data')
   out.append({'url':url,'http':st,'resultCode':body.get('resultCode'),'data':data})
  except Exception as e: out.append({'url':url,'error':str(e)[:180]})
 result={'sample':{'complex_id':cid,'area_id':aid,'name':x.get('user_name')},'attempts':out,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 O.parent.mkdir(exist_ok=True);O.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
