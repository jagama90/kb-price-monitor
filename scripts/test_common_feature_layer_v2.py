#!/usr/bin/env python3
import unittest
from research_common_feature_layer_v2 import auc,pearson,percentile,price_tier_feature,lead_lag_feature,selling_pressure_feature,policy_feature,rental_supply_feature

class CommonFeatureLayerV2Tests(unittest.TestCase):
 def test_percentile_is_rank_based(self):
  self.assertEqual(percentile([1,2,3],2),50)
 def test_auc(self):
  self.assertEqual(auc([0,0,1,1],[0,1,2,3]),1)
 def test_price_tier_uses_configured_scope_not_formula_names(self):
  m={'scope':{'data_scope':'TestMarket'},'signal_matched_period':{
    'current':{'period':'2026-08','total':80,'counts':{'<=9eok':30,'9-15eok':20,'15-25eok':20,'25eok+':10}},
    'previous':{'period':'2026-07','total':100,'counts':{'<=9eok':40,'9-15eok':30,'15-25eok':20,'25eok+':10}},
    'changes':{'trade_count_pct':-20}},
    'price_bands':{'months':[1,2,3]}}
  x=price_tier_feature(m)
  self.assertEqual(x['scope']['data_scope'],'TestMarket')
  self.assertEqual(x['signal_period'],'2026-08')
  self.assertEqual(len(x['bands']),4)
 def test_lead_lag_uses_configured_region(self):
  dates=['202501','202502','202503','202504']
  raw={'targets':{
   'leading50':{'payload':{'dataBody':{'data':{'날짜리스트':dates,'전월대비증감률리스트':[1,2,3,4]}}}},
   'median':{'payload':{'dataBody':{'data':{'날짜리스트':dates,'데이터리스트':[{'지역코드':'ZZ','지역명':'Test','dataList':[100,101,103,106]}]}}}}
  }}
  x=lead_lag_feature(raw,{'region':{'code':'ZZ','label':'Test'}})
  self.assertNotEqual(x['status'],'not_connected')
  self.assertEqual(x['market_region_code'],'ZZ')
  self.assertIn('Test',x['market_definition'])
 def test_price_tier_history_excludes_immature_rows(self):
  cfg={'analysis':[{'id':'low'},{'id':'mid'},{'id':'high'}],'absolute':[{'id':'low'},{'id':'mid'},{'id':'high'}]}
  hist={'price_tier_config':cfg,'months':[
   {'period':'2026-01','total':100,'counts':{'low':50,'mid':30,'high':20},'buckets3':{'low':50,'mid':30,'high':20},'mature':True},
   {'period':'2026-02','total':100,'counts':{'low':45,'mid':30,'high':25},'buckets3':{'low':45,'mid':30,'high':25},'mature':False}
  ]}
  m={'scope':{'data_scope':'Test'},'price_tier_config':cfg,'signal_matched_period':{
    'current':{'period':'2026-01','total':100,'counts':{'low':50,'mid':30,'high':20}},
    'previous':{'period':'2025-12','total':100,'counts':{'low':55,'mid':30,'high':15}},
    'changes':{'trade_count_pct':0}}}
  x=price_tier_feature(m,hist,{'sample':[]})
  self.assertEqual(x['validation']['available_band_months'],1)
 def test_selling_pressure_never_infers_forced_sale(self):
  w={'items':[{'sale_listing_count':10,'sale_listing_week_delta':2,'avg_ask_manwon':110,'recent_trade_manwon':100,'avg_ask_week_delta_manwon':-1}]}
  x=selling_pressure_feature(w,{'snapshots':[{'as_of':'2026-09-01'}]})
  self.assertFalse(x['representative_market_sample'])
  self.assertEqual(x['forced_selling']['status'],'not_observable')
 def test_policy_context_applies_scope_tags_without_score(self):
  raw={'status':'connected_current_context','as_of':'2026-10-01','historical_backtest_ready':False,'events':[{'id':'x','effective_date':'2026-07-01','end_date':'2026-12-31','scope_match_any':['capital_region'],'terms':{'stress':3.0},'source':'official'}]}
  x=policy_feature(raw,{'credit_policy_scope_tags':['capital_region']})
  self.assertEqual(x['active_rule_count'],1)
  self.assertFalse(x['production_applied'])
  self.assertFalse(x['historical_backtest_ready'])
 def test_structural_supply_does_not_replace_legacy_supply_score(self):
  m={'kb_sentiment':{'jeonse_score_0_100':55},'unsold_inventory':{'region_units':100,'period':'202601','region_code':'X'}}
  x=rental_supply_feature(m,{'status':'source_unreachable_from_actions','series':{}})
  self.assertEqual(x['rental_market_balance']['score_0_100'],55)
  self.assertFalse(x['production_applied'])
  self.assertEqual(x['structural_supply']['unsold_inventory']['units'],100)
 def test_pearson(self):
  self.assertAlmostEqual(pearson([1,2,3],[2,4,6]),1)

if __name__=='__main__':unittest.main(verbosity=2)
