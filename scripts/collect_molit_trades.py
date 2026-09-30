#!/usr/bin/env python3
import os,json,datetime,urllib.parse,urllib.request,xml.etree.ElementTree as ET,pathlib,calendar,time,random
from concurrent.futures import ThreadPoolExecutor,as_completed
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data_sources/molit.json'; VINTAGE=ROOT/'data_sources/molit_daily_history.json'; SHARED=ROOT/'data_sources/.molit_watchlist_pair_cache.json'
SEOUL=['11110','11140','11170','11200','11215','11230','11260','11290','11305','11320','11350','11380','11410','11440','11470','11500','11530','11545','11560','11590','11620','11650','11680','11710','11740']
REPORTING_WINDOW_DAYS=30
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
 retry_timeout=max(fast_timeout,float(os.getenv('MOLIT_RETRY_TIMEOUT','12')))
 retry_workers=max(1,min(int(os.getenv('MOLIT_RETRY_WORKERS','6')),workers))
 pairs=sorted(set(pairs))
 started=time.monotonic()
 first,failed,durations=_run_pairs(pairs,key,workers,fast_timeout)
 retried=sorted(failed)
 recovered={};retry_failed={};retry_durations={}
 if retried:
  time.sleep(float(os.getenv('MOLIT_RETRY_DELAY','0.5')))
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
 keys={'<=9eok':sum(p<=90000 for p in prices),'9-15eok':sum(90000<p<=150000 for p in prices),'15-25eok':sum(150000<p<250000 for p in prices),'25eok+':sum(p>=250000 for p in prices)}
 buckets3={'<=15eok':sum(p<=150000 for p in prices),'15-25eok':sum(150000<p<250000 for p in prices),'25eok+':sum(p>=250000 for p in prices)}
 boundary={'13-15eok':sum(130000<p<=150000 for p in prices),'15-17eok':sum(150000<p<=170000 for p in prices),'23-25eok':sum(230000<p<=250000 for p in prices),'25-27eok':sum(250000<p<=270000 for p in prices)}
 return {'total':n,'counts':keys,'buckets3':buckets3,'boundary_counts':boundary,'under15_share':round(buckets3['<=15eok']*100/n,1) if n else None}
def shift_month(d,delta):
 y=d.year+(d.month-1+delta)//12;m=(d.month-1+delta)%12+1;return y,m

def period_end(period):
 y,m=(int(x) for x in str(period).split('-',1))
 return datetime.date(y,m,calendar.monthrange(y,m)[1])

def mature_trade_signal(bands,as_of,reporting_window_days=REPORTING_WINDOW_DAYS):
 """Return the latest full-month comparison whose statutory reporting window has elapsed.

 Raw current-month matched data stays available for diagnostics, but the engine
 signal never interprets not-yet-reportable contracts as missing demand.
 """
 mature=[]
 for row in bands or []:
  try:
   end=period_end(row.get('period'))
  except Exception:
   continue
  ready=end+datetime.timedelta(days=int(reporting_window_days))
  if ready<=as_of and row.get('total') is not None and row.get('under15_share') is not None:
   mature.append((end,row,ready))
 mature.sort(key=lambda x:x[0])
 meta={
  'level':'low',
  'provisional':True,
  'basis':'statutory_reporting_window',
  'reporting_window_days':int(reporting_window_days),
  'as_of':as_of.isoformat(),
 }
 if len(mature)<2:
  meta['reason']='fewer_than_two_mature_completed_months'
  return None,'unavailable_until_reporting_window_elapses',meta
 _,cur,cur_ready=mature[-1];_,prev,_=mature[-2]
 pct=lambda a,b:round((a/b-1)*100,1) if b else None
 signal={
  'as_of':as_of.isoformat(),
  'basis':'completed_month_after_statutory_reporting_window',
  'reporting_window_days':int(reporting_window_days),
  'current':{**cur,'range':'full month','reporting_window_elapsed_on':cur_ready.isoformat()},
  'previous':{**prev,'range':'full month'},
  'changes':{
   'trade_count_pct':pct(cur.get('total'),prev.get('total')),
   'under15_share_pp':round(float(cur['under15_share'])-float(prev['under15_share']),1),
  },
  'warning':'당월·직전월 조기신고는 진단용이며 엔진 거래 신호는 신고기한이 경과한 최근 완성 월을 사용',
 }
 meta.update({
  'level':'high',
  'provisional':False,
  'reason':'latest_full_month_reporting_window_elapsed',
  'signal_period':cur.get('period'),
  'previous_period':prev.get('period'),
  'reporting_window_elapsed_on':cur_ready.isoformat(),
 })
 return signal,'mature_completed_month',meta

def main():
 key=os.getenv('MOLIT_SERVICE_KEY')
 if not key:raise SystemExit('MOLIT_SERVICE_KEY secret is required')
 OUT.parent.mkdir(exist_ok=True);now=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date();months=[]
 try:
  previous=json.loads(OUT.read_text()) if OUT.exists() else {}
 except Exception: previous={}
 try:
  history=json.loads(VINTAGE.read_text()) if VINTAGE.exists() else {'snapshots':[]}
 except Exception: history={'snapshots':[]}
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

 # Equal-calendar-day comparison for the previous month is already stored in
 # the daily vintage history. Reuse it on normal weekdays instead of re-querying
 # all 25 districts. Friday correction sweep still refreshes the raw prior months.
 py,pm=shift_month(now,-1)
 cutoff=min(now.day,calendar.monthrange(py,pm)[1])
 prev_period=f'{py:04d}-{pm:02d}'
 cached_prev_match=None
 if months[1] not in refresh:
  mp=(previous.get('matched_period') or {})
  p=(mp.get('previous') or {})
  if mp.get('cutoff_day')==cutoff and p.get('period')==prev_period:
   cached_prev_match=p
  if cached_prev_match is None:
   for snap in reversed(history.get('snapshots') or []):
    smp=snap.get('matched_period') or {}; sp=smp.get('previous') or {}
    if smp.get('cutoff_day')==cutoff and sp.get('period')==prev_period:
     cached_prev_match=sp;break

 # Reuse district/month responses already downloaded by the watchlist collector
 # earlier in the same job. Persistent cache never suppresses a requested refresh,
 # but same-run shared cache does.
 pairs_to_fetch={(code,ym) for ym in refresh for code in SEOUL if (code,ym) not in shared_cache}
 # Only if no matched-period vintage exists do we need raw previous-month pairs.
 if cached_prev_match is None and months[1] not in refresh:
  for code in SEOUL:
   if (code,months[1]) not in pair_cache and (code,months[1]) not in shared_cache:
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
   sm={k:cached.get(k) for k in ('total','counts','buckets3','boundary_counts','under15_share')}
  else:
   rows=[]
   missing=[]
   for code in SEOUL:
    if (code,ym) in pair_rows:rows.extend(pair_rows[(code,ym)])
    else:missing.append(code)
   if missing:raise RuntimeError(f'MOLIT raw pair cache incomplete {ym}: {missing}')
   monthly[ym]=rows;sm=summarize(rows)
  series.append([ym[:4]+'-'+ym[4:],sm['total'],ym==months[0]]);bands.append({'period':ym[:4]+'-'+ym[4:],**sm})

 # Matched-period calculation needs fresh raw current-month rows. Previous-month
 # summary comes from vintage on weekdays, or fresh raw rows during Friday sweep.
 cur=months[0];prev=months[1];cy,cm=now.year,now.month
 if cur not in monthly:
  rows=[]
  for code in SEOUL:
   pair=(code,cur)
   if pair not in pair_rows:raise RuntimeError(f'MOLIT current-month cache missing {code} {cur}')
   rows.extend(pair_rows[pair])
  monthly[cur]=rows
 cs=summarize([r for r in monthly.get(cur,[]) if 1<=r[0]<=cutoff])
 if cached_prev_match is not None:
  ps={k:cached_prev_match.get(k) for k in ('total','counts','boundary_counts','under15_share')}
 else:
  if prev not in monthly:
   rows=[]
   for code in SEOUL:
    pair=(code,prev)
    if pair not in pair_rows:raise RuntimeError(f'MOLIT previous-month cache missing {code} {prev}')
    rows.extend(pair_rows[pair])
   monthly[prev]=rows
  ps=summarize([r for r in monthly.get(prev,[]) if 1<=r[0]<=cutoff])
 pct=lambda a,b:round((a/b-1)*100,1) if b else None
 matched={'as_of':now.isoformat(),'cutoff_day':cutoff,'basis':'contract_date_equal_calendar_days','current':{'period':f'{cy:04d}-{cm:02d}','range':f'1~{cutoff}일',**cs},'previous':{'period':f'{py:04d}-{pm:02d}','range':f'1~{cutoff}일',**ps},'changes':{'trade_count_pct':pct(cs['total'],ps['total']),'under15_share_pp':round(cs['under15_share']-ps['under15_share'],1) if cs['under15_share'] is not None and ps['under15_share'] is not None else None},'warning':'당월은 계약 후 신고가 추가될 수 있어 조기신호로 사용'}
 signal_matched,signal_status,trade_confidence=mature_trade_signal(bands,now)
 cache_months=months[:3]
 out={'source':'MOLIT apartment trade OpenAPI',
      'collected_at':datetime.datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
      'refresh_meta':{
       'mode':'weekly_correction_sweep' if weekly_sweep else 'daily_current_month_only',
       'queried_pairs':len(pairs_to_fetch),
       'reused_watchlist_pairs':len(shared_cache),
       'reused_previous_matched_vintage':cached_prev_match is not None,
       'retried_pairs':[cache_key(*x) for x in fetch_meta['retried']],
       'cache_fallback_pairs':[cache_key(*x) for x in fetch_meta['fallbacks']],
       'elapsed_sec':round(fetch_meta['elapsed_sec'],1)
      },
      'pair_cache':encode_cache(pair_cache,cache_months),
      'seoul_apt_trade_count':series,
      'price_bands':{'status':'partial_last_good' if fetch_meta['fallbacks'] else 'connected','months':bands},
      'matched_period':matched,
      'signal_matched_period':signal_matched,
      'signal_matched_period_status':signal_status,
      'trade_signal_confidence':trade_confidence,
      'scope':{'data_scope':'Seoul','market_scope':'city','region_code':'1100000000','district_codes':SEOUL}}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 history['snapshots']=[x for x in history.get('snapshots',[]) if x.get('as_of')!=now.isoformat()];history['snapshots'].append({'as_of':now.isoformat(),'matched_period':matched,'current_month':bands[-1]});history['snapshots']=history['snapshots'][-400:];VINTAGE.write_text(json.dumps(history,ensure_ascii=False,indent=2))
 print(json.dumps({'collector':'MOLIT','months':len(months),'mode':out['refresh_meta']['mode'],'refreshed_months':sorted(refresh),'queried_pairs':len(pairs_to_fetch),'reused_watchlist_pairs':len(shared_cache),'workers':workers,'retried_pairs':len(fetch_meta['retried']),'cache_fallbacks':len(fetch_meta['fallbacks']),'latest_total':bands[-1]['total'],'matched':matched['changes']},ensure_ascii=False))
if __name__=='__main__':main()
