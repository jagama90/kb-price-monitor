#!/usr/bin/env python3
import os,json,datetime,urllib.parse,urllib.request,xml.etree.ElementTree as ET,pathlib,calendar,time,random
from concurrent.futures import ThreadPoolExecutor,as_completed
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data_sources/molit.json'; VINTAGE=ROOT/'data_sources/molit_daily_history.json'; SHARED=ROOT/'data_sources/.molit_watchlist_pair_cache.json'
SEOUL=['11110','11140','11170','11200','11215','11230','11260','11290','11305','11320','11350','11380','11410','11440','11470','11500','11530','11545','11560','11590','11620','11650','11680','11710','11740']
def request_page(code,ym,key,page,timeout):
 q=urllib.parse.urlencode({'serviceKey':key,'LAWD_CD':code,'DEAL_YMD':ym,'numOfRows':1000,'pageNo':page},safe='%')
 url='https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev?'+q
 req=urllib.request.Request(url,headers={'User-Agent':'kb-price-monitor/1.0'})
 return ET.fromstring(urllib.request.urlopen(req,timeout=timeout).read())

def item_value(it,*names):
 for n in names:
  v=it.findtext(n)
  if v is not None and str(v).strip():return str(v).strip()
 return ''

def fetch_all(code,ym,key,timeout):
 rows=[];page=1;fetched=0
 while True:
  root=request_page(code,ym,key,page,timeout);items=root.findall('.//item');fetched+=len(items)
  for it in items:
   s=item_value(it,'dealAmount','거래금액').replace(',','').strip();day=item_value(it,'dealDay','일')
   if s.isdigit():
    try:dd=int(day)
    except:dd=0
    rows.append((dd,int(s)))
  total=int(root.findtext('.//totalCount') or len(rows))
  if not items or fetched>=total:break
  page+=1
  if page>100:raise RuntimeError(f'pagination guard {code} {ym}')
 return rows

def cache_key(code,ym):
 return f'{code}:{ym}'

def decode_cache(previous):
 raw=previous.get('pair_cache') or {}
 out={}
 for k,v in raw.items():
  try:
   code,ym=k.split(':',1)
   if code in SEOUL and len(ym)==6:
    out[(code,ym)]=[(int(x[0]),int(x[1])) for x in (v or [])]
  except Exception:
   pass
 return out

def decode_shared_cache():
 if not SHARED.exists():return {}
 try:
  raw=json.loads(SHARED.read_text(encoding='utf-8'))
 except Exception:return {}
 out={}
 for k,v in raw.items():
  try:
   code,ym=k.split(':',1)
   if code in SEOUL and len(ym)==6:
    out[(code,ym)]=[(int(x[0]),int(x[1])) for x in (v or [])]
  except Exception:
   pass
 return out

def encode_cache(cache,keep_months):
 keep=set(keep_months)
 return {
  cache_key(code,ym):[[int(d),int(p)] for d,p in rows]
  for (code,ym),rows in cache.items() if ym in keep
 }

def _run_pairs(pairs,key,workers,timeout):
 tasks={};results={};errors={};durations={}
 with ThreadPoolExecutor(max_workers=max(1,workers)) as pool:
  for code,ym in pairs:
   started=time.monotonic()
   fut=pool.submit(fetch_all,code,ym,key,timeout)
   tasks[fut]=(code,ym,started)
  for fut in as_completed(tasks):
   code,ym,started=tasks[fut];durations[(code,ym)]=time.monotonic()-started
   try:results[(code,ym)]=fut.result()
   except Exception as e:errors[(code,ym)]=repr(e)
 return results,errors,durations

def fetch_refresh_pairs(pairs,key,workers,cache):
 # First pass is deliberately impatient: one slow district must never pin the
 # entire Seoul refresh for a minute. Only failed district-month pairs get a
 # second, more patient request.
 fast_timeout=max(3,float(os.getenv('MOLIT_FAST_TIMEOUT','8')))
 retry_timeout=max(fast_timeout,float(os.getenv('MOLIT_RETRY_TIMEOUT','20')))
 retry_workers=max(1,min(int(os.getenv('MOLIT_RETRY_WORKERS','2')),4))
 pairs=sorted(set(pairs))
 started=time.monotonic()
 first,failed,durations=_run_pairs(pairs,key,workers,fast_timeout)
 retried=sorted(failed)
 recovered={};retry_failed={};retry_durations={}
 if retried:
  time.sleep(float(os.getenv('MOLIT_RETRY_DELAY','1')))
  recovered,retry_failed,retry_durations=_run_pairs(retried,key,min(retry_workers,len(retried)),retry_timeout)
 results=dict(first);results.update(recovered)
 fallbacks=[]
 for pair,err in retry_failed.items():
  if pair in cache:
   results[pair]=cache[pair]
   fallbacks.append(pair)
  else:
   code,ym=pair
   raise RuntimeError(f'MOLIT pair failed without last-good cache: {code} {ym}: {err}')
 for pair,rows in results.items():
  if pair not in fallbacks:
   cache[pair]=rows
 elapsed=time.monotonic()-started
 slow=sorted(
  [(*pair,round(sec,1),'first') for pair,sec in durations.items()]+
  [(*pair,round(sec,1),'retry') for pair,sec in retry_durations.items()],
  key=lambda x:x[2],reverse=True
 )[:8]
 print(json.dumps({
  'collector':'MOLIT','stage':'adaptive_parallel_fetch',
  'district_month_pairs':len(pairs),'workers':workers,
  'fast_timeout_sec':fast_timeout,'first_pass_failed':len(retried),
  'retry_timeout_sec':retry_timeout,'retry_workers':retry_workers,
  'retry_recovered':len(recovered),'cache_fallbacks':len(fallbacks),
  'fallback_pairs':[cache_key(*x) for x in fallbacks],
  'slowest_pairs':slow,'elapsed_sec':round(elapsed,1)
 },ensure_ascii=False),flush=True)
 return results,cache,{'retried':retried,'fallbacks':fallbacks,'elapsed_sec':elapsed}


def summarize(rows):
 prices=[p for _,p in rows];n=len(prices)
 keys={'<=9eok':sum(p<=90000 for p in prices),'9-15eok':sum(90000<p<=150000 for p in prices),'15-25eok':sum(150000<p<=250000 for p in prices),'25eok+':sum(p>250000 for p in prices)}
 boundary={'13-15eok':sum(130000<p<=150000 for p in prices),'15-17eok':sum(150000<p<=170000 for p in prices),'23-25eok':sum(230000<p<=250000 for p in prices),'25-27eok':sum(250000<p<=270000 for p in prices)}
 return {'total':n,'counts':keys,'boundary_counts':boundary,'under15_share':round((keys['<=9eok']+keys['9-15eok'])*100/n,1) if n else None}
def shift_month(d,delta):
 y=d.year+(d.month-1+delta)//12;m=(d.month-1+delta)%12+1;return y,m
def main():
 key=os.getenv('MOLIT_SERVICE_KEY')
 if not key:raise SystemExit('MOLIT_SERVICE_KEY secret is required')
 OUT.parent.mkdir(exist_ok=True);now=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date();months=[]
 try:
  previous=json.loads(OUT.read_text()) if OUT.exists() else {}
 except Exception: previous={}
 previous_bands={str(x.get('period','')).replace('-',''):x for x in ((previous.get('price_bands') or {}).get('months') or [])}
 for back in range(7):
  y,m=shift_month(now,-back);months.append(f'{y:04d}{m:02d}')
 monthly={};series=[];bands=[]
 pair_cache=decode_cache(previous)
 shared_cache=decode_shared_cache()
 pair_cache.update(shared_cache)
 workers=max(1,min(int(os.getenv('MOLIT_WORKERS','6')),10))

 # Daily: query only the current month (25 district calls). The previous month's
 # raw rows are already available from when it was the current month. Friday is
 # the correction sweep for current/previous/two-months-back.
 weekly_sweep=(now.weekday()==4)
 refresh_count=3 if weekly_sweep else 1
 refresh=set(months[:refresh_count])

 # Reuse district/month responses already downloaded by the watchlist collector
 # earlier in the same job. Persistent cache never suppresses a requested refresh,
 # but same-run shared cache does.
 pairs_to_fetch={(code,ym) for ym in refresh for code in SEOUL if (code,ym) not in shared_cache}
 for code in SEOUL:
  if (code,months[1]) not in pair_cache:
   pairs_to_fetch.add((code,months[1]))
 # Historical bands missing from the repository are repaired lazily.
 for ym in months:
  if ym not in previous_bands:
   for code in SEOUL:
    if (code,ym) not in shared_cache:pairs_to_fetch.add((code,ym))

 fetched,pair_cache,fetch_meta=fetch_refresh_pairs(pairs_to_fetch,key,workers,pair_cache)
 pair_rows=dict(pair_cache);pair_rows.update(fetched)

 for ym in reversed(months):
  if ym not in refresh and ym in previous_bands:
   cached=dict(previous_bands[ym]);cached['period']=ym[:4]+'-'+ym[4:]
   sm={k:cached.get(k) for k in ('total','counts','boundary_counts','under15_share')}
  else:
   rows=[]
   missing=[]
   for code in SEOUL:
    if (code,ym) in pair_rows:rows.extend(pair_rows[(code,ym)])
    else:missing.append(code)
   if missing:raise RuntimeError(f'MOLIT raw pair cache incomplete {ym}: {missing}')
   monthly[ym]=rows;sm=summarize(rows)
  series.append([ym[:4]+'-'+ym[4:],sm['total'],ym==months[0]]);bands.append({'period':ym[:4]+'-'+ym[4:],**sm})

 # Matched-period calculation always needs raw current and previous rows.
 for ym in months[:2]:
  if ym not in monthly:
   rows=[]
   for code in SEOUL:
    pair=(code,ym)
    if pair not in pair_rows:raise RuntimeError(f'MOLIT matched-period cache missing {code} {ym}')
    rows.extend(pair_rows[pair])
   monthly[ym]=rows
 cy,cm=now.year,now.month;py,pm=shift_month(now,-1);cutoff=min(now.day,calendar.monthrange(py,pm)[1]);cur=f'{cy:04d}{cm:02d}';prev=f'{py:04d}{pm:02d}'
 cs=summarize([r for r in monthly.get(cur,[]) if 1<=r[0]<=cutoff]);ps=summarize([r for r in monthly.get(prev,[]) if 1<=r[0]<=cutoff])
 pct=lambda a,b:round((a/b-1)*100,1) if b else None
 matched={'as_of':now.isoformat(),'cutoff_day':cutoff,'basis':'contract_date_equal_calendar_days','current':{'period':f'{cy:04d}-{cm:02d}','range':f'1~{cutoff}일',**cs},'previous':{'period':f'{py:04d}-{pm:02d}','range':f'1~{cutoff}일',**ps},'changes':{'trade_count_pct':pct(cs['total'],ps['total']),'under15_share_pp':round(cs['under15_share']-ps['under15_share'],1) if cs['under15_share'] is not None and ps['under15_share'] is not None else None},'warning':'당월은 계약 후 신고가 추가될 수 있어 조기신호로 사용'}
 cache_months=months[:3]
 out={'source':'MOLIT apartment trade OpenAPI',
      'collected_at':datetime.datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
      'refresh_meta':{
       'mode':'weekly_correction_sweep' if weekly_sweep else 'daily_current_month_only',
       'queried_pairs':len(pairs_to_fetch),
       'reused_watchlist_pairs':len(shared_cache),
       'retried_pairs':[cache_key(*x) for x in fetch_meta['retried']],
       'cache_fallback_pairs':[cache_key(*x) for x in fetch_meta['fallbacks']],
       'elapsed_sec':round(fetch_meta['elapsed_sec'],1)
      },
      'pair_cache':encode_cache(pair_cache,cache_months),
      'seoul_apt_trade_count':series,
      'price_bands':{'status':'partial_last_good' if fetch_meta['fallbacks'] else 'connected','months':bands},
      'matched_period':matched}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 history=json.loads(VINTAGE.read_text()) if VINTAGE.exists() else {'snapshots':[]};history['snapshots']=[x for x in history.get('snapshots',[]) if x.get('as_of')!=now.isoformat()];history['snapshots'].append({'as_of':now.isoformat(),'matched_period':matched,'current_month':bands[-1]});history['snapshots']=history['snapshots'][-400:];VINTAGE.write_text(json.dumps(history,ensure_ascii=False,indent=2))
 print(json.dumps({'collector':'MOLIT','months':len(months),'mode':out['refresh_meta']['mode'],'refreshed_months':sorted(refresh),'queried_pairs':len(pairs_to_fetch),'reused_watchlist_pairs':len(shared_cache),'workers':workers,'retried_pairs':len(fetch_meta['retried']),'cache_fallbacks':len(fetch_meta['fallbacks']),'latest_total':bands[-1]['total'],'matched':matched['changes']},ensure_ascii=False))
if __name__=='__main__':main()
