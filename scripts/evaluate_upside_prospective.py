#!/usr/bin/env python3
"""Prospective, append-only shadow evaluation for monthly upside probabilities.

The protocol was frozen before a 2026-09 monthly price observation existed
in the trusted source. Never convert historical/revised observations into
prospective forecasts, never update previously frozen probabilities, and
never promote a production model from this script.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
from pathlib import Path

import audit_upside_probability_stability as audit
import build_upside_probability_engine as engine

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data_sources/reb_long_cycle.json"
PROTOCOL = ROOT / "research/upside_prospective_protocol.json"
JOURNAL = ROOT / "research/upside_prospective_journal.json"
REPORT = ROOT / "research/upside_prospective_report.json"
CLASSES = ("up", "flat", "down")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_prices(raw):
    if raw.get("status") != "full":
        raise ValueError("R-ONE raw long-cycle source is not full")
    raw_prices = (raw.get("series") or {}).get("price") or []
    prices = []
    for row in raw_prices:
        ym = str(row.get("ym") or "")
        val = engine.finite(row.get("value"))
        if len(ym) != 6 or val is None or val <= 0:
            raise ValueError("invalid or missing R-ONE price point")
        if prices and engine.ym_ord(ym) != engine.ym_ord(prices[-1]["ym"]) + 1:
            raise ValueError("monthly R-ONE price points must be strictly consecutive")
        prices.append({"ym": ym, "value": val})
    if len(prices) < 100:
        raise ValueError("insufficient monthly price history")
    return prices


def monthly_rows(prices):
    return engine.monthly_rows({"rows": [
        {"ym": p["ym"], "price": {"value": p["value"]}}
        for p in prices
    ]})


def forecast(rows, ym, protocol):
    idx = next((i for i, r in enumerate(rows) if r["ym"] == ym), None)
    if idx is None:
        raise ValueError("forecast month is absent")
    ctx = audit.features_at_time(rows, idx, protocol["frozen_flat_band_pct"])
    if ctx is None:
        raise ValueError("insufficient point-in-time price momentum or training rows")
    near = audit.neighbors(ctx, rows[idx]["m1"], rows[idx]["m3"])
    models = {}
    for key, spec in protocol["models"].items():
        result = audit.calculate(near, spec["k"], spec["weight"])
        models[key] = result["probabilities"]
        assert abs(sum(models[key].values()) - 1) < 1e-10
    return {"ym": ym, "inputs": {
        "price_momentum_1m_pct": rows[idx]["m1"],
        "price_momentum_3m_pct": rows[idx]["m3"],
    }, "training_observations": len(ctx["train"]), "models": models}


def new_snapshot(rows, prices, ym, protocol, source_collected_at, source_commit):
    item = forecast(rows, ym, protocol)
    price = next(p["value"] for p in prices if p["ym"] == ym)
    return {**item, "reference_price_index": price,
            "source_collected_at": source_collected_at,
            "source_commit": source_commit}


def validate_protocol(protocol, journal):
    assert protocol["status"] == "frozen_prospective_protocol"
    assert protocol["production_applied"] is False
    assert protocol["start_ym"] == "202608"
    assert protocol["baseline"] == "uniform_10"
    assert set(protocol["models"]) == {"uniform_10", "inverse_10", "inverse_15"}
    assert protocol["models"]["uniform_10"] == {"k": 10, "weight": "uniform"}
    assert protocol["models"]["inverse_10"] == {"k": 10, "weight": "inverse"}
    assert protocol["models"]["inverse_15"] == {"k": 15, "weight": "inverse"}
    assert journal["start_ym"] == protocol["start_ym"]
    assert journal["protocol_version"] == protocol["version"]
    snaps = journal.get("snapshots") or []
    assert snaps and snaps[0]["ym"] == protocol["start_ym"]
    assert len({s["ym"] for s in snaps}) == len(snaps)
    assert [s["ym"] for s in snaps] == sorted(s["ym"] for s in snaps)
    for snap in snaps:
        assert snap["ym"] >= protocol["start_ym"]
        assert engine.finite(snap.get("reference_price_index")) is not None
        assert engine.finite(snap.get("inputs", {}).get("price_momentum_1m_pct")) is not None
        assert engine.finite(snap.get("inputs", {}).get("price_momentum_3m_pct")) is not None
        for key in protocol["models"]:
            probs = snap["models"][key]
            assert all(0 <= probs[c] <= 1 for c in CLASSES)
            assert math.isclose(sum(probs.values()), 1, abs_tol=1e-9)
    observed = journal.get("outcomes") or []
    assert len({o["forecast_ym"] for o in observed}) == len(observed)
    assert all(o["forecast_ym"] in {s["ym"] for s in snaps} for o in observed)
    return True


def record_new_observations(protocol, journal, prices, rows, source_collected_at, source_commit):
    """Append only. Existing predictions AND first-published outcomes stay frozen."""
    result = copy.deepcopy(journal)
    snapshots = result["snapshots"]
    outcomes = result.setdefault("outcomes", [])
    by_ym = {p["ym"]: p for p in prices}
    outcome_months = {x["forecast_ym"] for x in outcomes}
    for snapshot in snapshots:
        ym = snapshot["ym"]
        target_ym = engine.shift_ym(ym, 1)
        if ym in outcome_months or target_ym not in by_ym:
            continue
        # Forecast must have been snapshotted before its outcome month appeared.
        observed_value = by_ym[target_ym]["value"]
        change = engine.pct(observed_value, snapshot["reference_price_index"])
        label = engine.klass(change, protocol["frozen_flat_band_pct"])
        outcomes.append({
            "forecast_ym": ym, "outcome_ym": target_ym,
            "observed_price_index": observed_value,
            "forward_price_change_pct": change, "class": label,
            "source_collected_at": source_collected_at,
            "source_commit": source_commit,
        })
        outcome_months.add(ym)
    outcomes.sort(key=lambda x: x["forecast_ym"])

    # One new forecast is allowed only if its next-month outcome is not present.
    # Missing earlier freezes are recorded as gaps, never backfilled.
    newest = prices[-1]["ym"]
    saved = {s["ym"] for s in snapshots}
    if newest >= protocol["start_ym"] and newest not in saved:
        snapshots.append(new_snapshot(
            rows, prices, newest, protocol, source_collected_at, source_commit
        ))
    snapshots.sort(key=lambda x: x["ym"])
    return result


def make_report(protocol, journal, prices):
    seen = {s["ym"]: s for s in journal["snapshots"]}
    by_price = {p["ym"]: p for p in prices}
    by_outcome = {o["forecast_ym"]: o for o in journal.get("outcomes", [])}
    gaps = []
    for n in range(engine.ym_ord(protocol["start_ym"]), engine.ym_ord(prices[-1]["ym"]) + 1):
        ym = f"{n//12:04d}{n%12+1:02d}"
        if ym not in seen:
            gaps.append(ym)
    for ym, outcome in by_outcome.items():
        if outcome["outcome_ym"] not in by_price:
            raise ValueError("stored outcome month is not present in source")
    matched = [{**s, "target": by_outcome[s["ym"]]["class"]}
               for s in journal["snapshots"] if s["ym"] in by_outcome]
    metrics = {}
    for key in protocol["models"]:
        if matched:
            preds = [
                {"ym": p["ym"], "probabilities": p["models"][key], "target": p["target"]}
                for p in matched
            ]
            metrics[key] = audit.scores(preds)
        else:
            metrics[key] = None
    counts = {c: sum(p["target"] == c for p in matched) for c in CLASSES}
    n = len(matched)
    threshold = protocol["minimum_matured_months"]
    # Independent end-of-period evaluation is descriptive until both sample
    # size and class diversity gates are satisfied.
    is_ready = (n >= threshold and counts["up"] >= protocol["min_up"]
                and n - counts["up"] >= protocol["min_non_up"]
                and not gaps)
    return {
        "report_type": "independent_prospective_upside_shadow",
        "status": "ready_for_independent_assessment" if is_ready else "insufficient_independent_outcomes",
        "production_applied": False, "no_future_label_leakage": True,
        "source": "data_sources/reb_long_cycle.json",
        "scope": protocol["source_scope"],
        "start_ym": protocol["start_ym"], "latest_source_price_ym": prices[-1]["ym"],
        "last_forecast_ym": journal["snapshots"][-1]["ym"],
        "matured_months": n, "required_matured_months": threshold,
        "class_counts": counts, "missing_pre_outcome_snapshots": gaps,
        "metrics": metrics, "eligible_for_review": is_ready,
        "policy": "No automatic production promotion; compare all frozen candidates using the predeclared protocol.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="Append predictions/outcomes and write report")
    parser.add_argument("--check", action="store_true", help="Read-only integrity check")
    parser.add_argument("--source-commit", default=None, help="Git SHA of the source reading, for provenance")
    args = parser.parse_args()
    if args.update == args.check:
        parser.error("specify exactly one of --update or --check")
    protocol, journal, raw = load(PROTOCOL), load(JOURNAL), load(RAW)
    validate_protocol(protocol, journal)
    prices = read_prices(raw)
    rows = monthly_rows(prices)

    # The first snapshot was committed while 2026-08 was the last known month.
    # This may be verified against the source until the next monthly publication.
    if prices[-1]["ym"] == protocol["start_ym"]:
        first = forecast(rows, protocol["start_ym"], protocol)
        locked = journal["snapshots"][0]
        assert math.isclose(locked["reference_price_index"], prices[-1]["value"], abs_tol=1e-10)
        for key in protocol["models"]:
            for c in CLASSES:
                assert math.isclose(first["models"][key][c], locked["models"][key][c], abs_tol=1e-9)

    updated = record_new_observations(
        protocol, journal, prices, raw.get("collected_at"), args.source_commit
    )
    validate_protocol(protocol, updated)
    report = make_report(protocol, updated, prices)
    if args.update:
        if updated != journal:
            save(JOURNAL, updated)
        save(REPORT, report)
    print(json.dumps({
        "status": report["status"], "production_applied": False,
        "latest_source_price_ym": report["latest_source_price_ym"],
        "matured_months": report["matured_months"],
        "last_forecast_ym": report["last_forecast_ym"],
        "gaps": report["missing_pre_outcome_snapshots"],
        "eligible_for_review": report["eligible_for_review"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
