#!/usr/bin/env python3
"""Regression guard for the historical-demand collector interface."""
import ast
import pathlib
import sys

R=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import collect_molit_trades as live

assert live.DISTRICT_CODES, 'market scope district codes are required'
assert isinstance(live.MARKET_SCOPE,dict) and live.MARKET_SCOPE.get('market_scope_id')
tree=ast.parse((R/'scripts/collect_historical_demand.py').read_text(encoding='utf-8'))
src=ast.unparse(tree)
assert 'SEOUL' not in src, 'historical demand must not depend on removed SEOUL constant'
assert 'DISTRICT_CODES' in src and 'MARKET_SCOPE' in src
calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='fetch_all']
assert calls and all(len(n.args)>=4 for n in calls), 'fetch_all must receive explicit timeout'
print({'status':'ok','districts':len(live.DISTRICT_CODES),'market_scope_id':live.MARKET_SCOPE.get('market_scope_id')})
