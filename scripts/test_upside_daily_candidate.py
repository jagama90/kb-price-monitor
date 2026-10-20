#!/usr/bin/env python3
"""Safety/retrospective gates for the daily finance-sentiment-trade shadow."""
import datetime as dt
import json
import math
import unittest
from pathlib import Path

import build_upside_daily_candidate as shadow
import record_upside_probability_history as record

class ShadowContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=shadow.read(shadow.OUT)
        cls.cert=shadow.read(shadow.CERTIFIED)
        cls.market=shadow.read(shadow.MARKET)
        cls.judgment=shadow.read(shadow.JUDGMENT)
    def test_candidate_is_explicitly_not_certified(self):
        d=self.data
        self.assertEqual(d['status'],'research_only_not_certified')
        self.assertIs(d['production_applied'],False)
        self.assertIs(d['certification']['eligible'],False)
        self.assertFalse(d['training']['historical_vintage_confirmed'])
        self.assertIn('independent prospective three-signal evaluation not yet certified',d['certification']['blocking_reasons'])
    def test_holdout_never_trains_parameters(self):
        d=self.data
        self.assertEqual(d['training']['selection_through'],'202412')
        self.assertEqual(d['training']['holdout_from'],'202501')
        self.assertLess(d['training']['selection_through'],d['training']['holdout_from'])
        self.assertGreaterEqual(d['training']['selection_n'],18)
        self.assertIsNotNone(d['metrics']['holdout']['baseline'])
        self.assertIsNotNone(d['metrics']['holdout']['candidate'])
    def test_daily_inputs_are_not_conflated_with_collection_clock(self):
        d=self.data;current=d['current']
        self.assertEqual(d['scope']['market_scope_id'],self.cert['scope']['market_scope_id'])
        if current['status']=='ok':
            self.assertEqual(set(current['components']),set(shadow.NAMES))
            self.assertNotEqual(current['vintages']['finance_mortgage_month'],self.judgment['as_of'])
            self.assertEqual(current['vintages']['trade_completed_month'],
                             self.market['signal_matched_period']['current']['period'])
            self.assertEqual(current['vintages']['trade_daily_as_of'],self.market['matched_period']['as_of'])
            self.assertEqual(current['vintages']['trade_daily_period'],self.market['matched_period']['current']['period'])
            self.assertEqual(current['source_status']['trade'],'connected')
            ch=self.market['matched_period']['changes']
            expected=max(0.0,min(100.0,50+float(ch['trade_count_pct'])*.35+float(ch['under15_share_pp'])*1.5))
            self.assertAlmostEqual(current['components']['demand'],expected,places=1)
            self.assertEqual(current['daily_signal']['status'],'provisional_reporting_window')
            self.assertTrue(current['daily_signal']['warning'])
            self.assertAlmostEqual(sum(current['probabilities'].values()),100,delta=.2)
            self.assertEqual(current['reference_probability_up_pct'],self.cert['current']['probabilities']['up'])
    def test_input_change_affects_candidate_but_not_certified(self):
        d=self.data
        if d['current']['status']!='ok':self.skipTest('daily input not available')
        co=d['coefficients'];means=d['selection_feature_means']
        self.assertTrue(any(abs(co[k])>0.0001 for k in shadow.NAMES))
        v=d['current']['components']
        basep={k:x/100 for k,x in self.cert['current']['probabilities'].items()}
        first=sum(co[k]*(v[k]-means[k])/20 for k in shadow.NAMES)
        name=next(k for k in shadow.NAMES if abs(co[k])>0.0001)
        second=first+co[name]*10/20
        a=shadow.adjust(basep,first)
        b=shadow.adjust(basep,second)
        self.assertNotEqual(a['up'],b['up'])
        self.assertAlmostEqual(sum(self.cert['current']['probabilities'].values()),100,delta=.2)
    def test_missing_and_invalid_source_never_zero(self):
        for val in (None,'',float('nan'),float('inf')):
            self.assertIsNone(shadow.vector({'finance':val,'sentiment':30,'demand':40}))
        market=json.loads(json.dumps(self.market))
        market['refresh_run']['sources']['molit']='unknown'
        result=shadow.live_inputs(market,self.judgment,self.cert)
        self.assertEqual(result['status'],'data_check')
        self.assertNotIn('probabilities',result)
        market=json.loads(json.dumps(self.market))
        market['matched_period']['changes']['trade_count_pct']=None
        result=shadow.live_inputs(market,self.judgment,self.cert)
        self.assertEqual(result['status'],'data_check')
    def test_daily_recording_is_append_only_and_does_not_modify_certified(self):
        h={'version':1,'scope':self.cert['scope']['market_scope_id'],'events':[],'daily':[]}
        now=dt.datetime(2026,10,16,3,tzinfo=dt.timezone.utc)
        current=record.update(h,self.cert,now,self.data)
        self.assertEqual(len(current['daily']),1)
        self.assertEqual(len(current.get('research_daily',[])),1)
        self.assertEqual(current['daily'][0]['probabilities']['up'],self.cert['current']['probabilities']['up'])
        again=record.update(current,self.cert,now+dt.timedelta(days=1),self.data)
        self.assertEqual(len(again['events']),len(current['events']))
        self.assertEqual(len(again['research_daily']),2)
        self.assertIn('daily_signal',again['research_daily'][-1])
        self.assertIn('changes_vs_previous',again['research_daily'][-1])
        bad=json.loads(json.dumps(self.data));bad['production_applied']=True
        with self.assertRaises(ValueError):record.update(h,self.cert,now,bad)

if __name__=='__main__':
    unittest.main()
