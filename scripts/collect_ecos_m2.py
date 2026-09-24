#!/usr/bin/env python3
import os,json,urllib.request,pathlib,datetime,time,random
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/ecos_m2.json'
def get(url):
 last=None
 for attempt in range(8):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'kb-price-monitor/1.0'})
   return json.load(urllib.request.urlopen(req,timeout=35))
  except Exception as e:
   last=e
   if attempt==7: break
   time.sleep(min(30,2**attempt+random.random()*2))
 raise last
def main():
 key=os.getenv('BOK_ECOS_KEY')
 if not key: raise SystemExit('BOK_ECOS_KEY secret is required')
 # Discover the official M2 table instead of hard-coding a code that may change.
 tables=get(f'https://ecos.bok.or.kr/api/StatisticTableList/{key}/json/kr/1/10000/').get('StatisticTableList',{}).get('row',[])
 hits=[r for r in tables if r.get('CYCLE')=='M' and ('광의통화' in str(r.get('STAT_NAME','')) or 'M2' in str(r.get('STAT_NAME','')))]
 rows=[];selected_table=None
 for h in hits:
  code=h.get('STAT_CODE')
  try:
   trial=get(f'https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/10000/{code}/M/201601/202612/').get('StatisticSearch',{}).get('row',[])
   if trial:
    rows=trial;selected_table={'stat_code':code,'stat_name':h.get('STAT_NAME')};break
  except Exception: pass
 def name(r): return ' '.join(str(r.get(k) or '') for k in ('ITEM_NAME1','ITEM_NAME2','ITEM_NAME3','ITEM_NAME4'))
 candidates=[r for r in rows if 'M2' in name(r) or '광의통화' in name(r)]
 # Some official M2 tables name the table itself M2 and item rows only say 평잔/말잔.
 if not candidates and selected_table: candidates=rows
 items={}
 for r in candidates:
  k=tuple((r.get(x) or '') for x in ('ITEM_CODE1','ITEM_CODE2','ITEM_CODE3','ITEM_NAME1','ITEM_NAME2','ITEM_NAME3'))
  items.setdefault(k,[]).append(r)
 level=[];selected_key=None
 for k,a in items.items():
  nm=' '.join(map(str,k))
  if not any(x in nm for x in ('증감률','전년','증가율','원계열대비')):
   if len(a)>len(level): level=a;selected_key=k
 level=sorted(level,key=lambda r:str(r.get('TIME','')))
 series=[]
 for r in level:
  try: series.append({'period':str(r['TIME']),'value':float(str(r['DATA_VALUE']).replace(',',''))})
  except: pass
 enriched=[]
 for i,x in enumerate(series):
  mom=round((x['value']/series[i-1]['value']-1)*100,2) if i>=1 and series[i-1]['value'] else None
  yoy=round((x['value']/series[i-12]['value']-1)*100,2) if i>=12 and series[i-12]['value'] else None
  enriched.append({**x,'mom_pct':mom,'yoy_pct':yoy})
 out={'source':'한국은행 ECOS','table':selected_table,'definition':'광의통화(M2) 동일 수준계열에서 MoM/YoY 계산','selected_item':selected_key,'series':enriched,'candidate_item_count':len(items),'raw_row_count':len(rows),'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({'collector':'ECOS M2','table':selected_table,'table_hits':len(hits),'raw_rows':len(rows),'candidate_items':len(items),'selected_points':len(enriched),'latest':enriched[-1] if enriched else None},ensure_ascii=False))
 if not enriched: raise SystemExit('ECOS M2 discovery returned no usable level series')
if __name__=='__main__':main()
