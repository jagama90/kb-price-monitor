#!/usr/bin/env python3
import json,pathlib
from market_judgment_engine import build_judgment
R=pathlib.Path(__file__).resolve().parents[1]
OUT=R/'dist/market_judgment_candidate.json'
if __name__=='__main__':
    d=build_judgment(R)
    OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'as_of':d['as_of'],'snapshot':d['feature_layer']['snapshot_id'],'current':d['heads']['current_state'],'buy':d['heads']['buy_condition'],'forward':d['heads']['forward_scenario']['horizons']},ensure_ascii=False,indent=2))
