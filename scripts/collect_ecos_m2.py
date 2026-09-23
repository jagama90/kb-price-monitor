#!/usr/bin/env python3
import os,json,urllib.request,pathlib,datetime,time,random
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/ecos_m2.json'
def get(url):
 last=None
 for attempt in range(5):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'kb-price-monitor/1.0'})
   return json.load(urllib.request.urlopen(req,timeout=60))
  except Exception as e:
   last=e
   if attempt==4: break
   time.sleep(min(20,2**attempt+random.random()))
 raise last
def main():
 key=os.getenv('BOK_ECOS_KEY')
 if not key: raise SystemExit('BOK_ECOS_KEY secret is required')
 base=f'https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/10000/101Y003/M/201601/202612/'
 rows=get(base).get('StatisticSearch',{}).get('row',[])
 # Never guess an ECOS item code. Identify official M2 rows by the ECOS item name,
 # and retain both raw and selected rows so schema changes are auditable.
 def name(r): return ' '.join(str(r.get(k) or '') for k in ('ITEM_NAME1','ITEM_NAME2','ITEM_NAME3','ITEM_NAME4'))
 candidates=[r for r in rows if 'M2' in name(r) or '광의통화' in name(r)]
 items={}
 for r in candidates:
  keytuple=tuple((r.get(k) or '') for k in ('ITEM_CODE1','ITEM_CODE2','ITEM_CODE3','ITEM_NAME1','ITEM_NAME2','ITEM_NAME3'))
  items.setdefault(keytuple,[]).append(r)
 # Prefer a level/amount series; growth rates are calculated from one consistent level series.
 level=[];selected_key=None
 for k,a in items.items():
  nm=' '.join(map(str,k))
  if ('평잔' in nm or '말잔' in nm or '광의통화' in nm or 'M2' in nm) and not any(x in nm for x in ('증감률','전년','증가율')):
   if len(a)>len(level): level=a;selected_key=k
 level=sorted(level,key=lambda r:str(r.get('TIME','')))
 series=[]
 for r in level:
  try: series.append({'period':str(r['TIME']), 'value':float(str(r['DATA_VALUE']).replace(',',''))})
  except: pass
 enriched=[]
 for i,x in enumerate(series):
  mom=round((x['value']/series[i-1]['value']-1)*100,2) if i>=1 and series[i-1]['value'] else None
  yoy=round((x['value']/series[i-12]['value']-1)*100,2) if i>=12 and series[i-12]['value'] else None
  enriched.append({**x,'mom_pct':mom,'yoy_pct':yoy})
 out={'source':'한국은행 ECOS','table':'101Y003','definition':'광의통화(M2) 동일 수준계열에서 MoM/YoY 계산','selected_item':selected_key,'series':enriched,'candidate_item_count':len(items),'raw_row_count':len(rows),'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({'collector':'ECOS M2','raw_rows':len(rows),'candidate_items':len(items),'selected_points':len(enriched),'latest':enriched[-1] if enriched else None},ensure_ascii=False))
if __name__=='__main__':main()
