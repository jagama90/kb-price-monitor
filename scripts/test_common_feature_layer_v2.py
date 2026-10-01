#!/usr/bin/env python3
import unittest
from research_common_feature_layer_v2 import auc,pearson,percentile,price_tier_feature,lead_lag_feature

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
 def test_pearson(self):
  self.assertAlmostEqual(pearson([1,2,3],[2,4,6]),1)

if __name__=='__main__':unittest.main(verbosity=2)
