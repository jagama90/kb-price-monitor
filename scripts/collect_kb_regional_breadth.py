#!/usr/bin/env python3
"""Collect current KB weekly Seoul district breadth from official statusBoard API."""
import json,urllib.request,urllib.parse,pathlib,datetime,time,random,statistics
from zoneinfo import ZoneInfo
R=pathlib.Path(__file__).resolve().parents[1]
OUT=R/'data_sources/kb_regional_breadth.json'
BASE='https://data-api.kbland.kr/bfmstat/statusBoard/weeklyAptPrcIndx'
SEOUL={
'종로구':'1111000000','중구':'1114000000','용산구':'1117000000','성동구':'1120000000','광진구':'1121500000','동대문구':'1123000000',
'중랑구':'1126000000','성북구':'1129000000','강북구':'1130500000','도봉구':'1132000000','노원구':'1135000000','은평구':'1138000000',
'서대문구':'1141000000','마포구':'1144000000','양천구':'1147000000','강서구':'1150000000','구로구':'1153000000','금천구':'1154500000',
'영등포구':'1156000000','동작구':'1159000000','관악구':'1162000000','서초구':'1165000000','강남구':'1168000000','송파구':'1171000000','강동구':'1174000000'}
G3={'강남구','서초구','송파구'}
def mondays(n=8):
 d=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date();d-=datetime.timedelta(days=d.weekday())
 return [(d-datetime.timedelta(days=7*i)).strftime('%Y%m%d') for i in range(n)]
def get(dt,code):
 q=urllib.parse.urlencode({'기준년월일':dt,'법정동코드':code})
 req=urllib.request.Request(BASE+'?'+q,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/','Origin':'https://data.kbland.kr'})
 last=None
 for a in range(4):
  try:
   with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
  except Exception as e:
   last=e
   if a<3:time.sleep(min(8,2**a+random.random()))
 raise last
def rows(payload):
 d=((payload.get('dataBody') or {}).get('data') or {})
 return d.get('주간 매매지수') or []
def pick(row):
 try:chg=float(row.get('변동률'))
 except:return None
 return {'region':row.get('지역명'),'code':str(row.get('법정동코드') or ''),'date':str(row.get('통계기준년월일시') or ''),
         'index':float(row.get('현재데이터')) if row.get('현재데이터') is not None else None,'change_pct':chg}
def main():
 hit_date=None;region_rows=[]
 for dt in mondays():
  try:
   p=get(dt,'1100000000'); rr=[pick(x) for x in rows(p)];rr=[x for x in rr if x]
   # Some API modes return Seoul + all 25 child districts in one response.
   child=[x for x in rr if x['region'] in SEOUL]
   if len(child)>=20:
    hit_date=dt;region_rows=child;break
  except Exception:pass
 if not region_rows:
  # Fallback: discover the latest valid date once, then query each district.
  for dt in mondays():
   got=[]
   for name,code in SEOUL.items():
    try:
     rr=[pick(x) for x in rows(get(dt,code))]; rr=[x for x in rr if x]
     z=next((x for x in rr if x['region']==name or x['code']==code),None)
     if z:got.append(z)
    except Exception:continue
   if len(got)>=20:
    hit_date=dt;region_rows=got;break
 if not region_rows: raise SystemExit('no Seoul district weekly rows')
 by={x['region']:x for x in region_rows}
 def group(names):
  arr=[by[n]['change_pct'] for n in names if n in by]
  return {'count':len(arr),'up':sum(v>0 for v in arr),'flat':sum(v==0 for v in arr),'down':sum(v<0 for v in arr),
          'up_share_pct':round(100*sum(v>0 for v in arr)/len(arr),1) if arr else None,
          'median_change_pct':round(statistics.median(arr),3) if arr else None}
 groups={'seoul_25':group(set(SEOUL)),'gangnam3':group(G3),'non_gangnam3':group(set(SEOUL)-G3)}
 out={'status':'connected','source':'KB부동산 데이터허브 statusBoard weeklyAptPrcIndx','date':hit_date,'districts':sorted(region_rows,key=lambda x:x['region']),
      'groups':groups,'songpa':by.get('송파구'),'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'date':hit_date,'districts':len(region_rows),'groups':groups,'songpa':by.get('송파구')},ensure_ascii=False))
if __name__=='__main__':main()
