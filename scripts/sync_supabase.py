#!/usr/bin/env python3
"""Atomically publish a validated schema_version=2 KB snapshot to Supabase."""
from __future__ import annotations
import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BATCH = 500

def request(base, key, path, method='GET', body=None, prefer=None):
    raw = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    headers = {'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    if prefer:
        headers['Prefer'] = prefer
    req = urllib.request.Request(base.rstrip('/') + path, data=raw, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            payload = response.read()
            return json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')
        raise RuntimeError(f'Supabase {exc.code}: {detail[:1000]}') from exc

def validate(data):
    if data.get('schema_version') != 2 or data.get('errors'):
        raise ValueError('Only a complete schema_version=2 snapshot can be published')
    rows = data.get('items') or []
    keys = {(r['complex_id'], r['area_id']) for r in rows}
    if len(keys) != len(rows) or len(rows) != data.get('type_count'):
        raise ValueError('Duplicate keys or type count mismatch')
    if any(not r.get('supply_pyeong') for r in rows):
        raise ValueError('Missing supply area')
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('snapshot', nargs='?', default='data/seoul_types.json')
    args = parser.parse_args()
    data = json.loads(Path(args.snapshot).read_text(encoding='utf-8'))
    rows = validate(data)
    base = os.environ['SUPABASE_URL']
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    collection = {
        'schema_version': 2, 'scope': data['scope'], 'districts': data['districts'],
        'collected_at': data['collected_at'], 'catalog_collected_at': data.get('catalog_collected_at'),
        'target_complex_count': data['target_complex_count'],
        'successful_complex_count': data['successful_complex_count'],
        'type_count': data['type_count'], 'priced_count': data['priced_count'],
        'empty_complex_count': len(data.get('empty_complex_ids') or []), 'status': 'importing'
    }
    created = request(base, key, '/rest/v1/kb_collections?select=id', 'POST', collection, 'return=representation')
    collection_id = created[0]['id']
    fields = ('complex_id','area_id','name','district','dong','households','type_households',
              'built_ymd','type_label','supply_m2','exclusive_m2','supply_pyeong',
              'exclusive_pyeong','general_price_manwon','price_status','price_date','collected_at','url')
    for start in range(0, len(rows), BATCH):
        payload = [dict(collection_id=collection_id, **{k:r.get(k) for k in fields}) for r in rows[start:start+BATCH]]
        request(base, key, '/rest/v1/kb_import_rows', 'POST', payload, 'return=minimal')
        print(f'uploaded {min(start+BATCH,len(rows))}/{len(rows)}', flush=True)
    result = request(base, key, '/rest/v1/rpc/promote_kb_collection', 'POST', {'p_collection_id': collection_id})
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()

