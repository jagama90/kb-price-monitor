#!/usr/bin/env python3
"""Fast render-safety checks for dashboard production artifacts."""
from __future__ import annotations
import json, math, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
errors=[]; warnings=[]

def load(path):
    try:return json.loads((ROOT/path).read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'{path}: {e}'); return {}

js=(ROOT/'dist/market.js').read_text(encoding='utf-8')
for token in ('const finiteNum=','safeDate=v=>','const refreshStamp=safeDate;',"headline:'데이터 확인 중'",'window.__currentCycleStage=null'):
    if token not in js: errors.append('render guard missing: '+token)

for token,reason in {
    'new Date(v||0)':'empty timestamp can become epoch/09:00',
    "kbUpdated=validDate(k.kb_collected_at)||new Date()":'missing KB timestamp can become current date',
    'Number(w?.downturn||0)':'missing forecast weight can become zero',
    'Number(m.exact_kb_rows||0)':'missing coverage can become 0/x',
    'Number(head.stage)||0':'missing regime stage can become downturn',
    'Number(s25.up_share_pct||0)':'missing breadth can become zero',
    'Number(t.songpa_vs_seoul_gap_pp)':'missing temperature gap can become zero',
    'Number(a.affordability_change_3m_pct)':'missing affordability change can become zero',
    'window.__currentCycleStage=0':'missing regime state can default to downturn',
    "d.updated_at||new Date()":'missing updated_at can become current date',
}.items():
    if token in js: errors.append(f'{reason}: {token}')

for pattern,reason in (
    (r'new Date\([^\n)]*\|\|0\)', 'empty timestamp can become epoch/09:00'),
    (r'updated_at\s*\|\|\s*new Date\(', 'missing updated_at can become current date'),
):
    if re.search(pattern, js): errors.append(reason+': '+pattern)

watch=load('dist/buy_watchlist_market.json')
numeric_keys={'sale_listing_count','sale_listing_week_delta','avg_ask_manwon','avg_ask_week_delta_manwon','recent_trade_manwon','kb_general_check_manwon'}
for i,row in enumerate(watch.get('items') or []):
    for key in numeric_keys:
        v=row.get(key)
        if v is None: continue
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)):
            errors.append(f'buy_watchlist_market items[{i}].{key}: expected finite number or null, got {v!r}')

judgment=load('dist/market_judgment.json')
components=(((judgment.get('heads') or {}).get('buy_condition') or {}).get('components') or {})
for key in ('finance','sentiment','demand','value','supply'):
    v=components.get(key)
    if v is None: warnings.append('buy condition component missing: '+key)
    elif isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(float(v)):
        errors.append(f'market_judgment component {key}: expected finite number or null, got {v!r}')

for path in ('dist/market_indicators.json','dist/market_judgment.json','dist/regime_forecast.json'):
    raw=(ROOT/path).read_text(encoding='utf-8')
    if '"NaN"' in raw or '"undefined"' in raw: errors.append(path+': literal NaN/undefined found')

print(json.dumps({'status':'ok' if not errors else 'error','errors':errors,'warnings':warnings},ensure_ascii=False))
raise SystemExit(1 if errors else 0)
