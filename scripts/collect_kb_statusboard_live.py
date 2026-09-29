#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime,concurrent.futures
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='https://data-api.kbland.kr/bfmstat/statusBoard/'
TARGETS={'sale':('weeklyAptPrcIndx','주간 매매지수','매매지수'),'rent':('weeklyAptYrpayPrcIndx','주간 전세지수','전세지수')}

def mondays(n=16):
 d=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date()
 d-=datetime.timedelta(days=d.weekday())
 return [(d-datetime.timedelta(days=7*i)).strftime('%Y%m%d') for i in range(n)]

def fetch(ep,dt):
 q=urllib.parse.urlencode({'기준년월일':dt,'법정동코드':'0000000000'})
 req=urllib.request.Request(BASE+ep+'?'+q,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/','Origin':'https://data.kbland.kr'})
 with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)

def numeric_count(x):
 if isinstance(x,dict):return sum(numeric_count(v) for v in x.values())
 if isinstance(x,list):return sum(numeric_count(v) for v in x)
 return int(isinstance(x,(int,float)) and not isinstance(x,bool))

def extract_seoul(payload,label,value_key):
 data=((payload or {}).get('dataBody') or {}).get('data') or {}
 rows=data.get(label) or []
 seoul=next((x for x in rows if str(x.get('법정동코드'))=='1100000000' or str(x.get('지역명'))=='서울'),None)
 if not seoul:return None
 raw=seoul.get('현재데이터')
 if raw is None:raw=seoul.get(value_key)
 if raw in (None,''):return None
 return {
  'date':str(seoul.get('통계기준년월일시') or ''),
  'value':float(raw),
  'display_value':seoul.get(value_key),
  'change_pct':float(seoul.get('변동률')) if seoul.get('변동률') not in (None,'') else None
 }

def fetch_point(ep,label,value_key,dt):
 try:
  payload=fetch(ep,dt)
  row=extract_seoul(payload,label,value_key)
  return (dt,row,payload) if row else (dt,None,payload)
 except Exception:
  return (dt,None,None)

def history_for(ep,label,value_key,n=16):
 dates=mondays(n)
 rows=[];payloads={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
  futs=[ex.submit(fetch_point,ep,label,value_key,dt) for dt in dates]
  for fut in concurrent.futures.as_completed(futs):
   dt,row,payload=fut.result()
   if payload is not None:payloads[dt]=payload
   if row:rows.append(row)
 dedup={r['date']:r for r in rows if r.get('date')}
 hist=sorted(dedup.values(),key=lambda x:x['date'])
 return hist,payloads

def nearest_at_or_before(hist,target):
 a=[x for x in hist if x.get('date') and x['date']<=target.strftime('%Y%m%d')]
 return a[-1] if a else None

def momentum(hist):
 if not hist:return None
 latest=hist[-1]
 try:ld=datetime.datetime.strptime(latest['date'],'%Y%m%d').date()
 except:return None
 p4=nearest_at_or_before(hist,ld-datetime.timedelta(days=28))
 p13=nearest_at_or_before(hist,ld-datetime.timedelta(days=91))
 def pct(base):
  return round((latest['value']/base['value']-1)*100,2) if base and base.get('value') else None
 return {
  'as_of':latest['date'],'index':latest['value'],
  'four_week_base_date':p4.get('date') if p4 else None,'four_week_base_index':p4.get('value') if p4 else None,'mom_4w_pct':pct(p4),
  'thirteen_week_base_date':p13.get('date') if p13 else None,'thirteen_week_base_index':p13.get('value') if p13 else None,'mom_13w_pct':pct(p13),
  'definition':'KB 서울 주간 매매가격지수 최신값 대비 4주/13주 전 변화율'
 }

def main():
 out={}
 for kind,(ep,label,value_key) in TARGETS.items():
  n=16 if kind=='sale' else 3
  hist,payloads=history_for(ep,label,value_key,n)
  if not hist:raise SystemExit(f'no live numeric payload: {kind}')
  latest=hist[-1]
  newest_query=max(payloads) if payloads else mondays(1)[0]
  out[kind]={'date':newest_query,'endpoint':BASE+ep,'numeric_fields':numeric_count(payloads.get(newest_query) or {}),'payload':payloads.get(newest_query),'history':hist}
  doc={'status':'connected','source':'KB부동산 데이터허브 statusBoard','region':'서울','frequency':'weekly',
       'latest':latest,'endpoint':BASE+ep,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  if kind=='sale':
   doc['history']=hist
   doc['momentum']=momentum(hist)
   doc['momentum_source']='KB 서울 주간 아파트 매매가격지수'
  target=ROOT/('data_sources/kb_weekly_sale_index.json' if kind=='sale' else 'data_sources/kb_weekly_rent_index.json')
  target.write_text(json.dumps(doc,ensure_ascii=False,indent=2))
 p=ROOT/'data_sources/kb_statusboard_live.json';p.parent.mkdir(exist_ok=True)
 p.write_text(json.dumps({'status':'connected','source':'KB부동산 데이터허브','query':{'법정동코드':'0000000000'},'targets':out,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()},ensure_ascii=False,indent=2))
 print(json.dumps({'sale_latest':out['sale']['history'][-1],'sale_points':len(out['sale']['history']),'sale_momentum':momentum(out['sale']['history']),'rent_latest':out['rent']['history'][-1]},ensure_ascii=False))

if __name__=='__main__':main()
