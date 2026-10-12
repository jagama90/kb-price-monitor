#!/usr/bin/env python3
"""Contract and leakage tests for frozen prospective shadow evaluation."""
import copy
import json
import math

import evaluate_upside_prospective as shadow

protocol = shadow.load(shadow.PROTOCOL)
journal = shadow.load(shadow.JOURNAL)
raw = shadow.load(shadow.RAW)
prices = shadow.read_prices(raw)
rows = shadow.monthly_rows(prices)
assert shadow.validate_protocol(protocol, journal)
assert journal["snapshots"][0]["ym"] == "202608"
assert journal["snapshots"][0]["source_collected_at"]
assert journal["snapshots"][0]["training_observations"] >= 200
assert protocol["promotion_policy"].startswith("Never auto-promote")
assert shadow.make_report(protocol, journal, prices)["production_applied"] is False
assert shadow.make_report(protocol, journal, prices)["eligible_for_review"] is False or len(journal["outcomes"]) >= protocol["minimum_matured_months"]

# An as-yet-unknown target must not enter the month-t forecast or training.
start = protocol["start_ym"]
initial_prices = [p for p in prices if p["ym"] <= start]
start_rows = shadow.monthly_rows(initial_prices)
first = shadow.forecast(start_rows, start, protocol)
frozen = journal["snapshots"][0]
assert first["training_observations"] == frozen["training_observations"]
for key in protocol["models"]:
    for klass in shadow.CLASSES:
        assert math.isclose(first["models"][key][klass],
                            frozen["models"][key][klass], abs_tol=1e-9)

synthetic_next = {"ym": shadow.engine.shift_ym(start, 1),
                  "value": initial_prices[-1]["value"] * 1.004}
next_prices = initial_prices + [synthetic_next]
later_rows = shadow.monthly_rows(next_prices)
after_future_arrived = shadow.forecast(later_rows, start, protocol)
for key in protocol["models"]:
    for klass in shadow.CLASSES:
        assert math.isclose(first["models"][key][klass],
                            after_future_arrived["models"][key][klass], abs_tol=1e-12)

# Arrival of next month's official price labels the frozen prediction once.
synthetic_journal = {"protocol_version": 1, "start_ym": start,
                     "snapshots": [copy.deepcopy(frozen)], "outcomes": []}
updated = shadow.record_new_observations(protocol, synthetic_journal,
                                         next_prices, later_rows, "synthetic", "test")
assert len(updated["outcomes"]) == 1
assert updated["outcomes"][0]["forecast_ym"] == start
assert updated["outcomes"][0]["class"] == "up"
assert updated["snapshots"][0] == frozen
assert updated["snapshots"][-1]["ym"] == synthetic_next["ym"]
again = shadow.record_new_observations(protocol, updated, next_prices,
                                       later_rows, "newer source", "newer commit")
assert again == updated

# If historical source batches skip a prediction issue, never backfill that
# month after its outcome is already in the data.
synthetic_oct = {"ym": shadow.engine.shift_ym(start, 2),
                 "value": synthetic_next["value"] * 1.004}
missed_prices = next_prices + [synthetic_oct]
missed = shadow.record_new_observations(protocol, synthetic_journal,
                                        missed_prices, shadow.monthly_rows(missed_prices),
                                        "synthetic", "test")
assert [s["ym"] for s in missed["snapshots"]] == [start, synthetic_oct["ym"]]
assert synthetic_next["ym"] in shadow.make_report(protocol, missed, missed_prices)["missing_pre_outcome_snapshots"]
assert shadow.make_report(protocol, missed, missed_prices)["eligible_for_review"] is False

# The separate previously-unscored July->August extension is retrospective
# context and must not be counted as an independent prospective outcome.
assert all(x["forecast_ym"] >= start for x in journal.get("outcomes", []))
print("prospective upside shadow: lock, no-leakage, append-only, gap safety ok")
