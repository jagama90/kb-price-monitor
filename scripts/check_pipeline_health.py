#!/usr/bin/env python3
"""Repository-level pipeline consistency checks. No network access required."""
from pathlib import Path
import json,sys,re

R=Path(__file__).resolve().parents[1]
errors=[]

def load(p):
    try:return json.loads((R/p).read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'{p}: {e}'); return {}

fb=load('dist/final_backtest.json')
tr=load('dist/turning_signal_research.json')
fc=load('dist/regime_forecast.json')
mi=load('dist/market_indicators.json')

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
         'forecast_research_month':fc.get('latest_research_month'),'errors':errors}
print(json.dumps(payload,ensure_ascii=False))
if errors: sys.exit(1)
