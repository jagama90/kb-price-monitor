#!/usr/bin/env python3
"""Repository-level pipeline consistency checks. No network access required."""
from pathlib import Path
import json,sys,re,datetime

R=Path(__file__).resolve().parents[1]
errors=[]
warnings=[]

def load(p):
    try:return json.loads((R/p).read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'{p}: {e}'); return {}

fb=load('dist/final_backtest.json')
tr=load('dist/turning_signal_research.json')
fc=load('dist/regime_forecast.json')
mi=load('dist/market_indicators.json')
master=load('data/buy_watchlist_master.json')
targets=load('data/buy_watchlist_targets.json')
details=load('data/buy_watchlist_listings.json')
watch_market=load('data/buy_watchlist_market.json')
watch_market_dist=load('dist/buy_watchlist_market.json')
watch_hist=load('dist/kb_watchlist_history.json')
trade_detail=load('data_sources/watchlist_recent_trades.json')
garak=load('dist/garak_geumho_24a_history.json')
market_ext=load('dist/market_extensions.json')

if fb and not fb.get('certified_final'): errors.append('final_backtest is not certified')
fbrows=fb.get('rows') or []
trrows=tr.get('rows') or []
latest=fb.get('latest_available_month')
cert=fb.get('certified_through')
if fbrows and latest and fbrows[-1].get('ym')!=latest: errors.append('final_backtest latest_available_month != last row')
if fbrows and cert and latest and latest>cert and not fbrows[-1].get('provisional'): errors.append('latest backtest row should be provisional')
if trrows and latest and trrows[-1].get('ym')!=latest: errors.append('turning research is not aligned to latest backtest month')
if trrows and tr.get('latest_source_provisional') is not None:
    if bool(trrows[-1].get('source_provisional')) != bool(tr.get('latest_source_provisional')):
        errors.append('turning research provisional flag mismatch')
if fc and trrows:
    if fc.get('latest_research_month')!=trrows[-1].get('ym'): errors.append('forecast latest_research_month is stale')
    if bool(fc.get('latest_research_provisional'))!=bool(trrows[-1].get('source_provisional')): errors.append('forecast provisional flag mismatch')
if fc and cert and fc.get('latest_certified_backtest_month')!=cert: errors.append('forecast certified month mismatch')
for h in fc.get('horizons') or []:
    w=h.get('weights') or {}
    if set(w)!={'consolidation','reacceleration','downturn'}: errors.append(f"{h.get('period')}: scenario keys invalid")
    total=sum(float(v) for v in w.values()) if w else 0
    if abs(total-100)>0.11: errors.append(f"{h.get('period')}: weights sum {total}, expected 100")
if not mi.get('updated_at'): errors.append('market_indicators.updated_at missing')
for key in ('kb_weekly_sale_index','kb_weekly_rent_index'):
    src=mi.get(key) or {}
    if src.get('status')!='connected' or not (src.get('latest') or {}).get('value'):
        errors.append(key+' missing or disconnected')
# Fail if last-good inputs silently become stale while the bundle keeps rebuilding.
today=datetime.datetime.now(datetime.timezone.utc).date()
def ymd(v):
    z=re.sub(r'[^0-9]','',str(v or ''))
    if len(z)>=8:
        try:return datetime.date(int(z[:4]),int(z[4:6]),int(z[6:8]))
        except:return None
    return None
def ym_age(v):
    z=re.sub(r'[^0-9]','',str(v or ''))
    if len(z)<6:return None
    try:return (today.year-int(z[:4]))*12 + today.month-int(z[4:6])
    except:return None
def iso_day(v):
    try:return datetime.datetime.fromisoformat(str(v).replace('Z','+00:00')).date()
    except:return None

mi_day=ymd(mi.get('updated_at'))
if not mi_day or (today-mi_day).days>2: errors.append('market_indicators bundle is stale')
refresh_run=mi.get('refresh_run') or {}
refresh_day=iso_day(refresh_run.get('attempted_at'))
if not refresh_run:
    errors.append('market_indicators refresh_run metadata missing')
elif not refresh_day or (today-refresh_day).days>2:
    errors.append('market_indicators source refresh attempt is stale')
else:
    src_states=refresh_run.get('sources') or {}
    for src in ('molit','ecos','kb_sentiment','watchlist_detail'):
        if src not in src_states: errors.append(f'market_indicators refresh status missing: {src}')
        elif src_states.get(src)!='connected':
            warnings.append({'source_refresh_fallback':src,'status':src_states.get(src),'attempted_at':refresh_run.get('attempted_at')})
fb_age=ym_age(latest)
if fb_age is None or fb_age>2: errors.append('final_backtest latest_available_month is stale')

for key in ('kb_weekly_sale_index','kb_weekly_rent_index'):
    src=mi.get(key) or {}
    if src.get('status')=='connected' and (src.get('latest') or {}).get('value'):
        kday=ymd((src.get('latest') or {}).get('date'))
        if not kday or (today-kday).days>14: errors.append(key+' is stale')
# Validated market extension freshness and integrity.
if market_ext:
    cur=market_ext.get('current') or {}
    br=cur.get('breadth') or {}; s25=br.get('seoul_25') or {}
    if int(s25.get('count') or 0)!=25: errors.append('market extension breadth must cover 25 Seoul districts')
    bday=ymd(str(br.get('date') or ''))
    if not bday or (today-bday).days>14: errors.append('market extension district breadth is stale')
    aff=cur.get('affordability') or {}; age=ym_age(aff.get('ym'))
    if age is None or age>3: errors.append('market extension affordability input is stale')
    temp=cur.get('temperature') or {}; tage=ym_age(temp.get('ym'))
    if tage is None or tage>2: errors.append('market extension local temperature is stale')
    val=market_ext.get('validation') or {}
    if val.get('production_price_turn_formula_changed') is not False: errors.append('market extension unexpectedly changed production price-turn formula')
    if val.get('breadth_role')!='confidence_context': warnings.append({'market_extension_breadth_role':val.get('breadth_role')})
else:
    errors.append('market_extensions.json missing')
if fc and fc.get('as_of')!=mi.get('updated_at'): errors.append('forecast as_of does not match market snapshot')
base=mi.get('base_rate_official') or {}
base_day=ymd(base.get('latest_observation_date') or (base.get('latest') or {}).get('date'))
if not base_day or (today-base_day).days>10: errors.append('official base-rate observation is stale')
mort=mi.get('mortgage_rate_official') or {}
mort_item=str(mort.get('item') or '')
if mort_item!='주택담보대출': errors.append('mortgage_rate_official must use aggregate 주택담보대출 rate')
if market_ext:
    aff=((market_ext.get('current') or {}).get('affordability') or {})
    if aff.get('ym')==mort.get('period') and aff.get('mortgage_rate_pct') is not None and mort.get('rate_pct') is not None:
        if abs(float(aff['mortgage_rate_pct'])-float(mort['rate_pct']))>.001:
            errors.append('affordability mortgage rate differs from market snapshot')
trade_day=ymd((mi.get('matched_period') or {}).get('as_of'))
if not trade_day or (today-trade_day).days>3: errors.append('MOLIT matched-period snapshot is stale')
sent_dates=[ymd(x.get('date')) for x in ((mi.get('kb_sentiment') or {}).get('latest') or {}).values() if isinstance(x,dict)]
sent_dates=[x for x in sent_dates if x]
if not sent_dates or (today-max(sent_dates)).days>14: errors.append('KB sentiment snapshot is stale')
for key,src,max_lag in [('M2',mi.get('m2_official') or mi.get('m2') or {},3),('mortgage',mi.get('mortgage_rate_official') or {},3),('KB value',mi.get('kb_value') or {},2)]:
    age=ym_age(src.get('period'))
    if age is None or age>max_lag: errors.append(f'{key} input is stale')

# Watchlist target coverage: never silently omit a named complex or requested area.
def norm_name(x):
    return re.sub(r'[^0-9A-Za-z가-힣]','',str(x or '')).replace('아파트','').lower()
masters=master.get('items') or []
by_name={norm_name(x.get('user_name')):x for x in masters}
by_kb={norm_name(x.get('kb_name')):x for x in masters if x.get('kb_name')}
unresolved=[]
for t in targets.get('items') or []:
    c=by_name.get(norm_name(t.get('name'))) or by_kb.get(norm_name(t.get('name')))
    if not c:
        unresolved.append({'name':t.get('name'),'reason':'complex_not_resolved'}); continue
    if not c.get('complex_id') and c.get('status') in ('confirmed_preoccupancy','preoccupancy'):
        continue
    aids=t.get('area_ids') or []
    if not aids:
        lo,hi=t.get('min_pyeong'),t.get('max_pyeong')
        for typ in c.get('types') or []:
            m=re.search(r'\d+(?:\.\d+)?',str(typ.get('type_label') or ''))
            if m and (lo is None or float(m.group())>=float(lo)) and (hi is None or float(m.group())<=float(hi)):
                aids.append(typ.get('area_id'))
    if not aids: unresolved.append({'name':t.get('name'),'reason':'target_area_not_resolved','selection':t.get('selection')})
if unresolved: warnings.append({'watchlist_unresolved_targets':unresolved})

# Representative interest-complex rows and recent-trade coverage.
wm_rows=watch_market.get('items') or []
dist_wm_rows=watch_market_dist.get('items') or []
for stamp in ('listing_collected_at','listing_refresh_attempted_at','listing_refresh_status','kb_detail_collected_at','molit_trade_collected_at'):
    if watch_market.get(stamp)!=watch_market_dist.get(stamp): errors.append('watchlist data/dist '+stamp+' mismatch')
if len(wm_rows)!=len(dist_wm_rows): errors.append('watchlist data/dist row count mismatch')
mt_day=iso_day(watch_market.get('molit_trade_collected_at'))
if not mt_day or (today-mt_day).days>3: errors.append('watchlist MOLIT trade refresh is stale')
kb_master_day=iso_day(master.get('kb_collected_at'))
if not kb_master_day or (today-kb_master_day).days>10: errors.append('watchlist KB price master is stale')
listing_day=iso_day(watch_market.get('listing_collected_at') or watch_market.get('collected_at'))
if any(x.get('sale_listing_count') is not None for x in wm_rows) and (not listing_day or (today-listing_day).days>10):
    warnings.append({'watchlist_listing_source_stale_days':None if not listing_day else (today-listing_day).days})
listing_status=watch_market.get('listing_refresh_status')
if listing_status in ('fallback_last_good','partial_last_good'):
    warnings.append({'watchlist_listing_refresh_status':listing_status,'last_good':watch_market.get('listing_collected_at'),'attempted_at':watch_market.get('listing_refresh_attempted_at')})
supported=int(watch_market.get('supported_target_rows') or 0)
if supported and len(wm_rows)<supported: errors.append('watchlist market representative coverage incomplete')
if supported>=10:
    traded=sum(1 for x in wm_rows if x.get('recent_trade_manwon') is not None)
    if traded/supported < .70: errors.append(f'watchlist recent-trade coverage too low: {traded}/{supported}')
if trade_detail and int(trade_detail.get('matched_count') or 0)<1: errors.append('watchlist recent trade source has no matches')
series=garak.get('series') or []
hist_rows=watch_hist.get('items') or []
hist_by_cid={int(x.get('complex_id')):x for x in hist_rows if x.get('complex_id')}
for row in wm_rows:
    cid=int(row.get('complex_id') or 0)
    h=hist_by_cid.get(cid)
    if not h:
        errors.append(f'KB watchlist history missing complex {cid} {row.get("name")}')
        continue
    if int(h.get('area_id') or 0)!=int(row.get('area_id') or 0):
        errors.append(f'KB watchlist history area mismatch {cid}: history={h.get("area_id")} market={row.get("area_id")}')
    months=[ymd(str(x.get('ym') or '')+'01') for x in (h.get('series') or []) if x.get('ym')]
    months=[x for x in months if x]
    if h.get('refresh_status')=='unavailable':
        if row.get('kb_general_check_manwon') is not None:
            errors.append(f'KB watchlist history unavailable despite current KB price for {cid} {row.get("name")}')
        else:
            warnings.append({'kb_watchlist_history_unavailable':{'complex_id':cid,'name':row.get('name'),'area_id':row.get('area_id')}})
    elif not months or (today-max(months)).days>75:
        errors.append(f'KB watchlist history stale for {cid} {row.get("name")}')
if watch_hist.get('refresh_status') in ('partial_last_good','partial'):
    warnings.append({'kb_watchlist_history_refresh_status':watch_hist.get('refresh_status'),
                     'fallback_rows':watch_hist.get('fallback_rows'),'errors':watch_hist.get('errors')})
if len(series)<200: errors.append('Garak Geumho long history too short')
elif series[-1].get('ym'):
    age=ym_age(series[-1].get('ym'))
    if age is None or age>2: errors.append('Garak Geumho long history is stale')
if garak.get('refresh_status')=='fallback_last_good':
    warnings.append({'garak_history_refresh_status':'fallback_last_good','attempted_at':garak.get('refresh_attempted_at')})

# Exact-area trade identity must never cross-map sibling complexes.
def ident_tokens(v):
    s=str(v or '')
    return ({x for x in re.findall(r'(\d+)\s*단지',s)},{x for x in re.findall(r'(\d+)\s*차',s)})
def ident_conflict(a,b):
    aa,ab=ident_tokens(a);ba,bb=ident_tokens(b)
    return bool((aa and ba and aa!=ba) or (ab and bb and ab!=bb))
observed={}
for x in trade_detail.get('items') or []:
    if x.get('match_method')=='unique_dong_exact_area':
        errors.append(f"unsafe area-only MOLIT match remains: {x.get('name')} -> {x.get('molit_apt_name')}")
    if ident_conflict(x.get('name'),x.get('molit_apt_name')) and ident_conflict(x.get('kb_name'),x.get('molit_apt_name')):
        errors.append(f"numbered-complex MOLIT mismatch: {x.get('name')} -> {x.get('molit_apt_name')}")
    k=(x.get('molit_apt_name'),x.get('recent_trade_date'),x.get('recent_trade_manwon'),x.get('matched_exclusive_m2'))
    if all(v is not None for v in k):
        observed.setdefault(k,set()).add(int(x.get('complex_id') or 0))
for k,cids in observed.items():
    if len(cids)>1: errors.append(f'MOLIT trade assigned to multiple complexes {sorted(cids)}: {k}')
if trade_detail.get('status')=='partial':
    warnings.append({'watchlist_trade_source_status':'partial','fetch_errors':trade_detail.get('fetch_errors')})

# Detail snapshots must never claim false zero/price values after a degraded collection.
for x in details.get('items') or []:
    if x.get('data_quality')=='sanitized_pending_exact_area_refresh': continue
    if x.get('listing_count')==0 and x.get('avg_ask_manwon') is None:
        warnings.append({'detail_suspicious_zero_listing':{'complex_id':x.get('complex_id'),'area_id':x.get('area_id')}})
        break


paths={
 'parallel':'.github/workflows/parallel-market-refresh.yml',
 'weekly':'.github/workflows/weekly-refresh.yml',
 'research':'.github/workflows/research-turning-signal.yml',
 'forecast':'.github/workflows/forecast-regime.yml',
 'final':'.github/workflows/final-backtest.yml',
 'extensions':'.github/workflows/market-extensions.yml',
 'pages':'.github/workflows/pages.yml',
 'repair':'.github/workflows/repair-dashboard-data.yml'
}
wf={k:(R/p).read_text(encoding='utf-8') for k,p in paths.items()}
for bad in ["'dist/market.html'","'dist/market.js'","'dist/index.html'"]:
    if bad in wf['parallel']: errors.append('parallel refresh still triggered by UI file '+bad)
if 'cancel-in-progress: true' not in wf['parallel']: errors.append('parallel refresh should cancel superseded runs')
if 'artifact_ready' not in wf['parallel'] or "needs.molit.outputs.artifact_ready == 'true'" not in wf['parallel']:
    errors.append('MOLIT degraded-mode artifact guard missing')
if 'refresh_run_status.json' not in wf['parallel']: errors.append('parallel workflow does not persist per-run source refresh outcomes')
if wf['weekly'].count("'.github/workflows/weekly-refresh.yml'")!=1: errors.append('weekly workflow trigger duplicated')
if 'cancel-in-progress: false' not in wf['weekly']: errors.append('weekly checkpoint should preserve in-progress run')
if 'merge_weekly_listing_snapshot.py' not in wf['weekly']: errors.append('weekly listing merge guard missing')
if wf['weekly'].count('scripts/collect_kb_watchlist_history.py')<2: errors.append('weekly workflow does not trigger when KB watchlist history collector changes')
if wf['weekly'].count('scripts/collect_garak_geumho_24a.py')<2: errors.append('weekly workflow does not trigger when Garak history collector changes')
if 'merge_parallel_market_snapshot.py' not in wf['parallel']: errors.append('parallel watchlist merge guard missing')
if 'merge_parallel_market_snapshot.py' not in wf['repair']: errors.append('repair workflow can roll back newer listing data')
if 'check_pipeline_health.py' not in wf['pages']: errors.append('Pages deploy is not gated by pipeline health')
if 'buy_watchlist_market.prev.json' in wf['weekly'] or 'restoring last-good market snapshot' in wf['weekly']:
    errors.append('weekly workflow can roll back newer watchlist market data')
if "'scripts/forecast_market_regime.py'" in wf['research']: errors.append('research workflow has unrelated forecast-script trigger')
if 'dist/regime_forecast.json' in wf['parallel']: errors.append('parallel workflow must not own regime_forecast output')
if 'dist/regime_forecast.json' in wf['research']: errors.append('research workflow must not own regime_forecast output')
if 'dist/regime_forecast.json' not in wf['forecast']: errors.append('forecast workflow does not own regime_forecast output')

# Dashboard live-data lineage: every fetched asset must have a repository producer/owner
# and Pages must publish dist changes. This is deliberately explicit so a new fetch
# cannot silently bypass refresh/freshness review.
market_js=(R/'dist/market.js').read_text(encoding='utf-8')
fetch_assets={x.split('?')[0] for x in re.findall(r"fetch\(['\"]([^'\"]+)",market_js)}
expected_fetch_assets={
    'kb_watchlist_history.json','buy_watchlist_market.json','buy_watchlist_master.json',
    'buy_watchlist_targets.json','market_indicators.json','final_backtest.json',
    'turning_signal_research.json','regime_forecast.json','garak_geumho_24a_history.json',
    'market_extensions.json'
}
if fetch_assets!=expected_fetch_assets:
    errors.append('dashboard fetch asset set changed without lineage review: '+str(sorted(fetch_assets^expected_fetch_assets)))
for asset in expected_fetch_assets:
    if not (R/'dist'/asset).exists(): errors.append('dashboard fetch asset missing from dist: '+asset)
lineage=[
    ('kb_watchlist_history.json','weekly','scripts/collect_kb_watchlist_history.py'),
    ('buy_watchlist_market.json','parallel','dist/buy_watchlist_market.json'),
    ('buy_watchlist_market.json','weekly','dist/buy_watchlist_market.json'),
    ('buy_watchlist_master.json','weekly','dist/buy_watchlist_master.json'),
    ('buy_watchlist_targets.json','pages','cp data/buy_watchlist_targets.json dist/buy_watchlist_targets.json'),
    ('market_indicators.json','parallel','dist/market_indicators.json'),
    ('final_backtest.json','final','dist/final_backtest.json'),
    ('turning_signal_research.json','research','dist/turning_signal_research.json'),
    ('regime_forecast.json','forecast','dist/regime_forecast.json'),
    ('garak_geumho_24a_history.json','parallel','dist/garak_geumho_24a_history.json'),
    ('garak_geumho_24a_history.json','weekly','dist/garak_geumho_24a_history.json'),
    ('market_extensions.json','extensions','dist/market_extensions.json'),
]
for asset,owner,needle in lineage:
    if needle not in wf[owner]: errors.append(f'{asset}: {owner} workflow ownership missing')
if "paths: ['dist/**'" not in wf['pages']: errors.append('Pages push trigger does not cover all dist assets')

payload={'status':'ok' if not errors else 'failed','latest_available':latest,'certified_through':cert,
         'research_month':trrows[-1].get('ym') if trrows else None,
         'forecast_research_month':fc.get('latest_research_month'),'warnings':warnings,'errors':errors}
print(json.dumps(payload,ensure_ascii=False))
if errors: sys.exit(1)
