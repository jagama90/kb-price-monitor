#!/usr/bin/env python3
"""Regression guard for the historical-demand collector interface."""
import pathlib
import sys

R=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import collect_molit_trades as live

assert live.DISTRICT_CODES, 'market scope district codes are required'
assert isinstance(live.MARKET_SCOPE,dict) and live.MARKET_SCOPE.get('market_scope_id')
src=(R/'scripts/collect_historical_demand.py').read_text(encoding='utf-8')
assert 'SEOUL' not in src, 'historical demand must not depend on removed SEOUL constant'
assert 'DISTRICT_CODES' in src and 'MARKET_SCOPE' in src
assert 'pool.submit(fetch_all' in src, 'historical demand should parallelize live district fetches'
assert 'HISTORY_TIMEOUT' in src, 'historical demand must pass an explicit timeout'
assert 'fetch_all,code,ym,key,HISTORY_TIMEOUT' in src.replace(' ','').replace('\n',''), 'fetch_all interface changed without historical collector update'
compile(src,'collect_historical_demand.py','exec')
print({'status':'ok','districts':len(live.DISTRICT_CODES),'market_scope_id':live.MARKET_SCOPE.get('market_scope_id')})
