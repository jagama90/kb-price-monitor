#!/usr/bin/env python3
"""Build the purchase-watchlist master from the validated KB type snapshot."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def write(name, value):
    (DATA / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    watch = load("buy_watchlist.json")
    catalog = load("seoul_snapshot.json")
    type_snapshot = load("seoul_types.json")

    catalog_by_id = {int(x["complex_id"]): x for x in catalog.get("items", [])}
    types_by_id = {}
    for row in type_snapshot.get("items", []):
        types_by_id.setdefault(int(row["complex_id"]), []).append(row)

    items = []
    matched = 0
    priced_complexes = 0
    missing_ids = []

    for watched in watch["items"]:
        out = dict(watched)
        cid = watched.get("complex_id")
        rows = sorted(
            types_by_id.get(int(cid), []) if cid is not None else [],
            key=lambda x: (x.get("supply_m2") or 0, x.get("area_id") or 0),
        )
        cat = catalog_by_id.get(int(cid)) if cid is not None else None

        if cat:
            matched += 1
            out.update({
                "dong": cat.get("dong"),
                "households": cat.get("households"),
                "built_ymd": cat.get("built_ymd"),
            })
        elif cid is not None:
            missing_ids.append(int(cid))

        normalized = []
        for row in rows:
            normalized.append({
                "area_id": row.get("area_id"),
                "type_label": row.get("type_label"),
                "supply_m2": row.get("supply_m2"),
                "exclusive_m2": row.get("exclusive_m2"),
                "type_households": row.get("type_households"),
                "general_price_manwon": row.get("general_price_manwon"),
                "price_status": row.get("price_status"),
                "price_date": row.get("price_date"),
            })

        out["type_count"] = len(normalized)
        out["priced_type_count"] = sum(
            x["general_price_manwon"] is not None for x in normalized
        )
        out["types"] = normalized
        if out["priced_type_count"]:
            priced_complexes += 1
        items.append(out)

    payload = {
        "schema_version": 2,
        "source": "KB부동산 + user purchase watchlist",
        "kb_collected_at": type_snapshot.get("collected_at"),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "complex_count": len(items),
        "matched_in_snapshot": matched,
        "priced_complex_count": priced_complexes,
        "missing_complex_ids": missing_ids,
        "items": items,
    }
    if len(items) != watch.get("count"):
        raise ValueError("watchlist count mismatch")
    if missing_ids:
        raise ValueError(
            "KB snapshot does not cover watchlist IDs: " + ",".join(map(str, missing_ids))
        )

    write("buy_watchlist_master.json", payload)
    write("buy_watchlist_types.json", {
        "schema_version": 2,
        "snapshot_collected_at": type_snapshot.get("collected_at"),
        "complex_count": len(items),
        "matched_type_complex_count": sum(bool(x["types"]) for x in items),
        "type_row_count": sum(len(x["types"]) for x in items),
        "items": items,
    })
    print(json.dumps({
        "complex_count": len(items),
        "matched_in_snapshot": matched,
        "priced_complex_count": priced_complexes,
        "type_row_count": sum(len(x["types"]) for x in items),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
