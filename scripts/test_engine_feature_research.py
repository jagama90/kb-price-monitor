#!/usr/bin/env python3
import json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]
d=json.loads((R/'dist/engine_feature_research.json').read_text())
assert d['no_future_leakage'] is True
assert d['market_strength']['hand_tuned_weights'] is False
assert d['decisions']['market_strength']['decision']=='selected_production_support'
assert d['decisions']['improving_breadth_3m']['decision']=='rejected'
assert set(d['rejected_features'])=={'improving_breadth_3m','strength_delta_1m','strength_delta_3m','price_strength_gap','deteriorating_breadth_3m','change_balance_3m'}
o=d['forecast_overlay'];assert o['apply_recommended'] is True and abs(float(o['selected_weight'])-.25)<1e-9
b=o['baseline'];s=next(x for x in o['candidates'] if abs(float(x['weight'])-.25)<1e-6)
assert s['passed'] is True
assert s['metrics']['down_auc']>b['down_auc'] and s['metrics']['reaccel_auc_positive']>b['reaccel_auc_positive']
assert s['metrics']['down_corr_negative_fwd3']>=b['down_corr_negative_fwd3']-.05
assert s['metrics']['reaccel_corr_fwd3']>=b['reaccel_corr_fwd3']-.02
print('engine feature research contract: ok')
