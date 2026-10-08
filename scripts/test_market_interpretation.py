#!/usr/bin/env python3
import json, pathlib
R=pathlib.Path(__file__).resolve().parents[1]
d=json.loads((R/'dist/market_interpretation.json').read_text(encoding='utf-8'))
assert d['production_formula_changed'] is False
assert d['new_score_created'] is False
assert d['current']['flow']
assert d['current']['strength'] in {'강함','보통','약함','확인 중'}
assert d['current']['turn_sign']
assert d['current']['data_voice']
v=d['validation']
assert v['status'] in {'historically_supported','insufficient'}
if v['status']=='historically_supported':
    assert v['strong_uptrend']['fwd_3m']['mean_pct'] > v['weak_uptrend']['fwd_3m']['mean_pct']
print('plain market interpretation contract: ok')
