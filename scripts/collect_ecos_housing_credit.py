#!/usr/bin/env python3
"""Discover and collect an official ECOS housing-credit balance series.

The collector deliberately does not guess a statistic code. It discovers
monthly ECOS tables, selects a sufficiently long series whose item labels
explicitly identify housing-mortgage lending, and records the chosen lineage.
If a trustworthy series cannot be identified, it emits status=not_connected.
"""
import datetime,json,os,pathlib,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data_sources/ecos_housing_credit.json'
BASE='https://ecos.bok.or.kr/api'

def fetch_json(url,timeout=20):
 req=urllib.request.Request(url,headers={'User-Agent':'kb-price-monitor/1.0'})
 return json.loads(urllib.request.urlopen(req,timeout=timeout).read())

def fnum(v):
 try:return float(str(v).replace(',',''))
 except:return None

def api(key,name,start,end,*parts):
 path='/'.join(urllib.parse.quote(str(x),safe='') for x in parts)
 url=f'{BASE}/{name}/{key}/json/kr/{start}/{end}'
 if path:url+='/'+path
 return fetch_json(url)

def table_rows(key):
 j=api(key,'StatisticTableList',1,10000)
 return ((j.get('StatisticTableList') or {}).get('row') or [])

def search_rows(key,code,start='200001',end='202612'):
 j=api(key,'StatisticSearch',1,10000,code,'M',start,end)
 return ((j.get('StatisticSearch') or {}).get('row') or [])

def select_series(rows,table_name):
 groups={}
 for r in rows:
  period=str(r.get('TIME') or '')
  if len(period)!=6 or not period.isdigit():continue
  value=fnum(r.get('DATA_VALUE'))
  if value is None:continue
  names=tuple(str(r.get(f'ITEM_NAME{i}') or '').strip() for i in range(1,5))
  label=' '.join(x for x in names if x)
  unit=str(r.get('UNIT_NAME') or '').strip()
  if '주택담보대출' not in label and '주택담보대출' not in table_name:continue
  if any(bad in (table_name+' '+label) for bad in ('연체율','대출금리','금리수준','증가율')):continue
  groups.setdefault((names,unit),{})[period]=value
 candidates=[]
 for (names,unit),by_period in groups.items():
  periods=sorted(by_period)
  if len(periods)<36:continue
  label=' / '.join(x for x in names if x)
  score=min(len(periods),240)/10
  if '주택담보대출' in label:score+=40
  if '가계대출' in (table_name+' '+label):score+=12
  if '예금은행' in (table_name+' '+label):score+=8
  if '잔액' in (table_name+' '+label):score+=5
  if unit in ('십억원','억원','백만원'):score+=2
  candidates.append({'score':round(score,2),'names':names,'label':label,'unit':unit,'periods':periods,'values':by_period})
 return sorted(candidates,key=lambda x:(x['score'],x['periods'][-1],len(x['periods'])),reverse=True)

def enrich(selected):
 periods=selected['periods'];vals=selected['values'];out=[]
 for i,p in enumerate(periods):
  v=vals[p];prev=vals.get(periods[i-1]) if i else None
  yprev=vals.get(f'{int(p[:4])-1:04d}{p[4:]}')
  out.append({
   'period':p,'value':v,
   'mom_change':round(v-prev,4) if prev is not None else None,
   'mom_pct':round((v/prev-1)*100,4) if prev not in (None,0) else None,
   'yoy_change':round(v-yprev,4) if yprev is not None else None,
   'yoy_pct':round((v/yprev-1)*100,4) if yprev not in (None,0) else None,
  })
 return out

def main():
 key=os.getenv('BOK_ECOS_KEY')
 payload={'status':'not_connected','source':'한국은행 ECOS','candidate_feature':'credit_availability','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 if not key:
  payload['reason']='BOK_ECOS_KEY missing'
  OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return
 try:
  tables=[]
  for t in table_rows(key):
   name=str(t.get('STAT_NAME') or '')
   cycle=str(t.get('CYCLE') or '')
   if cycle=='M' and ('가계대출' in name or '주택담보대출' in name):
    tables.append((str(t.get('STAT_CODE') or ''),name))
  all_candidates=[]
  for code,name in tables[:10]:
   try:
    rows=search_rows(key,code)
   except Exception:
    continue
   for c in select_series(rows,name):
    all_candidates.append({**c,'stat_code':code,'stat_name':name})
  all_candidates.sort(key=lambda x:(x['score'],x['periods'][-1],len(x['periods'])),reverse=True)
  if not all_candidates:
   payload.update({'reason':'No monthly ECOS housing-mortgage balance candidate with >=36 observations','tables_checked':len(tables),'table_candidates':[{'stat_code':c,'stat_name':n} for c,n in tables]})
  else:
   s=all_candidates[0];series=enrich(s)
   payload.update({
    'status':'connected','stat_code':s['stat_code'],'stat_name':s['stat_name'],
    'item_names':list(s['names']),'item_label':s['label'],'unit':s['unit'],
    'series':series,'latest':series[-1],'observations':len(series),
    'selection_rule':'monthly official ECOS series; explicit 주택담보대출 item; >=36 observations; prefer household/bank balance lineage',
    'alternative_candidates':[{'stat_code':x['stat_code'],'stat_name':x['stat_name'],'item_label':x['label'],'unit':x['unit'],'observations':len(x['periods']),'latest_period':x['periods'][-1],'score':x['score']} for x in all_candidates[:5]],
   })
 except Exception as e:
  payload['reason']='collector_error: '+repr(e)[:300]
 OUT.parent.mkdir(exist_ok=True)
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':payload.get('status'),'stat_code':payload.get('stat_code'),'item':payload.get('item_label'),'observations':payload.get('observations'),'reason':payload.get('reason')},ensure_ascii=False))

if __name__=='__main__':main()
