#!/usr/bin/env python3
"""Validate market-feature guardrail for complex 3m direction.

The primary complex model is never overwritten. Market features are evaluated only
as a high-precision downside confirmation layer using vintage-safe rows from
dist/final_backtest.json.
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"dist/complex_direction_market_overlay_validation.json"

def main():
    data=json.loads(OUT.read_text())
    c=data["comparison"]
    g=data["guardrail_validation"]
    assert c["decision"]=="do_not_blend_into_primary_direction"
    assert g["confirmed_downside"]["negative_precision_pct"] >= 70
    assert g["market_only_downside"]["decision"]=="reject_as_standalone_warning"
    assert data["current"]["confirmed_downside_count"] == 0
    assert data["certification"]["certified"] is False
    print(json.dumps({"status":"ok","validated":"complex market guardrail","confirmed_downside_precision_pct":g["confirmed_downside"]["negative_precision_pct"]}))

if __name__=="__main__":
    main()
