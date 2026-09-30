#!/usr/bin/env python3
"""Unit and integration invariants for the unified Seoul market judgment engine."""
import pathlib
import unittest

from market_judgment_engine import (
    build_judgment,
    buy_condition_head,
    current_state_head,
    forward_scenario_head,
    rolling_horizons,
    stable_risk_band,
)

R=pathlib.Path(__file__).resolve().parents[1]


def feature(m1=-1.0,m3=-2.0,bottom=False,momentum=False):
    return {
        'as_of':'2026-09-30',
        'components':{'finance':60.0,'sentiment':20.0,'demand':40.0,'value':30.0,'supply':50.0},
        'price_momentum':{'m1_pct':m1,'m3_pct':m3},
        'signals':{'breadth':40.0,'reaccel':30.0,'turn':35.0,'bottom_zone':bottom,'momentum_zone':momentum},
        'context':{'liquidity_support_0_100':60.0,'trade_pressure_0_100':30.0,'rate_pressure_0_100':35.0,'cooling_score_0_100':50.0},
    }


class UnifiedEngineTests(unittest.TestCase):
    def test_current_state_thresholds(self):
        weak_hist=[{'momentum_3m_pct':-1.0},{'momentum_3m_pct':-0.5},{'momentum_3m_pct':0.0}]
        self.assertEqual(current_state_head(feature(-1,-2),weak_hist)['stage'],0)
        self.assertEqual(current_state_head(feature(-1,-2,bottom=True),weak_hist)['stage'],1)
        self.assertEqual(current_state_head(feature(.2,-.2),weak_hist)['stage'],2)
        self.assertEqual(current_state_head(feature(.4,2.0),weak_hist)['stage'],3)
        self.assertEqual(current_state_head(feature(.4,2.0,momentum=True),weak_hist)['stage'],4)

    def test_buy_condition_weights_are_preserved(self):
        h=buy_condition_head(feature())
        self.assertAlmostEqual(h['score_0_100'],40.5,places=1)
        self.assertEqual(h['coverage_weight'],100)
        self.assertEqual(h['weights'],{'finance':25,'sentiment':20,'demand':20,'value':20,'supply':15})

    def test_forward_weights_sum_to_100(self):
        h=forward_scenario_head(feature())
        self.assertEqual([x['period'] for x in h['horizons']],['2026Q4','2027H1','2027H2'])
        for row in h['horizons']:
            self.assertAlmostEqual(sum(row['weights'].values()),100.0,places=6)

    def test_hysteresis_requires_two_points_to_ease(self):
        self.assertEqual(stable_risk_band(34.5,3),3)
        self.assertEqual(stable_risk_band(32.9,3),2)

    def test_production_build_uses_one_snapshot(self):
        j=build_judgment(R)
        f=j['feature_layer']
        c=j['heads']['current_state']
        b=j['heads']['buy_condition']
        q=j['heads']['forward_scenario']
        self.assertEqual(c['evidence']['m1_pct'],f['price_momentum']['m1_pct'])
        self.assertEqual(c['evidence']['m3_pct'],f['price_momentum']['m3_pct'])
        self.assertEqual(b['components'],f['components'])
        self.assertEqual(b['coverage_weight'],100)
        self.assertEqual(len(q['horizons']),3)
        self.assertTrue(f['snapshot_id'])
        if f['price_momentum']['overlay'].get('applied'):
            self.assertNotEqual(f['price_momentum']['m3_pct'],f['price_momentum']['overlay'].get('research_m3_pct'))


if __name__=='__main__':
    unittest.main(verbosity=2)
