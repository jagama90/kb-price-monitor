#!/usr/bin/env python3
"""Collect exact KB complex/area-ID pairs; never substitute complex summary prices."""
import argparse
import concurrent.futures
import datetime as dt
import http.client
import json
import math
import os
from pathlib import Path
import ssl
import threading
import time
import urllib.parse
import urllib.request
from price_changes import compare

ROOT = Path(__file__).resolve().parents[1]
LOCAL = threading.local()
LOCK = threading.Lock()
STOP = threading.Event()
NEXT_REQUEST = 0.0

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')

def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) and n > 0 else None
    except (ValueError, TypeError):
        return None

def connection():
    """Reuse HTTPS connections, using the normal configured HTTPS proxy if present."""
    proxy = urllib.request.getproxies().get('https')
    if proxy:
        p = urllib.parse.urlparse(proxy)
        if p.username or p.password:
            raise RuntimeError('Authenticated proxy requires the standard urllib transport')
        conn = http.client.HTTPSConnection(p.hostname, p.port or 80, timeout=35)
        conn.set_tunnel('api.kbland.kr', 443)
    else:
        conn = http.client.HTTPSConnection('api.kbland.kr', timeout=35)
    return conn

def api_get(path, params, rate=6):
    global NEXT_REQUEST
    url = path + '?' + urllib.parse.urlencode(params)
    for attempt in range(3):
        if STOP.is_set():
            raise RuntimeError('Collection stopped after access/rate restriction')
        with LOCK:
            delay = max(0, NEXT_REQUEST-time.monotonic())
            NEXT_REQUEST = max(NEXT_REQUEST,time.monotonic()) + 1/rate
        if delay:
            time.sleep(delay)
        try:
            if not getattr(LOCAL, 'conn', None):
                LOCAL.conn = connection()
            LOCAL.conn.request('GET', url, headers={'Accept':'application/json','User-Agent':'KB-price-personal-monitor/2.0'})
            response = LOCAL.conn.getresponse()
            raw = response.read()
            if response.status in (401,403,429):
                STOP.set()
                raise RuntimeError(f'Access/rate restriction: HTTP {response.status}')
            if response.status != 200:
                raise RuntimeError(f'HTTP {response.status}')
            payload = json.loads(raw)
            body = payload.get('dataBody')
            if not isinstance(body,dict) or str(body.get('resultCode')) not in ('11000','33210'):
                raise RuntimeError('Unexpected KB response envelope')
            return body.get('data')
        except Exception:
            if getattr(LOCAL,'conn',None):
                LOCAL.conn.close()
                LOCAL.conn = None
            if STOP.is_set() or attempt == 2:
                raise
            time.sleep(2**attempt)

def normalize(complex_row, raw_rows, collected_at):
    if raw_rows is None:
        return []
    if not isinstance(raw_rows,list):
        raise ValueError('Expected a list of KB area types')
    result, seen = [], set()
    for raw in raw_rows:
        cid = int(raw['단지기본일련번호'])
        if cid != int(complex_row['complex_id']):
            raise ValueError('Wrong complex ID')
        # KB sometimes returns an empty placeholder, not an actual area type.
        if (raw.get('면적일련번호') is None and raw.get('공급면적') is None
                and raw.get('공급면적평') is None
                and str(raw.get('시세제공여부')) == '0'
                and raw.get('매매일반거래가') in (None, 0, '0')):
            continue
        aid = int(raw['면적일련번호'])
        if cid <= 0 or aid <= 0 or cid != int(complex_row['complex_id']) or aid in seen:
            raise ValueError('Wrong complex ID or duplicate area ID')
        seen.add(aid)
        supply, exclusive = number(raw.get('공급면적')), number(raw.get('전용면적'))
        # Use KB's reported decimals, not a clipped complex-wide area interval.
        supply_py = number(raw.get('공급면적평'))
        exclusive_py = number(raw.get('전용면적평'))
        if supply is None or supply_py is None:
            raise ValueError(f'Missing supply area for {cid}/{aid}')
        ai = str(raw.get('50세대미만여부')) == '1' or str(raw.get('단지AI시세여부')) == '1'
        supplied = str(raw.get('시세제공여부')) == '1'
        price = number(raw.get('매매일반거래가')) if supplied and not ai else None
        result.append({
            'complex_id':cid,'area_id':aid,'name':complex_row['name'],
            'district':complex_row['district'],'dong':complex_row['dong'],
            'households':complex_row.get('households'),
            'type_households':raw.get('세대수'),
            'built_ymd':complex_row.get('built_ymd'),
            'type_label':str(raw.get('공급면적평N') or '')+str(raw.get('주택형타입내용') or ''),
            'supply_m2':supply,'exclusive_m2':exclusive,
            'supply_pyeong':supply_py,'exclusive_pyeong':exclusive_py,
            'general_price_manwon':price,
            'price_status':'kb_general' if price is not None else ('ai_excluded' if ai else 'unavailable'),
            'price_date':raw.get('시세기준년월일') or None,
            'collected_at':collected_at,
            'url':f'https://kbland.kr/c/{cid}',
        })
    return result

def atomic_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    temporary.replace(path)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workers',type=int,default=12)
    parser.add_argument('--rate',type=float,default=6)
    parser.add_argument('--ids',help='Comma-separated complex IDs for validation only')
    parser.add_argument('--run-dir',default=None,help='Resume this exact collection run')
    parser.add_argument('--publish-data',action='store_true')
    args=parser.parse_args()
    catalog=json.loads((ROOT/'data/seoul_snapshot.json').read_text())
    complexes=catalog['items']
    if args.ids:
        ids={int(x) for x in args.ids.split(',')}
        complexes=[r for r in complexes if r['complex_id'] in ids]
    # Prioritize both regression examples and the larger complexes without dropping others.
    complexes.sort(key=lambda r:(r['complex_id'] not in (1913,15758),-(r.get('households') or 0),r['complex_id']))
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    run=Path(args.run_dir) if args.run_dir else ROOT/'data/type_runs'/stamp
    run.mkdir(parents=True,exist_ok=True)
    print(f'RUN_DIR={run} complexes={len(complexes)}',flush=True)
    def collect(row):
        checkpoint=run/f"{row['complex_id']}.json"
        if checkpoint.exists():
            saved=json.loads(checkpoint.read_text())
        else:
            raw=api_get('/land-complex/complex/mpriByType',{'단지기본일련번호':row['complex_id']},args.rate)
            saved={'complex_id':row['complex_id'],'collected_at':now(),'raw':raw}
            normalize(row,raw,saved['collected_at'])
            atomic_json(checkpoint,saved)
        return normalize(row,saved['raw'],saved['collected_at'])
    rows,errors,empty=[],[],[]
    started=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs={pool.submit(collect,r):r for r in complexes}
        for index,future in enumerate(concurrent.futures.as_completed(jobs),1):
            c=jobs[future]
            try:
                batch=future.result()
                rows.extend(batch)
                if not batch: empty.append(c['complex_id'])
            except Exception as exc:
                errors.append({'complex_id':c['complex_id'],'error':str(exc)})
            if index%100==0 or index==len(complexes):
                print(f'{index}/{len(complexes)} types={len(rows)} errors={len(errors)} elapsed={time.monotonic()-started:.0f}s',flush=True)
    rows.sort(key=lambda r:(r['district'],r['name'],r['supply_m2'],r['area_id']))
    snapshot={'schema_version':2,'source':'KB부동산 mpriByType','scope':catalog.get('scope','서울 아파트 / 개별 평형'),
        'collected_at':now(),'catalog_collected_at':catalog['collected_at'],
        'target_complex_count':len(complexes),'successful_complex_count':len(complexes)-len(errors),
        'complex_count':len({r['complex_id'] for r in rows}),'type_count':len(rows),
        'priced_count':sum(r['general_price_manwon'] is not None for r in rows),
        'district_count':len({r['district'] for r in complexes}),
        'districts':sorted({r['district'] for r in complexes}),
        'empty_complex_ids':sorted(empty),'errors':errors,'items':rows}
    atomic_json(run/'snapshot.json',snapshot)
    # Never replace a complete published snapshot with failed or sample collection.
    if args.publish_data and not errors and not args.ids and len(complexes)==catalog['complex_count']:
        current_path=ROOT/'data/seoul_types.json'
        previous=json.loads(current_path.read_text()) if current_path.exists() else None
        if previous and previous.get('schema_version')==2:
            atomic_json(ROOT/'data/previous_seoul_types.json',previous)
        atomic_json(ROOT/'data/price_changes.json',compare(previous,snapshot))
        atomic_json(ROOT/'data/seoul_types.json',snapshot)
        atomic_json(ROOT/'dist/seoul_types.json',snapshot)
        print('Validated complete collection written to data and dist.',flush=True)
    else:
        print('Staging snapshot only; published data unchanged.',flush=True)
    print(json.dumps({k:v for k,v in snapshot.items() if k not in ('items','errors','empty_complex_ids','districts')},ensure_ascii=False),flush=True)
    return 2 if errors else 0

if __name__=='__main__':
    raise SystemExit(main())
