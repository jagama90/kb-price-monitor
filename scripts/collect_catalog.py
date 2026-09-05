#!/usr/bin/env python3
"""Refresh the complex catalog only. Summary prices MUST NOT be used in the UI."""

from __future__ import annotations

import concurrent.futures
import csv
import json
import os
import sys
import time
from pathlib import Path
from collect_types import api_get, atomic_json

API = "https://api.kbland.kr"
OUT = Path(__file__).resolve().parents[1] / "data"
WORKERS = 12


def parallel(items, fn, label):
    results, errors = [], []
    total = len(items)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fn, item): item for item in items}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            item = futures[future]
            try:
                value = future.result()
                if isinstance(value, list):
                    results.extend(value)
                elif value is not None:
                    results.append(value)
            except Exception as exc:
                errors.append({"item": item, "error": str(exc)})
            if index % 25 == 0 or index == total:
                print(f"{label}: {index}/{total} (errors {len(errors)})", flush=True)
    return results, errors


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    districts = api_get("/land-complex/map/siGunGuAreaNameList", {"시도명": "서울시"})
    if not isinstance(districts, list) or len(districts) != 25:
        raise ValueError('서울 25개 구 목록이 완전하지 않습니다. 기존 자료를 보존합니다.')
    requested = {x.strip() for x in os.getenv('KB_TARGET_DISTRICTS', '').split(',') if x.strip()}
    if requested:
        available = {row['시군구명'] for row in districts}
        missing = requested - available
        if missing:
            raise ValueError(f'존재하지 않는 자치구: {sorted(missing)}')
        districts = [row for row in districts if row['시군구명'] in requested]
    print(f"districts: {len(districts)}", flush=True)

    def district_dongs(row):
        data = api_get(
            "/land-complex/map/stutDongAreaNameList",
            {"시도명": "서울시", "시군구명": row["시군구명"]},
        )
        # KB returns resultCode 33210 with data=null when a district has no rows.
        return [dict(dong, 시군구명=row["시군구명"]) for dong in (data or [])]

    dongs, errors1 = parallel(districts, district_dongs, "dongs")
    print(f"legal dongs: {len(dongs)}", flush=True)

    dong_by_code = {row["법정동코드"]: row for row in dongs}

    def dong_complexes(row):
        data = api_get(
            "/land-complex/complexComm/hscmList", {"법정동코드": row["법정동코드"]}
        )
        return [
            dict(item, 시군구명=row["시군구명"], 법정동명=row["법정동명"])
            for item in (data or [])
            if item.get("매물종별구분") == "01"
        ]

    complexes_raw, errors2 = parallel(dongs, dong_complexes, "complex lists")
    complexes = {
        int(item["단지기본일련번호"]): item
        for item in complexes_raw
        if item.get("단지기본일련번호")
    }
    print(f"unique apartment complexes: {len(complexes)}", flush=True)

    def complex_prices(batch):
        joined = ",".join(str(item["단지기본일련번호"]) for item in batch)
        data = api_get(
            "/land-complex/complex/brifs",
            {"단지기본일련번호": joined, "매물종별구분": "01", "정렬기준": "price"},
        )
        expected = {int(item['단지기본일련번호']) for item in batch}
        if not data or {int(row['단지기본일련번호']) for row in data} != expected:
            raise ValueError('단지 기본정보 응답에 요청한 단지가 누락되었습니다.')
        found = []
        for row in data:
            complex_id = int(row["단지기본일련번호"])
            item = complexes.get(complex_id, {})
            found.append({
                "complex_id": complex_id,
                "name": row.get("단지명") or item.get("단지명"),
                "district": row.get("시군구명") or item.get("시군구명"),
                "dong": row.get("법정동명") or item.get("법정동명"),
                "households": row.get("총세대수"),
                "built_ymd": row.get("입주년월") or row.get("준공년월"),
                "min_area_m2": row.get("최소공급면적"),
                "max_area_m2": row.get("최대공급면적"),
                "min_price_manwon": row.get("최소매매일반거래가"),
                "max_price_manwon": row.get("최대매매일반거래가"),
                "sale_count": row.get("매매건수"),
                "lat": row.get("wgs84위도") or item.get("wgs84위도"),
                "lng": row.get("wgs84경도") or item.get("wgs84경도"),
                "url": f"https://kbland.kr/c/{complex_id}",
            })
        return found

    complex_rows = list(complexes.values())
    batches = [complex_rows[i:i + 80] for i in range(0, len(complex_rows), 80)]
    priced, errors3 = parallel(batches, complex_prices, "price summary batches")
    priced.sort(key=lambda row: (row.get("district") or "", row.get("dong") or "", row.get("name") or ""))

    snapshot = {
        "source": "KB부동산",
        "scope": "서울시 아파트 / " + ','.join(sorted(row['시군구명'] for row in districts)),
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "district_count": len(districts),
        "complex_count": len(priced),
        "priced_count": sum(bool(row.get("min_price_manwon")) for row in priced),
        "items": priced,
    }
    errors = errors1 + errors2 + errors3
    atomic_json(OUT / 'collection_errors.json', errors)
    if errors:
        print(f'Catalog incomplete: {len(errors)} errors. Previous catalog preserved.', flush=True)
        return 2
    atomic_json(OUT / 'seoul_snapshot.json', snapshot)
    with (OUT / "seoul_snapshot.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        columns = list(priced[0].keys()) if priced else []
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(priced)
    print(
        f"complete: complexes={len(priced)} priced={snapshot['priced_count']} errors={len(errors)}",
        flush=True,
    )
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
