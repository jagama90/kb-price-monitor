#!/usr/bin/env python3
import unittest
from research_common_feature_layer_v2 import auc,pearson,percentile,price_tier_feature

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
 def test_pearson(self):
  self.assertAlmostEqual(pearson([1,2,3],[2,4,6]),1)

if __name__=='__main__':unittest.main(verbosity=2)
