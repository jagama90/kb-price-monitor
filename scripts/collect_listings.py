#!/usr/bin/env python3
"""Collect KB lowest asking prices for configured buy-watchlist area IDs."""
import argparse, datetime as dt, http.client, json, os, random, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
API_HOST='api.kbland.kr'
API_PATH='/land-property/propList/main'

def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    tmp.replace(path)

def connection():
    proxy=urllib.request.getproxies().get('https')
    if proxy:
        p=urllib.parse.urlparse(proxy)
        conn=http.client.HTTPSConnection(p.hostname,p.port or 80,timeout=35)
        conn.set_tunnel(API_HOST,443)
        return conn
    return http.client.HTTPSConnection(API_HOST,timeout=35)

def post(payload, token=None):
    cookie=os.getenv('KB_COOKIE','').strip()
    # Match the request headers used by the KB Land web client.
    kst=dt.timezone(dt.timedelta(hours=9))
    timestamp=dt.datetime.now(kst).strftime('%Y%m%d%H%M%S%f')[:17]
    traceid='user_'+timestamp[2:14]+str(random.randint(1000,9999))
    headers={'Accept':'application/json, text/plain, */*','Accept-Language':'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
             'Content-Type':'application/json','Origin':'https://kbland.kr','Referer':'https://kbland.kr/',
             'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36',
             'Timestamp':timestamp,'Traceid':traceid,'Webservice':'1'}
    if cookie: headers['Cookie']=cookie
    if token: headers['Authorization']='bearer '+token.removeprefix('bearer ').removeprefix('Bearer ')
    conn=connection()
    try:
        body=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        conn.request('POST',API_PATH,body=body,headers=headers)
        r=conn.getresponse(); raw=r.read()
        if r.status!=200: raise RuntimeError(f'HTTP {r.status}')
        try:
            data=json.loads(raw)
        except Exception:
            ctype=r.getheader('Content-Type')
            preview=raw[:800].decode('utf-8','replace').replace('\n',' ')
            raise RuntimeError(f'non-JSON HTTP {r.status} content-type={ctype!r} bytes={len(raw)} body={preview!r}')
        h=data.get('dataHeader') or {}
        if str(h.get('resultCode'))!='10000': raise RuntimeError(f"KB result {h.get('resultCode')}: {h.get('message')}")
        return (data.get('dataBody') or {}).get('data') or {}
    finally: conn.close()

def payload_for(c,area_id,page):
    # The listing endpoint accepts the selection fields below; no user-specific fields are stored.
    return {'단지기본일련번호':c['complex_id'],'단지명':c.get('kb_name') or c.get('user_name'),
      '매물종별구분':'01','페이지번호':page,'페이지목록수':10,'중복타입':'02',
      '정렬타입':'priceA','매물거래구분':'1','면적일련번호':str(area_id),
      '전자계약여부':'0','비대면대출여부':'0','클린주택여부':'0','honeyYn':'0','건물동명':''}

def collect_one(c,area_id,token):
    listings=[]; pages=1
    for page in range(1,51):
        data=post(payload_for(c,area_id,page),token)
        pages=int(data.get('페이지개수') or pages or 1)
        batch=data.get('propertyList') or []
        listings.extend(batch)
        if page>=pages or not batch: break
    sale=[x for x in listings if str(x.get('매물거래구분'))=='1' and int(x.get('면적일련번호') or 0)==int(area_id) and x.get('매매가')]
    if not sale: return {'lowest_ask_manwon':None,'listing_count':0,'page_count':pages}
    x=min(sale,key=lambda y:int(y['매매가']))
    return {'lowest_ask_manwon':int(x['매매가']),'listing_count':int(x.get('totalCnt') or len(sale)),
      'page_count':pages,'building':x.get('건물동명'),'floor':x.get('해당층수'),'direction':x.get('방향구분명'),
      'listing_id':x.get('매물일련번호'),'verified_date':x.get('매물확인년월일'),'registered_date':x.get('등록년월일'),
      'duplicate_count':x.get('중복개수'),'supply_m2':x.get('순공급면적'),'exclusive_m2':x.get('순전용면적')}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--complex-id',type=int); ap.add_argument('--area-id',type=int); ap.add_argument('--publish',action='store_true')
    a=ap.parse_args(); token=os.getenv('KB_AUTH_TOKEN')
    master=json.loads((ROOT/'data/buy_watchlist_master.json').read_text(encoding='utf-8'))
    targets=json.loads((ROOT/'data/buy_watchlist_targets.json').read_text(encoding='utf-8'))
    cmap={x.get('complex_id'):x for x in master['items'] if x.get('complex_id')}
    rows=[]; errors=[]
    for t in targets['items']:
        cid=t.get('complex_id')
        if a.complex_id and cid!=a.complex_id: continue
        c=cmap.get(cid)
        if not c: continue
        for aid in t.get('area_ids',[]):
            if a.area_id and aid!=a.area_id: continue
            try:
                r=collect_one(c,aid,token); r.update({'complex_id':cid,'area_id':aid,'name':c['user_name'],'collected_at':now()}); rows.append(r)
                print(json.dumps(r,ensure_ascii=False),flush=True)
            except Exception as e:
                errors.append({'complex_id':cid,'area_id':aid,'error':str(e)}); print(errors[-1],flush=True)
    snap={'schema_version':1,'source':'KB부동산 propList/main','collected_at':now(),'items':rows,'errors':errors}
    atomic_json(ROOT/'data/listing_asks_probe.json',snap)
    if a.publish and not errors: atomic_json(ROOT/'data/buy_watchlist_listings.json',snap)
    return 2 if errors else 0
if __name__=='__main__': raise SystemExit(main())
