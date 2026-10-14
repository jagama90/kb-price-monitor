#!/usr/bin/env python3
"""Daily probability record invariants; no network or time-dependent writes."""
import datetime as dt
import unittest

import record_upside_probability_history as history

def engine(day,up):
    return {'version':'upside_probability_v1','scope':{'market_scope_id':'example_market'},
            'current':{'status':'ok','as_of':day,'source':'official weekly price index',
                       'probabilities':{'up':up,'flat':100-up-7.7,'down':7.7}},
            'generated_at':'2026-10-14T00:00:00+00:00'}

class TestDailyProbabilityHistory(unittest.TestCase):
    def setUp(self):
        self.base={'version':1,'scope':'example_market','events':[],'daily':[]}
        self.day=dt.datetime(2026,10,14,0,0,tzinfo=dt.timezone.utc)
    def test_live_and_unchanged(self):
        a=history.update(self.base,engine('20261005',61.5),self.day)
        self.assertEqual(len(a['events']),1)
        b=history.update(a,engine('20261005',61.5),self.day+dt.timedelta(days=1))
        self.assertEqual(len(b['events']),1)
        self.assertEqual(len(b['daily']),2)
        self.assertEqual(b['daily'][-1]['status'],'source_unchanged')
        self.assertEqual(b['events'][0],a['events'][0])
    def test_new_observation_and_same_day(self):
        a=history.update(self.base,engine('20260928',69.2),self.day)
        b=history.update(a,engine('20261005',61.5),self.day+dt.timedelta(minutes=5))
        self.assertEqual(len(b['events']),2)
        self.assertEqual(len(b['daily']),1)
        self.assertEqual(b['daily'][0]['probabilities']['up'],61.5)
        self.assertEqual(b['events'][0]['probabilities']['up'],69.2)
    def test_missing_never_zero(self):
        bad=engine('20261005',61.5)
        bad['current']['probabilities']=None
        b=history.update(self.base,bad,self.day)
        self.assertEqual(b['events'],[])
        self.assertIsNone(b['daily'][-1]['probabilities'])
        self.assertEqual(b['daily'][-1]['status'],'data_check')
    def test_reject_wrong_market_and_source_regress(self):
        a=history.update(self.base,engine('20261005',61.5),self.day)
        with self.assertRaises(ValueError):
            history.update(a,engine('20260928',69.2),self.day+dt.timedelta(days=1))
        different=engine('20261012',61.5)
        different['scope']['market_scope_id']='other_market'
        with self.assertRaises(ValueError):
            history.update(a,different,self.day+dt.timedelta(days=1))
    def test_bad_numbers_not_normalized(self):
        for x in [None,'',float('nan'),float('inf')]:
            bad=engine('20261005',61.5)
            bad['current']['probabilities']['up']=x
            b=history.update(self.base,bad,self.day)
            self.assertEqual(b['events'],[])

if __name__=='__main__':
    unittest.main()
