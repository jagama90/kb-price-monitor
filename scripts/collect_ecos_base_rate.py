#!/usr/bin/env python3
"""Collect Bank of Korea base-rate history from ECOS."""
import os,json,urllib.request,pathlib,datetime,time
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/ecos_base_rate.json'
CODE='722Y001';ITEM='0101000';CYCLE='D'
def get(u):
 for n in range(4):
  try:
   with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'kb-price-monitor/1.0'}),timeout=25) as r:return json.load(r)
  except Exception:
   if n==3:raise
   time.sleep(2**n)
def main():
 key=os.getenv('BOK_ECOS_KEY')
 if not key:raise SystemExit('BOK_ECOS_KEY required')
 today=datetime.date.today();start='20160101';end=today.strftime('%Y%m%d')
 u=f'https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/10000/{CODE}/{CYCLE}/{start}/{end}/{ITEM}/'
 rows=get(u).get('StatisticSearch',{}).get('row',[])
 obs=[]
 for r in rows:
  if r.get('DATA_VALUE') in (None,'') or not r.get('TIME'):continue
  try:v=float(r['DATA_VALUE'])
  except:continue
  obs.append({'date':str(r['TIME']),'rate_pct':v,'item':r.get('ITEM_NAME1') or r.get('ITEM_NAME2') or '한국은행 기준금리'})
 obs.sort(key=lambda x:x['date'])
 if not obs:raise SystemExit('no BOK base-rate observations')
 changes=[];prev=None
 for x in obs:
  if prev is None or x['rate_pct']!=prev:
   changes.append(x)
   prev=x['rate_pct']
 payload={'status':'connected','source':'한국은행 ECOS','stat_code':CODE,'item_code':ITEM,'frequency':'daily',
  'latest':obs[-1],'latest_observation_date':obs[-1]['date'],'series':changes,
  'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 print(json.dumps({'observations':len(obs),'change_points':len(changes),'latest':obs[-1]},ensure_ascii=False))
if __name__=='__main__':main()
