#!/usr/bin/env python3
"""Point-in-time monthly rising-probability sensitivity audit.

Research only: never alters the certified engine or production JSON.
Model choice uses 2012-2017 data only. 2018+ is a frozen evaluation holdout.
Rows with target maturity after the prediction date are excluded.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean

import build_upside_probability_engine as engine

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "dist/long_cycle_master.json"
CERTIFIED = ROOT / "dist/upside_probability_engine.json"
FEATURES = ("m1", "m3")
CLASSES = ("up", "flat", "down")
MONTHS = ("202305", "202311", "202404", "202504", "202603")
KS = (10, 15, 20, 25, 35)
WEIGHTS = ("uniform", "inverse", "exponential", "gaussian")
MAX_K = max(KS)


def features_at_time(rows, idx, band):
    row = rows[idx]
    if any(engine.finite(row.get(f)) is None for f in FEATURES):
        return None
    cutoff = engine.ym_ord(row["ym"])
    train = []
    for historical in rows:
        historical_date = engine.ym_ord(historical["ym"])
        label = engine.klass(historical.get("fwd_1m_pct"), band)
        if historical_date is None or historical_date + 1 > cutoff or label is None:
            continue
        if any(engine.finite(historical.get(f)) is None for f in FEATURES):
            continue
        train.append({**historical, "target": label})
    if len(train) < 48:
        return None
    means = [mean(float(x[f]) for x in train) for f in FEATURES]
    sds = [
        math.sqrt(sum((x[f] - means[i]) ** 2 for x in train) / max(1, len(train) - 1)) or 1.0
        for i, f in enumerate(FEATURES)
    ]
    return {"train": train, "means": means, "sds": sds}


def neighbors(context, m1, m3):
    probe = {"m1": m1, "m3": m3}
    distances = []
    for row in context["train"]:
        squared = sum(
            ((row[f] - probe[f]) / context["sds"][i]) ** 2
            for i, f in enumerate(FEATURES)
        )
        distances.append((math.sqrt(squared), row))
    # Python stable sort and original row order exactly match the certified engine.
    return sorted(distances, key=lambda x: x[0])[:MAX_K]


def calculate(nearest, k, method):
    chosen = nearest[:k]
    assert len(chosen) == k
    distances = [d for d, _ in chosen]
    if method == "inverse":
        weights = [1.0 / (0.15 + d) for d in distances]
    elif method == "exponential":
        weights = [math.exp(-d / 0.5) for d in distances]
    elif method == "gaussian":
        weights = [math.exp(-d * d / (2 * 0.75**2)) for d in distances]
    elif method == "uniform":
        weights = [1.0] * len(chosen)
    else:
        raise ValueError(method)
    weight_scale = k / sum(weights)
    counts = {c: 1.0 for c in CLASSES}
    for weight, (_, row) in zip(weights, chosen):
        counts[row["target"]] += weight * weight_scale
    denom = k + 3
    return {
        "probabilities": {c: counts[c] / denom for c in CLASSES},
        "neighbors": [row["ym"] for _, row in chosen],
        "neighbor_classes": [row["target"] for _, row in chosen],
    }


def scores(predictions):
    matured = [p for p in predictions if p.get("target") is not None]
    standard = engine.metrics(matured)
    jumps = [
        abs(predictions[i]["probabilities"]["up"] - predictions[i - 1]["probabilities"]["up"]) * 100
        for i in range(1, len(predictions))
        if engine.ym_ord(predictions[i]["ym"]) == engine.ym_ord(predictions[i - 1]["ym"]) + 1
    ]
    matrix = {c: {"tp": 0, "fp": 0, "fn": 0} for c in CLASSES}
    correct = 0
    for p in matured:
        predicted = max(CLASSES, key=lambda c: p["probabilities"][c])
        actual = p["target"]
        correct += predicted == actual
        for c in CLASSES:
            matrix[c]["tp"] += predicted == c and actual == c
            matrix[c]["fp"] += predicted == c and actual != c
            matrix[c]["fn"] += predicted != c and actual == c
    f1 = []
    for c in CLASSES:
        entry = matrix[c]
        denom = 2 * entry["tp"] + entry["fp"] + entry["fn"]
        f1.append(2 * entry["tp"] / denom if denom else 0.0)
    return {
        **standard,
        "accuracy": round(correct / len(matured), 4) if matured else None,
        "macro_f1": round(mean(f1), 4) if matured else None,
        "monthly_jump_mean_pp": round(mean(jumps), 2) if jumps else None,
        "monthly_jump_ge30_count": sum(j >= 30 for j in jumps),
    }


def turning_detection(panel, key):
    points = [p for p in panel if p["ym"] >= "201601"]
    actual = [p["target"] for p in points]
    # Ex-post evaluation definition. It is never supplied to the prediction model.
    turns = [
        i for i in range(1, len(points) - 1)
        if actual[i] == "up" and actual[i - 1] != "up" and actual[i + 1] == "up"
    ]
    delays = []
    for i in turns:
        hits = [
            offset for offset in range(-3, 4)
            if 0 < i + offset < len(points)
            and points[i + offset]["models"][key]["probabilities"]["up"] >= 0.5
            and points[i + offset - 1]["models"][key]["probabilities"]["up"] < 0.5
        ]
        if hits:
            delays.append(min(hits, key=lambda delta: (abs(delta), delta)))
    return {
        "actual_up_turns": len(turns),
        "matched": len(delays),
        "mean_detection_lag_months": round(mean(delays), 2) if delays else None,
    }


def paired_block_bootstrap(panel, key, block=12, reps=4000):
    # Same prediction dates, paired losses; moving blocks keep local dependence.
    import random
    relevant = [p for p in panel if p["ym"] >= "201801" and p["target"]]
    def squared(p, model):
        return sum(
            (p["models"][model]["probabilities"][c] - (1 if p["target"] == c else 0)) ** 2
            for c in CLASSES
        )
    values = [squared(p, "uniform_10") - squared(p, key) for p in relevant]
    n = len(values)
    rng = random.Random(20261012 + block)
    sample = []
    for _ in range(reps):
        chosen = []
        while len(chosen) < n:
            start = rng.randrange(n - block + 1)
            chosen.extend(values[start:start + block])
        sample.append(mean(chosen[:n]))
    sample.sort()
    return {
        "samples": reps, "block_months": block,
        "paired_brier_improvement": round(mean(values), 5),
        "ci95": [round(sample[int(0.025 * reps)], 5), round(sample[int(0.975 * reps) - 1], 5)],
    }


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--json", type=Path, help="Optional research-only report output")
    args.add_argument("--check", action="store_true", help="Verify certified baseline reproduction")
    options = args.parse_args()
    source = json.loads(HISTORY.read_text(encoding="utf-8"))
    certified = json.loads(CERTIFIED.read_text(encoding="utf-8"))
    rows = engine.monthly_rows(source)
    pre_2012 = [r for r in rows if r["ym"] < "201201"]
    band = engine.quantile([
        abs(r["fwd_1m_pct"]) for r in pre_2012 if r["fwd_1m_pct"] is not None
    ], 0.25)
    assert band is not None
    panel = []
    for idx, row in enumerate(rows):
        if row["ym"] < "201201":
            continue
        context = features_at_time(rows, idx, band)
        if context is None:
            continue
        nearest = neighbors(context, row["m1"], row["m3"])
        result = {
            "ym": row["ym"], "target": engine.klass(row.get("fwd_1m_pct"), band),
            "training_observations": len(context["train"]),
            "m1": row["m1"], "m3": row["m3"], "models": {},
        }
        for k in KS:
            for method in WEIGHTS:
                result["models"][f"{method}_{k}"] = calculate(nearest, k, method)
        panel.append(result)

    all_scores = {}
    for k in KS:
        for method in WEIGHTS:
            key = f"{method}_{k}"
            all_scores[key] = {
                "selection": scores([
                    {**p["models"][key], "ym": p["ym"], "target": p["target"]}
                    for p in panel if p["ym"] < "201801"
                ]),
                "holdout": scores([
                    {**p["models"][key], "ym": p["ym"], "target": p["target"]}
                    for p in panel if p["ym"] >= "201801"
                ]),
                "turning": turning_detection(panel, key),
            }
    baseline = all_scores["uniform_10"]
    frozen = certified["validation"]["1"]
    if options.check:
        assert abs(baseline["selection"]["multiclass_brier"] - frozen["selection"]["multiclass_brier"]) <= .001
        assert abs(baseline["holdout"]["multiclass_brier"] - frozen["holdout"]["multiclass_brier"]) <= .001
        assert baseline["holdout"]["n"] == frozen["holdout"]["n"]
        assert certified["model"]["selected_k"]["1"] == 10
        assert certified["no_future_leakage"] is True

    winner = min(all_scores, key=lambda key: (
        all_scores[key]["selection"]["multiclass_brier"],
        key
    ))
    candidate = all_scores[winner]
    boot = {
        str(block): paired_block_bootstrap(panel, winner, block)
        for block in (6, 12)
    }
    reasons = []
    sel0 = baseline["selection"]["multiclass_brier"]
    sel1 = candidate["selection"]["multiclass_brier"]
    test0, test1 = baseline["holdout"], candidate["holdout"]
    if (sel0 - sel1) / sel0 < 0.03:
        reasons.append("selection Brier gain below predeclared 3% materiality floor")
    if (test0["multiclass_brier"] - test1["multiclass_brier"]) / test0["multiclass_brier"] < .05:
        reasons.append("holdout Brier gain below 5% materiality floor")
    if test1["up_auc"] < test0["up_auc"] or test1["up_ece"] > test0["up_ece"]:
        reasons.append("holdout discrimination or calibration regressed")
    if test1["monthly_jump_mean_pp"] > test0["monthly_jump_mean_pp"]:
        reasons.append("mean month-to-month volatility increased")
    if candidate["turning"]["matched"] < baseline["turning"]["matched"] or (
        candidate["turning"]["mean_detection_lag_months"]
        > baseline["turning"]["mean_detection_lag_months"]
    ):
        reasons.append("turning point detection worsened")
    if any(b["ci95"][0] <= 0 for b in boot.values()):
        reasons.append("paired 6/12-month block-bootstrap CI includes no improvement")

    cases = []
    for ym in MONTHS:
        i = next((j for j, p in enumerate(panel) if p["ym"] == ym), None)
        if i is None or i == 0:
            continue
        curr, prev = panel[i], panel[i - 1]
        prev10 = prev["models"]["uniform_10"]
        new10 = curr["models"]["uniform_10"]
        context = features_at_time(rows, next(j for j, r in enumerate(rows) if r["ym"] == ym), band)
        old_inputs_in_new = calculate(neighbors(context, prev["m1"], prev["m3"]), 10, "uniform")
        only_m1 = calculate(neighbors(context, curr["m1"], prev["m3"]), 10, "uniform")
        only_m3 = calculate(neighbors(context, prev["m1"], curr["m3"]), 10, "uniform")
        def up(p):
            return p["probabilities"]["up"] * 100
        pool = up(old_inputs_in_new) - up(prev10)
        d1 = (up(only_m1) - up(old_inputs_in_new) + up(new10) - up(only_m3)) / 2
        d3 = (up(only_m3) - up(old_inputs_in_new) + up(new10) - up(only_m1)) / 2
        cases.append({
            "ym": ym, "prior_up_pct": round(up(prev10), 1),
            "up_pct": round(up(new10), 1),
            "monthly_jump_pp": round(up(new10) - up(prev10), 1),
            "momentum_1m_pct": [round(prev["m1"], 3), round(curr["m1"], 3)],
            "momentum_3m_pct": [round(prev["m3"], 3), round(curr["m3"], 3)],
            "retained_nearest_10": len(set(prev10["neighbors"]) & set(new10["neighbors"])),
            "attribution_pp": {
                "training_pool": round(pool, 1),
                "momentum_1m_shapley": round(d1, 1),
                "momentum_3m_shapley": round(d3, 1),
            },
            "next_month_outcome": curr["target"],
            "alternative_up_pct": {
                key: round(curr["models"][key]["probabilities"]["up"] * 100, 1)
                for key in ("inverse_10", "inverse_15")
            },
        })

    report = {
        "report_type": "monthly_probability_sensitivity_audit",
        "production_applied": False,
        "decision": "research_only_preserve_certified" if reasons else "candidate_requires_separate_certification",
        "scope": certified.get("scope"),
        "period": {"first": "201601", "last": rows[-1]["ym"], "selection": "201201..201712", "holdout_start": "201801"},
        "no_future_leakage": True,
        "horizon_months": 1,
        "flat_band_pct": round(band, 6),
        "baseline": baseline,
        "selection_winner": winner,
        "winner_scores": candidate,
        "winner_bootstrap": boot,
        "all_candidates": all_scores,
        "focused_cases": cases,
        "blocking_reasons": reasons,
        "note": "Only 1-month probabilities audited. 3/6-month and rejected 12-month models are unchanged.",
    }
    if options.json:
        options.json.parent.mkdir(parents=True, exist_ok=True)
        options.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"], "winner": winner,
        "baseline_selection_brier": sel0, "winner_selection_brier": sel1,
        "baseline_holdout_brier": test0["multiclass_brier"],
        "winner_holdout_brier": test1["multiclass_brier"],
        "blocking_reasons": reasons, "focused_cases": len(cases),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
