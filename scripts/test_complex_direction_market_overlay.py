#!/usr/bin/env python3
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
a=json.loads((R/"dist/complex_direction_research.json").read_text())
v=json.loads((R/"dist/complex_direction_market_overlay_validation.json").read_text())
assert a["market_overlay"]["primary_direction_unchanged"] is True
assert a["market_overlay"]["certification"]=="research_only"
assert v["comparison"]["decision"]=="do_not_blend_into_primary_direction"
assert v["guardrail_validation"]["confirmed_downside"]["negative_precision_pct"]==75.0
assert v["guardrail_validation"]["market_only_downside"]["decision"]=="reject_as_standalone_warning"
assert all(x["market_guardrail_3m"]["primary_direction_overridden"] is False for x in a["items"])
print("complex direction market overlay contract: ok")
