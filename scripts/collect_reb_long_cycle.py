#!/usr/bin/env python3
"""Collect REB R-ONE long-cycle inputs. Full history requires RONE_API_KEY."""
import os,json,urllib.parse,urllib.request,pathlib,datetime,time,random
from zoneinfo import ZoneInfo
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'data_sources/reb_long_cycle.json'
BASE='https://www.reb.or.kr/r-one/openapi/'
def get(ep,p):
 q=urllib.parse.urlencode(p); last=None
 for attempt in range(5):
  try:
   with urllib.request.urlopen(urllib.request.Request(BASE+ep+'?'+q,headers={'User-Agent':'kb-price-monitor/1.0'}),timeout=45) as r:return json.load(r)
  except Exception as e:
   last=e
   if attempt<4: time.sleep(min(20,2**attempt+random.random()))
 raise last
def rows(x,key):
 v=x.get(key,[])
 if isinstance(v,list):
  for z in v:
   if isinstance(z,dict) and isinstance(z.get('row'),list): return z['row']
 return []
def norm(r):
 return {'ym':str(r.get('WRTTIME_IDTFR_ID') or '').replace('.','').replace('-','')[:6],
         'value':float(r['DTA_VAL']) if r.get('DTA_VAL') not in (None,'') else None,
         'statbl_id':r.get('STATBL_ID'),'cls_id':r.get('CLS_ID'),'cls_name':r.get('CLS_NM'),
         'itm_id':r.get('ITM_ID'),'itm_name':r.get('ITM_NM'),'unit':r.get('UI_NM')}
def month_range(year,last_ym):
 out=[]
 for m in range(1,13):
  ym=f'{year:04d}{m:02d}'
  if ym<=last_ym: out.append(ym)
 return out
def fill_tail(key,statbl_id,cls_id,itm_id,series,last_ym):
 by={x['ym']:x for x in series if x.get('ym')}
 for ym in month_range(int(last_ym[:4]),last_ym):
  if ym in by: continue
  try:
   raw=get('SttsApiTblData.do',{'KEY':key,'Type':'json','STATBL_ID':statbl_id,'DTACYCLE_CD':'MM','CLS_ID':cls_id,'ITM_ID':itm_id,'WRTTIME_IDTFR_ID':ym,'pIndex':1,'pSize':1000})
   for x in rows(raw,'SttsApiTblData'):
    z=norm(x)
    if z.get('ym')==ym and z.get('value') is not None:
     by[ym]=z;break
  except Exception:
   pass
 return [by[k] for k in sorted(by)]
def main():
 key=os.getenv('RONE_API_KEY','sample')
 today=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date(); end_year=str(today.year)
 prev_month=(today.replace(day=1)-datetime.timedelta(days=1)).strftime('%Y%m')
 # Known current R-ONE Seoul real-transaction price table; always request through the current year.
 price_params={'KEY':key,'Type':'json','STATBL_ID':'A_2024_00045','DTACYCLE_CD':'MM','CLS_ID':'500008','ITM_ID':'100001','START_WRTTIME':'2006','END_WRTTIME':end_year,'pIndex':1,'pSize':1000}
 price_raw=get('SttsApiTblData.do',price_params)
 price=[norm(x) for x in rows(price_raw,'SttsApiTblData') if norm(x)['ym']]
 price=fill_tail(key,'A_2024_00045','500008','100001',price,prev_month)
 if not price:
  (R/'data_sources/reb_price_debug.json').write_text(json.dumps(price_raw,ensure_ascii=False,indent=2))
 # Discover valid Seoul CLS/ITM pairs for the transaction-status table from a single month.
 trade_probe=get('SttsApiTblData.do',{'KEY':key,'Type':'json','STATBL_ID':'A_2024_00549','DTACYCLE_CD':'MM','WRTTIME_IDTFR_ID':prev_month,'pIndex':1,'pSize':1000})
 trade_probe_rows=rows(trade_probe,'SttsApiTblData')
 trade_candidates=[{'cls_id':x.get('CLS_ID'),'cls_name':x.get('CLS_NM'),'cls_fullname':x.get('CLS_FULLNM'),
                    'itm_id':x.get('ITM_ID'),'itm_name':x.get('ITM_NM'),'itm_fullname':x.get('ITM_FULLNM'),
                    'unit':x.get('UI_NM'),'value':x.get('DTA_VAL')}
                   for x in trade_probe_rows if '서울' in str(x.get('CLS_FULLNM') or x.get('CLS_NM') or '')]
 (R/'data_sources/reb_trade_debug.json').write_text(json.dumps({'probe':trade_probe,'seoul_candidates':trade_candidates},ensure_ascii=False,indent=2))
 trade_params={'KEY':key,'Type':'json','STATBL_ID':'A_2024_00549','DTACYCLE_CD':'MM','CLS_ID':'500002','ITM_ID':'100001','START_WRTTIME':'2006','END_WRTTIME':end_year,'pIndex':1,'pSize':1000}
 trade_raw=get('SttsApiTblData.do',trade_params)
 trade=[norm(x) for x in rows(trade_raw,'SttsApiTblData') if norm(x)['ym']]
 trade=fill_tail(key,'A_2024_00549','500002','100001',trade,prev_month)
 if not trade:
  (R/'data_sources/reb_trade_debug.json').write_text(json.dumps({'probe':trade_probe,'full_request':trade_raw,'seoul_candidates':trade_candidates},ensure_ascii=False,indent=2))
 catalog=get('SttsApiTbl.do',{'KEY':key,'Type':'json','pIndex':1,'pSize':1000})
 out={'status':'full' if key!='sample' else 'sample_limited','source':'한국부동산원 R-ONE',
      'target_start':'2006-01','price_contract':{'statbl_id':'A_2024_00045','cls_id':'500008','itm_id':'100001'},
      'trade_contract':{'statbl_id':'A_2024_00549','cls_id':'500002','itm_id':'100001','itm_name':'동(호)수'},
      'trade_discovery':{'statbl_id':'A_2024_00549','probe_month':prev_month,'seoul_candidates':trade_candidates},
      'series':{'price':price,'trade':trade},'table_catalog':catalog,
      'blockers':([] if key!='sample' else ['RONE_API_KEY required for full history']),
      'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({'status':out['status'],'price_rows':len(price),'trade_rows':len(trade),'blockers':out['blockers']},ensure_ascii=False))
if __name__=='__main__':main()





