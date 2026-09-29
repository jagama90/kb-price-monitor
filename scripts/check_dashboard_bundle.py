#!/usr/bin/env python3
"""Fail-fast contract checks for the static dashboard bundle."""
from pathlib import Path
import re,sys,json

R=Path(__file__).resolve().parents[1]
html=(R/'dist/market.html').read_text(encoding='utf-8')
js=(R/'dist/market.js').read_text(encoding='utf-8')
errors=[]

ids=re.findall(r'\bid="([^"]+)"',html)
dups=sorted({x for x in ids if ids.count(x)>1})
if dups: errors.append('duplicate ids: '+', '.join(dups))

required=['conditionScore','scoreFinance','scoreSentiment','scoreDemand','scoreValue','scoreSupply',
          'scoreExplanation','scoreExplainTitle','scoreExplainWeight','scoreExplainBody',
          'regimeForecast','forecastGrid','forecastMeta','mobileCards','body',
          'driverLive',
          'backtestScope','backtestCertified','backtestCorr',
          'sourceMolitStatus','sourceKbStatus','sourceEcosStatus','sourceWatchStatus',
          'conditionTier','confidenceScore','validationUnsold','validationUnsoldPeriod',
          'b15all','b15to25','b25p']
for x in required:
    if ids.count(x)!=1: errors.append(f'required id {x}: expected 1, got {ids.count(x)}')

for k in ['finance','sentiment','demand','value','supply']:
    n=len(re.findall(rf'<article[^>]+class="[^"]*score-component[^"]*"[^>]+data-score-key="{k}"',html))
    if n!=1: errors.append(f'score card {k}: expected 1 clickable card, got {n}')
if '점수 근거 보기' in html: errors.append('legacy score detail label still visible')
if 'score-detail-close' not in html: errors.append('score detail close control missing')

if js.count('window.showScoreDetail=function')!=1: errors.append('showScoreDetail must be defined exactly once')
if js.count('window.hideScoreDetail=function')!=1: errors.append('hideScoreDetail must be defined exactly once')
if "card.dataset.scoreKey" not in js: errors.append('delegated score card handler missing')
if ".score-detail-btn" in js: errors.append('legacy score detail button handler remains')

a=js.find('function setupScoreDetails')
b=js.find('\nfunction setupSnapshotEvidence',a)
block=js[a:b] if a>=0 and b>a else ''
for forbidden in ['.onclick=','.onkeydown=','.after(panel)','appendChild(panel)']:
    if forbidden in block: errors.append('legacy score handler still present: '+forbidden)

if not (R/'dist/regime_forecast.json').exists(): errors.append('regime_forecast.json missing')
# The former standalone Garak long-term chart was intentionally removed; the
# watchlist-wide KB history remains the canonical history source.
if '가락금호 24A · KB 장기 추이' in html:
    errors.append('retired standalone Garak long-term chart returned')
if "const kbKey=x=>" not in js: errors.append('exact complex+area KB key missing')
if "kb.get(Number(x.complex_id))" in js: errors.append('legacy complex-only KB price lookup remains')

# visual remodel contract
for rid in ('forecastHeadline','forecastTrend','storyHeadline','storySummary','nextSignals','hubDriversMeta','hubValidationMeta','hubWatchMeta','hubBacktestMeta'):
    if ids.count(rid)!=1: errors.append(f'visual remodel id {rid}: expected 1, got {ids.count(rid)}')
if html.count('class="card score-component"')!=5: errors.append('condition dashboard must contain five compact score tiles')
if 'class="forecast-flow"' not in html: errors.append('forward-regime infographic flow missing')
if 'forecast-risk-track-v153' not in js or 'forecast-risk-sub-v153' not in js: errors.append('simplified forecast risk renderer missing')
if '<summary><span><small>2 · 왜 움직이고 있나' in html: errors.append('legacy text-heavy analysis menu returned')
if '점수 근거 보기' in html: errors.append('legacy score CTA returned')

# isolated mobile v4 contract: legacy layout selectors must not be used by live markup.
if html.count('class="weekly-flow-v4"')!=1: errors.append('weekly v4 flow missing or duplicated')
if html.count('class="flow-step-v4')!=4: errors.append('weekly v4 flow must contain exactly four steps')
if 'class="signal-rail"' in html or 'decision-path-mini' in html: errors.append('legacy weekly flow markup returned')
if html.count('class="deep-row-v4"')!=4: errors.append('deep dive must contain exactly four isolated rows')
if html.count('class="deep-summary-v4"')!=4: errors.append('deep dive summaries missing')
if 'class="analysis-hub"' in html or 'class="hub-summary"' in html or 'class="compact-section"' in html:
    errors.append('legacy deep-dive wrapper classes returned')
if html.count('class="driver-change-list-v143"')!=1: errors.append('change-first driver list missing')
if 'class="transmission compact"' in html: errors.append('legacy boxed driver infographic returned')
if html.count('class="audit-source-grid-v140"')!=1: errors.append('combined validation/data source grid missing')
if len(re.findall(r'class="[^"]*\baudit-panel-v140\b[^"]*"',html))!=1: errors.append('combined validation/data panel missing')
if 'class="card method-v4"' in html: errors.append('retired standalone data-validation panel returned')
if 'methodology-v3' in html or 'methodology-v2' in html: errors.append('legacy methodology markup returned')
if "flow-step-v4 '+state[1]" not in js: errors.append('live signal updater does not preserve v4 flow classes')



# refresh calendar / semantic change-history contract
for rid in ('refreshCalendar','refreshCalendarTitle','refreshSummaryStatus','refreshSummaryMeta','refreshLegend','refreshChangedCount','refreshUnchangedCount','refreshWarningCount',
            'refreshDaily','refreshWeekly','refreshMonthly','refreshDailyLast','refreshDailyNext','refreshWeeklyLast','refreshWeeklyNext','refreshMonthlyLast','refreshMonthlyNext',
            'refreshHealthSummary'):
    if ids.count(rid)!=1: errors.append(f'refresh calendar id {rid}: expected 1, got {ids.count(rid)}')
if not re.search(r'<details[^>]+id="refreshCalendar"[^>]*>',html):
    errors.append('refresh calendar must default to collapsed details')
if '<summary class="refresh-calendar-summary">' not in html:
    errors.append('refresh calendar compact summary missing')
if 'refreshSummaryStatus' not in js or 'refreshSummaryMeta' not in js:
    errors.append('refresh calendar compact live status wiring missing')
if "const REFRESH_SNAPSHOT_KEY='kbpm.refresh.snapshot.v3'" not in js:
    errors.append('semantic refresh snapshot storage contract missing')
if 'REFRESH_CHANGE_TTL=24*60*60*1000' not in js:
    errors.append('24h recent-change visibility contract missing')
if 'initRefreshCalendar()' not in js or 'decorateRefreshPanel' not in js or 'decorateFactorRefresh' not in js:
    errors.append('semantic refresh renderer missing')
if js.count("decorateRefreshPanel({key:")<6:
    errors.append('six core dashboard panels must expose refresh timestamps')
if "dot.className='panel-refresh-dot'" in js:
    errors.append('legacy unread red-dot creator returned')
if '실제 변경' not in js or '변경 없음' not in js:
    errors.append('refresh summary must distinguish real changes from checks with no value change')
if 'factor-change-v135' not in js:
    errors.append('factor before-to-after change display missing')


# watchlist simplified source-state contract
if ids.count('watchSourceNotice')!=1:
    errors.append('watchlist source notice missing')
if '실거래 미확인' not in js:
    errors.append('unverified trade must use neutral 실거래 미확인 label')
watch_render_start=js.find("document.querySelector('#summary').textContent=market.length+'개 단지'")
watch_render_end=js.find("}load().catch",watch_render_start)
watch_render=js[watch_render_start:watch_render_end] if watch_render_start>=0 and watch_render_end>watch_render_start else ''
for noisy in ("원천 검증",):
    if noisy in watch_render:
        errors.append('watchlist row-level noisy source label returned: '+noisy)
for legacy_label in ('FORWARD REGIME · 전망엔진','THIS WEEK · 이번 주 핵심','MARKET CONTEXT · 검증된 보조신호','DEEP DIVE','DATA QUALITY','월간 갱신','>LIVE<'):
    if legacy_label in html:
        errors.append('redundant dashboard label returned: '+legacy_label)
if '가격·Value' in js or 'Breadth 백테스트' in js:
    errors.append('internal English metric label returned to user-facing dashboard')


# mobile density v132 contract
if 'score-dashboard-inline' not in html:
    errors.append('compact five-score inline gauge strip missing')
if 'forecast-compact-mobile' not in html:
    errors.append('compact mobile forecast marker missing')
if ids.count('watchInsights')!=1:
    errors.append('watchlist supporting analyses drawer missing')
watch_pos=html.find('<details class="deep-row-v4" id="watchlist"')
watch_primary=html.find('<section class="card watch">',watch_pos)
watch_insights=html.find('id="watchInsights"',watch_pos)
if watch_pos<0 or watch_primary<0 or watch_insights<0 or not (watch_pos < watch_primary < watch_insights):
    errors.append('watchlist detail must appear before supporting analyses')
watch_insight_tag=re.search(r'<details[^>]+id="watchInsights"[^>]*>',html)
if not watch_insight_tag or re.search(r'\sopen(?:\s|>)',watch_insight_tag.group(0)):
    errors.append('watchlist supporting analyses must default closed')

jsv=re.search(r'market\.js\?v=([^"]+)',html)
cssv=re.search(r'market\.css\?v=([^"]+)',html)
if not jsv or not cssv: errors.append('asset cache versions missing')

# market context extension contract
for rid in ('marketContext','contextBreadthBadge','breadthHeadline','breadthFill','breadthGangnam','breadthNonGangnam','breadthSongpa',
            'temperatureHeadline','tempSeoul','tempSongpa','tempGap','affordHeadline','affordRate','affordPayment','affordChange',
            'affordBenchmark','contextValidation'):
    if ids.count(rid)!=1: errors.append(f'market context id {rid}: expected 1, got {ids.count(rid)}')
if 'market_extensions.json' not in js or 'loadMarketExtensions()' not in js:
    errors.append('market extension loader missing')
if html.count('class="card market-context-v1"')!=1:
    errors.append('market context panel missing or duplicated')

# live-data anti-hardcode contract
if 'const KB_HISTORY=' in js:
    errors.append('hard-coded KB history returned')
if 'const BASE_RATES=[' in js:
    errors.append('hard-coded base-rate history returned')
if '2026.08.27' in js or "['3.00%'" in js:
    errors.append('hard-coded current base-rate snapshot returned')
if 'kb_watchlist_history.json' not in js:
    errors.append('watchlist KB history is not loaded from live JSON')
if 'base_rate_official' not in js:
    errors.append('official base-rate snapshot is not wired to dashboard')
if 'm.listing_collected_at||m.collected_at' not in js:
    errors.append('listing freshness is not tied to the listing-source timestamp')
if 'rowListingFresh=x=>' not in js or 'listing_refresh_status' not in js:
    errors.append('listing freshness must be evaluated per row and source status')
if 'rowTradeFresh=x=>' not in js or 'trade_refresh_status' not in js:
    errors.append('recent-trade identity/freshness must be evaluated per row')
if "sourceRefreshNote=delayed.length?' · 일부 지연':' · 정상'" not in js or 'refresh_run?.sources' not in js:
    errors.append('dashboard must surface current per-run source refresh status')
if "rowListingFresh(x)&&rowTradeFresh(x)?signal(x)" not in js:
    errors.append('directional listing signal must require both fresh listing and verified trade')
if "hasAsk=x.avg_ask_manwon!=null" not in js or "hasTrade=x.recent_trade_manwon!=null" not in js:
    errors.append('directional listing signal must fail closed when ask/trade data is missing')

payload={'status':'ok' if not errors else 'failed','checks':'all-dashboard-contracts','errors':errors}
print(json.dumps(payload,ensure_ascii=False))
if errors: sys.exit(1)

# change-first v140 contracts
if 'buckets3' not in js: errors.append('three-band transaction distribution not wired')
if 'kb_watchlist_weekly_change.json' not in js: errors.append('15eok boundary must use Friday KB comparison')
if 'scoreBand=' not in js: errors.append('score categories missing')
if 'coverage-badge-v140' not in html: errors.append('separate data coverage badge missing')
if '원천 미연결' in html and '미분양' in html: errors.append('unsold housing must not be shown as disconnected')

# Current-regime regression guard: cycleStageBadge was intentionally removed.
if "badge.textContent=label" in js or "badge.textContent='데이터 확인 중'" in js:
    errors.append('cycle renderer still depends on removed cycleStageBadge')
if "renderRegimeReference(window.__currentCycleStage" in js:
    errors.append('historical regime reference must remain hidden until user taps a phase')
if "window.__currentCycleStage=stage" not in js:
    errors.append('current regime stage is not persisted for UI highlighting')

# v151 historical/current regime comparison contract
for _id in ('regimeCompareToggle','regimeMetricM1','regimeMetricM3','regimeMetricBreadth','regimeMetricReaccel'):
    if f'id="{_id}"' not in html: errors.append(f'regime compare element missing: {_id}')
if 'window.__currentRegimeMetrics=' not in js: errors.append('current regime metrics are not persisted for historical comparison')
if 'window.__regimeCompare=' not in js: errors.append('historical/current comparison state missing')
if "s===window.__currentCycleStage" not in js: errors.append('current phase must auto-open comparison mode')

# v153 forecast-language contract
if 'forecast-rules-v153' not in html: errors.append('forecast expression rules missing')
if "하락 가능성" not in js: errors.append('forecast must foreground downturn risk')
if "시나리오 가중치 · 확률 예측 아님" not in js: errors.append('forecast probability disclaimer missing')
