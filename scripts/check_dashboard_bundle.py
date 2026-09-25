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
          'regimeForecast','forecastGrid','forecastMeta']
for x in required:
    if ids.count(x)!=1: errors.append(f'required id {x}: expected 1, got {ids.count(x)}')

for k in ['finance','sentiment','demand','value','supply']:
    n=len(re.findall(rf'data-score-key="{k}"',html))
    if n!=1: errors.append(f'score detail button {k}: expected 1, got {n}')
if 'score-detail-close' not in html: errors.append('score detail close control missing')

if js.count('window.showScoreDetail=function')!=1: errors.append('showScoreDetail must be defined exactly once')
if js.count('window.hideScoreDetail=function')!=1: errors.append('hideScoreDetail must be defined exactly once')
if "btn.dataset.scoreKey" not in js: errors.append('delegated score button handler missing')

a=js.find('function setupScoreDetails')
b=js.find('\nfunction setupSnapshotEvidence',a)
block=js[a:b] if a>=0 and b>a else ''
for forbidden in ['.onclick=','.onkeydown=','.after(panel)','appendChild(panel)']:
    if forbidden in block: errors.append('legacy score handler still present: '+forbidden)

if not (R/'dist/regime_forecast.json').exists(): errors.append('regime_forecast.json missing')

jsv=re.search(r'market\.js\?v=([^"]+)',html)
cssv=re.search(r'market\.css\?v=([^"]+)',html)
if not jsv or not cssv: errors.append('asset cache versions missing')

payload={'status':'ok' if not errors else 'failed','checks':len(required)+9,'errors':errors}
print(json.dumps(payload,ensure_ascii=False))
if errors: sys.exit(1)
