#!/usr/bin/env python3
"""Fetch tiny real-value samples from discovered ECOS finance tables."""
import os,json,urllib.request,pathlib,datetime,time
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'data_sources/ecos_finance_sample.json'
TERMS={'mortgage':'주택담보대출','household_credit':'가계신용','loan_rate':'대출금리'}
def get(u):
 for n in range(4):
  try:
   with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'kb-price-monitor/1.0'}),timeout=25) as r:return json.load(r)
  except Exception:
   if n==3: raise
   time.sleep(2**n)
def span(c):
 return {'M':('202501','202612'),'Q':('2025Q1','2026Q4'),'A':('2024','2026')}.get(c,('202501','202612'))
def main():
 key=os.getenv('BOK_ECOS_KEY')
 if not key: raise SystemExit('BOK_ECOS_KEY required')
 tables=get(f'https://ecos.bok.or.kr/api/StatisticTableList/{key}/json/kr/1/1000/').get('StatisticTableList',{}).get('row',[])
 out={}
 for k,term in TERMS.items():
  hits=[x for x in tables if term in str(x.get('STAT_NAME','')) and x.get('CYCLE') in ('M','Q','A')]
  sample=None
  for h in hits[:8]:
   code,cy=h.get('STAT_CODE'),h.get('CYCLE'); a,b=span(cy)
   try:
    rows=get(f'https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/30/{code}/{cy}/{a}/{b}/').get('StatisticSearch',{}).get('row',[])
    vals=[r for r in rows if r.get('DATA_VALUE') not in (None,'')]
    if vals:
     sample={'stat_code':code,'stat_name':h.get('STAT_NAME'),'cycle':cy,'rows':[{'time':r.get('TIME'),'item':r.get('ITEM_NAME1'),'item2':r.get('ITEM_NAME2'),'value':r.get('DATA_VALUE')} for r in vals[-3:]]};break
   except Exception: pass
  out[k]={'term':term,'table_hits':len(hits),'sample':sample,'sample_value_ok':bool(sample)}
 payload={'source':'한국은행 ECOS','mode':'real_value_sample','results':out,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2));print(json.dumps(payload,ensure_ascii=False))
 if not any(v['sample_value_ok'] for v in out.values()): raise SystemExit('no finance value sample retrieved')
if __name__=='__main__':main()
