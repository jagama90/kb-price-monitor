#!/usr/bin/env python3
import json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]
d=json.loads((R/'dist/upside_probability_engine.json').read_text(encoding='utf-8'))
m=json.loads((R/'dist/market_indicators.json').read_text(encoding='utf-8'))
assert d['status']=='validated_probability_engine'
assert d['no_future_leakage'] is True
assert d['model']['features']==['price_momentum_1m','price_momentum_3m']
assert d['model']['current_feature_mapping']['price_momentum_1m'].startswith('REB weekly')
for h,floor in ((1,.80),(3,.75),(6,.65)):
    v=d['validation'][str(h)]
    assert v['status']=='validated'
    assert v['selection']['multiclass_brier'] < v['selection']['base_brier']
    assert v['holdout']['multiclass_brier'] < v['holdout']['base_brier']
    assert v['holdout']['up_auc'] >= floor
assert d['validation']['12']['status']=='rejected'
assert d['forecast']['12']['status']=='not_validated'
for node in [d['current'],d['forecast']['3'],d['forecast']['6']]:
    p=node.get('probabilities')
    assert p and abs(sum(float(p[k]) for k in ('up','flat','down'))-100)<=.2
    assert all(0<=float(p[k])<=100 for k in ('up','flat','down'))
assert len(d['history'])==4 and d['history'][-1]['label']=='현재'
assert d['current']['as_of']==str((m.get('reb_weekly') or {}).get('latest',{}).get('date'))
assert {x['feature'] for x in d['rejected_inputs']}=={'trade','M2','market_strength'}
assert all(x['decision']=='rejected' for h in ('1','3','6') for k,x in d['candidate_screen'][h].items() if k!='price_momentum')
print('upside probability engine contract: ok')
