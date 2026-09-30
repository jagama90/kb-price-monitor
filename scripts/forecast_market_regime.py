#!/usr/bin/env python3
"""Production wrapper for the unified market judgment engine.

The common feature snapshot is built once and feeds Current State, Buy
Condition, and Forward Scenario. A legacy-compatible regime_forecast.json is
still emitted for downstream consumers during migration.
"""
import json,pathlib
from market_judgment_engine import build_judgment, legacy_forecast_payload
R=pathlib.Path(__file__).resolve().parents[1]
OUT=R/'dist/regime_forecast.json'
JUDGMENT=R/'dist/market_judgment.json'
VALIDATION=R/'dist/market_judgment_validation.json'

def main():
    if not VALIDATION.exists():
        raise SystemExit('market_judgment_validation.json missing; refusing unvalidated unified engine')
    v=json.loads(VALIDATION.read_text())
    if not v.get('apply_recommended'):
        raise SystemExit('unified market judgment validation gate failed; keep last-good production outputs')
    previous={}
    if OUT.exists():
        try:previous=json.loads(OUT.read_text())
        except:previous={}
    judgment=build_judgment(R,previous)
    forecast=legacy_forecast_payload(judgment,R)
    JUDGMENT.write_text(json.dumps(judgment,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    OUT.write_text(json.dumps(forecast,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({
      'status':'ok','as_of':judgment.get('as_of'),'snapshot_id':judgment['feature_layer']['snapshot_id'],
      'current_state':judgment['heads']['current_state']['label'],
      'buy_score':judgment['heads']['buy_condition']['score_0_100'],
      'forward':[(x['label'],x['display']['headline'],x['display']['downturn_weight']) for x in judgment['heads']['forward_scenario']['horizons']]
    },ensure_ascii=False))

if __name__=='__main__':main()
