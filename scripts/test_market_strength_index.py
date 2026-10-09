#!/usr/bin/env python3
import json, pathlib
R=pathlib.Path(__file__).resolve().parents[1]
d=json.loads((R/'dist/market_strength_index.json').read_text()); j=json.loads((R/'dist/market_judgment.json').read_text())
assert d['method']['hand_tuned_weights'] is False
ef=((j.get('feature_layer') or {}).get('engine_features') or {}).get('market_strength') or {}
overlay=(ef.get('forecast_overlay') or {})
assert d['production_formula_changed'] is bool(overlay.get('applied'))
assert d['snapshot_id']==j['feature_layer']['snapshot_id'] and d['validation']['monotonic'] is True and d['validation']['n']>=36
assert sum(1 for x in d['current']['components'].values() if x['used_in_index'])==6
print('market strength index contract: ok')
