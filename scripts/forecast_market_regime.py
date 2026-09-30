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

WEIGHTS={'finance':25,'sentiment':20,'demand':20,'value':20,'supply':15}

def buy_fingerprint(buy):
    c=buy.get('components') or {}
    return (round(float(buy.get('score_0_100') or 0),3),tuple(round(float(c.get(k) or 0),3) for k in WEIGHTS))

def attach_buy_comparison(judgment,previous_judgment):
    buy=(judgment.get('heads') or {}).get('buy_condition') or {}
    old=((previous_judgment.get('heads') or {}).get('buy_condition') or {}) if previous_judgment else {}
    if not old or old.get('score_0_100') is None or buy.get('score_0_100') is None:
        return
    # Preserve the last meaningful comparison across no-change rebuilds.
    if buy_fingerprint(buy)==buy_fingerprint(old) and old.get('comparison'):
        buy['comparison']=old['comparison']
        return
    current=float(buy['score_0_100']);previous=float(old['score_0_100'])
    ctx=judgment.get('feature_layer',{}).get('context') or {}
    oldctx=previous_judgment.get('feature_layer',{}).get('context') or {}
    rollover_correction=bool(
        ctx.get('trade_signal_status')=='carried_forward_last_usable' and
        ctx.get('trade_signal_as_of')!=ctx.get('raw_matched_as_of') and
        float(oldctx.get('trade_count_pct') or 0)<=-99
    )
    if rollover_correction:
        buy['comparison']={
            'previous_score_0_100':round(current,1),
            'current_score_0_100':round(current,1),
            'score_change':0.0,
            'previous_as_of':previous_judgment.get('as_of'),
            'current_as_of':judgment.get('as_of'),
            'component_changes':{},
            'dominant_reasons':[],
            'trade_signal_status':ctx.get('trade_signal_status'),
            'trade_signal_as_of':ctx.get('trade_signal_as_of'),
            'correction_note':'month_rollover_reporting_gap_excluded',
            'superseded_display_score':round(previous,1),
        }
        return
    oldc=old.get('components') or {};newc=buy.get('components') or {}
    changes={}
    for k,w in WEIGHTS.items():
        if oldc.get(k) is None or newc.get(k) is None:
            continue
        delta=round(float(newc[k])-float(oldc[k]),1)
        changes[k]={
            'previous':round(float(oldc[k]),1),
            'current':round(float(newc[k]),1),
            'component_delta':delta,
            'weighted_score_delta':round(delta*w/100,1),
        }
    reasons=sorted(
        [{'factor':k,**v} for k,v in changes.items()],
        key=lambda x:abs(x['weighted_score_delta']),
        reverse=True
    )
    buy['comparison']={
        'previous_score_0_100':round(previous,1),
        'current_score_0_100':round(current,1),
        'score_change':round(current-previous,1),
        'previous_as_of':previous_judgment.get('as_of'),
        'current_as_of':judgment.get('as_of'),
        'component_changes':changes,
        'dominant_reasons':reasons[:3],
        'trade_signal_status':ctx.get('trade_signal_status'),
        'trade_signal_as_of':ctx.get('trade_signal_as_of'),
    }

def main():
    if not VALIDATION.exists():
        raise SystemExit('market_judgment_validation.json missing; refusing unvalidated unified engine')
    v=json.loads(VALIDATION.read_text())
    if not v.get('apply_recommended'):
        raise SystemExit('unified market judgment validation gate failed; keep last-good production outputs')
    previous_forecast={}
    if OUT.exists():
        try:previous_forecast=json.loads(OUT.read_text())
        except:previous_forecast={}
    previous_judgment={}
    if JUDGMENT.exists():
        try:previous_judgment=json.loads(JUDGMENT.read_text())
        except:previous_judgment={}
    judgment=build_judgment(R,previous_forecast)
    attach_buy_comparison(judgment,previous_judgment)
    forecast=legacy_forecast_payload(judgment,R)
    JUDGMENT.write_text(json.dumps(judgment,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    OUT.write_text(json.dumps(forecast,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({
      'status':'ok','as_of':judgment.get('as_of'),'snapshot_id':judgment['feature_layer']['snapshot_id'],
      'current_state':judgment['heads']['current_state']['label'],
      'buy_score':judgment['heads']['buy_condition']['score_0_100'],
      'buy_change':judgment['heads']['buy_condition'].get('comparison',{}).get('score_change'),
      'forward':[(x['label'],x['display']['headline'],x['display']['downturn_weight']) for x in judgment['heads']['forward_scenario']['horizons']]
    },ensure_ascii=False))

if __name__=='__main__':main()
