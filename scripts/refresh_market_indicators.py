#!/usr/bin/env python3
"""Legacy entry point retained for compatibility.

The dashboard snapshot is now built exclusively from connected source adapters;
never overwrite it with hand-coded point-in-time values.
"""
import pathlib,runpy
ROOT=pathlib.Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'scripts/build_market_snapshot.py'),run_name='__main__')
