#!/usr/bin/env python3
"""Collect REB R-ONE long-cycle inputs. Full history requires RONE_API_KEY."""
import os,json,urllib.parse,urllib.request,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'data_sources/reb_long_cycle.json'
BASE='https://www.reb.or.kr/r-one/openapi/'
def get(ep,p):
 q=urllib.parse.urlencode(p)
 with urllib.request.urlopen(urllib.request.Request(BASE+ep+'?'+q,headers={'User-Agent':'kb-price-monitor/1.0'}),timeout=45) as r:return json.load(r)
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
def main():
 key=os.getenv('RONE_API_KEY','sample')
 # Known current R-ONE Seoul real-transaction price table; trade table remains metadata-discovered.
 price_params={'KEY':key,'Type':'json','STATBL_ID':'A_2024_00045','DTACYCLE_CD':'MM','CLS_ID':'500008','ITM_ID':'100001','START_WRTTIME':'2006','END_WRTTIME':'2024','pIndex':1,'pSize':5000}
 price_raw=get('SttsApiTblData.do',price_params)
 price=[norm(x) for x in rows(price_raw,'SttsApiTblData') if norm(x)['ym']]
 if not price:
  (R/'data_sources/reb_price_debug.json').write_text(json.dumps(price_raw,ensure_ascii=False,indent=2))
 catalog=get('SttsApiTbl.do',{'KEY':key,'Type':'json','pIndex':1,'pSize':1000})
 out={'status':'full' if key!='sample' else 'sample_limited','source':'한국부동산원 R-ONE',
      'target_start':'2006-01','price_contract':{'statbl_id':'A_2024_00045','cls_id':'500008','itm_id':'100001'},
      'series':{'price':price,'trade':[]},'table_catalog':catalog,
      'blockers':([] if key!='sample' else ['RONE_API_KEY required for full history']),
      'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({'status':out['status'],'price_rows':len(price),'trade_rows':0,'blockers':out['blockers']},ensure_ascii=False))
if __name__=='__main__':main()





