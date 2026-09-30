#!/usr/bin/env python3
"""Regression tests for transaction-reporting maturity gates."""
import datetime
import unittest
from collect_molit_trades import mature_trade_signal

class MatureTradeSignalTests(unittest.TestCase):
    def test_month_rollover_uses_latest_reporting_mature_month(self):
        bands=[
            {'period':'2026-07','total':5993,'under15_share':79.4,'counts':{},'buckets3':{},'boundary_counts':{}},
            {'period':'2026-08','total':3546,'under15_share':79.6,'counts':{},'buckets3':{},'boundary_counts':{}},
            {'period':'2026-09','total':1873,'under15_share':82.5,'counts':{},'buckets3':{},'boundary_counts':{}},
            {'period':'2026-10','total':0,'under15_share':None,'counts':{},'buckets3':{},'boundary_counts':{}},
        ]
        signal,status,confidence=mature_trade_signal(bands,datetime.date(2026,10,1))
        self.assertEqual(status,'mature_completed_month')
        self.assertEqual(signal['current']['period'],'2026-08')
        self.assertEqual(signal['previous']['period'],'2026-07')
        self.assertAlmostEqual(signal['changes']['trade_count_pct'],-40.8,places=1)
        self.assertAlmostEqual(signal['changes']['under15_share_pp'],0.2,places=1)
        self.assertFalse(confidence['provisional'])

    def test_insufficient_mature_history_returns_unavailable(self):
        signal,status,confidence=mature_trade_signal(
            [{'period':'2026-09','total':10,'under15_share':80.0}],
            datetime.date(2026,10,1)
        )
        self.assertIsNone(signal)
        self.assertEqual(status,'unavailable_until_reporting_window_elapses')
        self.assertTrue(confidence['provisional'])

if __name__=='__main__':
    unittest.main(verbosity=2)
