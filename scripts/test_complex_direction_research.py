#!/usr/bin/env python3
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
a=json.loads((R/"dist/complex_direction_research.json").read_text())
v=json.loads((R/"dist/complex_direction_validation.json").read_text())
assert a["status"]=="research_only" and v["decision"]["certified"] is False
assert a["leakage_guard"]["no_future_target_rows"] is True
assert a["market_overlay"]["status"]=="context_only_not_blended"
assert v["decision"]["production_candidate_horizon"]=="3m"
assert v["decision"]["rejected_horizon"]=="12m"
assert len(a["items"])>=30
print("complex direction research contract: ok")
