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
          'regimeForecast','forecastGrid','forecastMeta','garakHistoryLatest','garakHistoryChart','mobileCards','body']
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
hist=R/'dist/garak_geumho_24a_history.json'
if not hist.exists(): errors.append('garak_geumho_24a_history.json missing')
else:
    try:
        hd=json.loads(hist.read_text(encoding='utf-8')); series=hd.get('series') or []
        if len(series)<200: errors.append(f'garak history too short: {len(series)}')
    except Exception as e: errors.append('garak history invalid: '+str(e))
if 'garak_geumho_24a_history.json' not in js or 'loadGarakHistory()' not in js: errors.append('Garak history loader missing from market.js')
if "const kbKey=x=>" not in js: errors.append('exact complex+area KB key missing')
if "kb.get(Number(x.complex_id))" in js: errors.append('legacy complex-only KB price lookup remains')

# visual remodel contract
for rid in ('forecastHeadline','forecastTrend','storyHeadline','storySummary','nextSignals','hubDriversMeta','hubValidationMeta','hubWatchMeta','hubBacktestMeta'):
    if ids.count(rid)!=1: errors.append(f'visual remodel id {rid}: expected 1, got {ids.count(rid)}')
if html.count('class="hub-summary"')!=4: errors.append('analysis hub must contain exactly four visual summaries')
if html.count('class="card score-component"')!=5: errors.append('condition dashboard must contain five compact score tiles')
if 'class="analysis-hub"' not in html: errors.append('analysis hub wrapper missing')
if 'class="forecast-flow"' not in html: errors.append('forward-regime infographic flow missing')
if 'forecast-mini-values' not in js or 'scenario-rail' not in js: errors.append('forecast infographic renderer missing')
if '<summary><span><small>2 · 왜 움직이고 있나' in html: errors.append('legacy text-heavy analysis menu returned')
if '점수 근거 보기' in html: errors.append('legacy score CTA returned')

# mobile flow repair contract
if html.count('class="signal-rail"')!=1: errors.append('weekly signal rail missing or duplicated')
if 'decision-path-mini' in html: errors.append('legacy boxed weekly path returned')
if html.count('class="driver-rail"')!=1: errors.append('deep-dive driver rail missing')
if 'class="transmission compact"' in html: errors.append('legacy boxed driver infographic returned')
if html.count('methodology-v3')!=1: errors.append('methodology v3 status-first layout missing')
if 'methodology-v2' in html: errors.append('legacy methodology v2 returned')
if html.count('class="method-health"')!=1: errors.append('methodology health summary missing')


jsv=re.search(r'market\.js\?v=([^"]+)',html)
cssv=re.search(r'market\.css\?v=([^"]+)',html)
if not jsv or not cssv: errors.append('asset cache versions missing')

payload={'status':'ok' if not errors else 'failed','checks':len(required)+9,'errors':errors}
print(json.dumps(payload,ensure_ascii=False))
if errors: sys.exit(1)
