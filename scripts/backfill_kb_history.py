#!/usr/bin/env python3
"""Historical KB backfill guard.
Current public collector exposes current KB general prices, not a documented historical-series endpoint.
This script deliberately refuses to synthesize 3 years of values. Add a verified KB historical source/export here when available.
"""
import pathlib,json
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=ROOT/'dist/kb_history_status.json'
p.write_text(json.dumps({'status':'blocked_source','requested_years':3,'reason':'No verified public KB historical price endpoint/source is configured; current DB begins 2026-09.'},ensure_ascii=False,indent=2))
print(p)
