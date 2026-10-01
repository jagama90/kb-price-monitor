#!/usr/bin/env python3
import datetime,json,pathlib,urllib.parse,urllib.request,urllib.error,re,sys,io
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data_sources/molit_structural_supply.json'
SCOPE=json.loads((ROOT/'config/market_scope.json').read_text(encoding='utf-8'))
REGION=(SCOPE.get('region') or {})
REGION_LABEL=str(REGION.get('label') or '')
REGION_CODE=str(REGION.get('code') or '')
if not REGION_LABEL: raise RuntimeError('market_scope.region.label is required')
BASE='https://stat.molit.go.kr/portal/cate/statView.do'
SERIES={
 'permit':{'hRsId':'31','hFormId':'1948','label':'주택건설실적통계(인허가)'},
 'start':{'hRsId':'471','hFormId':'5386','label':'주택건설실적통계(착공)'},
 'completion':{'hRsId':'468','hFormId':'5373','label':'주택건설실적통계(준공)'},
}
def shift(y,m,d):
 q=y*12+(m-1)+d
 return q//12,q%12+1
def fetch_html(kind,start,end):
 spec=SERIES[kind]
 q={'hAppr':'1','hPoint':'00','hRsId':spec['hRsId'],'hFormId':spec['hFormId'],'hSelectId':spec['hFormId'],
    'hDivEng':'','oFileName':'','rFileName':'','midpath':'','month_yn':'N','sFormId':spec['hFormId'],'sStart':start,'sEnd':end,'sStyleNum':'1','EXPORT':''}
 u=BASE+'?'+urllib.parse.urlencode(q)
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'text/html,application/xhtml+xml','Referer':'https://stat.molit.go.kr/'})
 with urllib.request.urlopen(req,timeout=30) as r:
  return r.read().decode('utf-8','replace'),u
def flatten(x):
 if isinstance(x,tuple): return ' '.join(str(v) for v in x if str(v)!='nan')
 return str(x)
def parse(kind,html):
 try:
  import pandas as pd
 except Exception as e:
  raise RuntimeError('pandas is required in workflow: '+repr(e))
 tables=pd.read_html(io.StringIO(html))
 candidates=[]
 for ti,t in enumerate(tables):
  t.columns=[flatten(c) for c in t.columns]
  for ri,row in t.iterrows():
   vals=[str(v).strip() for v in row.tolist()]
   joined=' | '.join(vals)
   if REGION_LABEL in joined:
    candidates.append((ti,ri,t,row,joined))
 if not candidates:
  previews=[]
  for i,t in enumerate(tables[:6]):
   previews.append({'table':i,'shape':list(t.shape),'columns':[str(c) for c in t.columns[:12]],'head':t.head(3).astype(str).values.tolist()})
  raise RuntimeError('region row not found '+REGION_LABEL+' '+json.dumps(previews,ensure_ascii=False)[:5000])
 rows=[]
 for ti,ri,t,row,joined in candidates:
  vals=[]
  for c,v in row.items():
   s=str(v).replace(',','').strip()
   if re.fullmatch(r'-?\d+(?:\.\d+)?',s):
    try: vals.append((str(c),float(s)))
    except: pass
  if vals:
   rows.append({'table':ti,'row':int(ri),'joined':joined,'numbers':vals})
 # Prefer rows where region appears as its own cell and use the first non-month numeric value after it.
 best=None
 for r in rows:
  parts=[x.strip() for x in r['joined'].split('|')]
  exact=REGION_LABEL in parts
  score=(1 if exact else 0,len(r['numbers']))
  if best is None or score>best[0]: best=(score,r)
 if best is None: raise RuntimeError('region rows had no numeric values: '+json.dumps(rows[:10],ensure_ascii=False))
 return best[1],len(tables),len(candidates)
def main():
 today=datetime.date.today(); y,m=shift(today.year,today.month,-1);end=f'{y:04d}{m:02d}';sy,sm=shift(y,m,-23);start=f'{sy:04d}{sm:02d}'
 out={'status':'connected','source':'국토교통부 국토교통통계누리 승인통계',
      'scope':{'market_scope_id':SCOPE.get('market_scope_id'),'region_code':REGION_CODE,'region_label':REGION_LABEL},
      'period_query':{'start':start,'end':end},'series':{},'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'official_meta':{'permit':'https://stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=31',
                       'start':'https://stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=471',
                       'completion':'https://stat.molit.go.kr/portal/cate/statMetaView.do?hRsId=468'}}
 failures=[]
 for kind in SERIES:
  spec=SERIES[kind];html='';url=''
  try:
   html,url=fetch_html(kind,start,end);row,nt,nc=parse(kind,html)
   out['series'][kind]={'status':'connected_probe','official_name':spec['label'],'query_url':url,'table_count':nt,'region_candidate_rows':nc,'selected_row':row}
   print(json.dumps({'kind':kind,'status':'connected','tables':nt,'candidates':nc},ensure_ascii=False),flush=True)
  except Exception as e:
   failures.append(kind)
   unreachable=isinstance(e,(urllib.error.URLError,TimeoutError))
   state='source_unreachable_from_actions' if unreachable else 'parse_error'
   links=[]
   if html:
    links=list(dict.fromkeys(re.findall(r'''[A-Za-z0-9_./?=&%:-]+\.do[^"'<> ]*''',html)))[:40]
   out['series'][kind]={'status':state,'official_name':spec['label'],'query_url':url or None,'official_meta_url':out['official_meta'][kind],
                        'error':repr(e)[:300],'html_diagnostics':{'length':len(html),'do_links':links}}
   print(json.dumps({'kind':kind,'status':state,'error':repr(e)[:200],'do_links':links[:15]},ensure_ascii=False),flush=True)
 if failures:
  states=[(out['series'].get(k) or {}).get('status') for k in failures]
  out['status']='partial_connected' if len(failures)<len(SERIES) else ('source_unreachable_from_actions' if all(x=='source_unreachable_from_actions' for x in states) else 'parse_error')
  out['automation_blocker']='official source could not be fully parsed/reached in this run; no values were fabricated or copied from secondary sources'
 OUT.parent.mkdir(exist_ok=True)
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':out['status'],'failures':failures,'out':str(OUT),'region':REGION_LABEL},ensure_ascii=False))
 return 0

if __name__=='__main__':main()
