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
supported=int(watch_market.get('supported_target_rows') or 0)
if supported and len(wm_rows)<supported: errors.append('watchlist market representative coverage incomplete')
if supported>=10:
    traded=sum(1 for x in wm_rows if x.get('recent_trade_manwon') is not None)
    if traded/supported < .70: errors.append(f'watchlist recent-trade coverage too low: {traded}/{supported}')
if trade_detail and int(trade_detail.get('matched_count') or 0)<1: errors.append('watchlist recent trade source has no matches')
series=garak.get('series') or []
if len(series)<200: errors.append('Garak Geumho long history too short')
elif series[-1].get('ym'):
    age=ym_age(series[-1].get('ym'))
    if age is None or age>2: errors.append('Garak Geumho long history is stale')

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
 'forecast':'.github/workflows/forecast-regime.yml'
}
wf={k:(R/p).read_text(encoding='utf-8') for k,p in paths.items()}
for bad in ["'dist/market.html'","'dist/market.js'","'dist/index.html'"]:
    if bad in wf['parallel']: errors.append('parallel refresh still triggered by UI file '+bad)
if 'cancel-in-progress: false' not in wf['parallel']: errors.append('parallel refresh should preserve in-progress run')
if 'artifact_ready' not in wf['parallel'] or "needs.molit.outputs.artifact_ready == 'true'" not in wf['parallel']:
    errors.append('MOLIT degraded-mode artifact guard missing')
if wf['weekly'].count("'.github/workflows/weekly-refresh.yml'")!=1: errors.append('weekly workflow trigger duplicated')
if 'cancel-in-progress: false' not in wf['weekly']: errors.append('weekly checkpoint should preserve in-progress run')
if "'scripts/forecast_market_regime.py'" in wf['research']: errors.append('research workflow has unrelated forecast-script trigger')
if 'dist/regime_forecast.json' in wf['parallel']: errors.append('parallel workflow must not own regime_forecast output')
if 'dist/regime_forecast.json' in wf['research']: errors.append('research workflow must not own regime_forecast output')
if 'dist/regime_forecast.json' not in wf['forecast']: errors.append('forecast workflow does not own regime_forecast output')

payload={'status':'ok' if not errors else 'failed','latest_available':latest,'certified_through':cert,
         'research_month':trrows[-1].get('ym') if trrows else None,
         'forecast_research_month':fc.get('latest_research_month'),'warnings':warnings,'errors':errors}
print(json.dumps(payload,ensure_ascii=False))
if errors: sys.exit(1)
