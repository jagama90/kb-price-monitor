#!/usr/bin/env python3
"""Collect production monthly BOK ECOS mortgage lending rate."""
import os,json,urllib.request,pathlib,datetime,time
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/ecos_mortgage_rate.json'
CODE='121Y006';CYCLE='M'
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
 now=datetime.date.today();start='200601';end=f'{now.year}12'
 u=f'https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/5000/{CODE}/{CYCLE}/{start}/{end}/'
 rows=get(u).get('StatisticSearch',{}).get('row',[])
 hits=[]
 for r in rows:
  names=' '.join(str(r.get(k) or '') for k in ('ITEM_NAME1','ITEM_NAME2','ITEM_NAME3'))
  if '주택담보대출' in names and r.get('DATA_VALUE') not in (None,''):
   hits.append({'period':r.get('TIME'),'rate_pct':float(r['DATA_VALUE']),'item':names.strip()})
 hits.sort(key=lambda x:x['period'] or '')
 if not hits:raise SystemExit('no mortgage rate rows')
 aggregate=[x for x in hits if '고정형' not in x['item'] and '변동형' not in x['item']]
 latest=max(aggregate,key=lambda x:x['period']) if aggregate else hits[-1]
 p={'status':'connected','source':'한국은행 ECOS','stat_code':CODE,'stat_name':'예금은행 대출금리(신규취급액 기준)','series':hits,'latest':latest,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(p,ensure_ascii=False,indent=2));print(json.dumps({'rows':len(hits),'latest':latest},ensure_ascii=False))
if __name__=='__main__':main()
