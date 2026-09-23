#!/usr/bin/env python3
"""Collect KB weekly market sentiment from KB DataHub's public JSON endpoint."""
import json,urllib.parse,urllib.request,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/kb_sentiment.json'
URL='https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/maktTrnd'
def get(params):
 u=URL+'?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
def main():
 # HT04 is KB DataHub's market-trend/survey menu; 02 = weekly.
 responses=[]
 for menu,kind in [('01','매수우위'),('02','매매거래활발')]:
  raw=get({'메뉴코드':menu,'기간':'2','월간주간구분코드':'02'});responses.append((kind,raw))
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
