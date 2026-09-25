#!/usr/bin/env python3
"""Collect KB lowest asking prices for configured buy-watchlist area IDs."""
import argparse, datetime as dt, http.client, json, os, random, re, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
API_HOST='api.kbland.kr'
API_PATH='/land-property/propList/main'
PRICE_PATH='/land-price/price/complex/integrationChart'

def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def norm_name(s):
    return re.sub(r'[^0-9A-Za-z가-힣]','',str(s or '')).replace('아파트','').lower()
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
    cookie=os.getenv('KB_COOKIE','').strip() or (('WMONID='+os.getenv('KB_WMONID','').strip()) if os.getenv('KB_WMONID','').strip() else '')
    # Match the request headers used by the KB Land web client.
    kst=dt.timezone(dt.timedelta(hours=9))
    timestamp=dt.datetime.now(kst).strftime('%Y%m%d%H%M%S%f')[:17]
    traceid=os.getenv('KB_TRACE_ID','').strip() or ('user_'+timestamp[2:14]+str(random.randint(1000,9999)))
    headers={'Accept':'application/json, text/plain, */*','Accept-Language':'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
             'Content-Type':'application/json','Origin':'https://kbland.kr','Referer':'https://kbland.kr/',
             'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36',
             'Timestamp':timestamp,'Traceid':traceid,'Webservice':'1',
             'Sec-Fetch-Dest':'empty','Sec-Fetch-Mode':'cors','Sec-Fetch-Site':'same-site',
             'Sec-CH-UA':'\"Chromium\";v=\"153\", \"Google Chrome\";v=\"153\", \"Not_A Brand\";v=\"99\"',
             'Sec-CH-UA-Mobile':'?0','Sec-CH-UA-Platform':'\"Windows\"'}
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
    # propList/main expects the complex summary context sent by the KB web client,
    # not only the filter fields.
    p={'단지기본일련번호':c['complex_id'],'단지명':c.get('kb_name') or c.get('user_name'),
       '매물종별구분':'01','매물종별구분명':'아파트',
       '재건축여부':str(c.get('rebuild_yn') or '0'),'도시형생활주택여부':'0',
       '준공년월':c.get('built_ymd') or '','총세대수':c.get('households') or 0,
       '최소공급면적':c.get('min_area_m2') or '','최대공급면적':c.get('max_area_m2') or '',
       '최소매매일반거래가':c.get('min_price_manwon') or 0,'최대매매일반거래가':c.get('max_price_manwon') or 0,
       '매매건수':c.get('sale_count') or 0,'시세여부':'Y','시세노출사용여부':'Y',
       '관심단지여부':'0','단지알림수신여부':'0','wgs84경도':str(c.get('lng') or ''),
       'wgs84위도':str(c.get('lat') or ''),'50세대미만여부':'0','AI시세여부':'0','단지AI시세여부':'0',
       '페이지번호':page,'페이지목록수':10,'중복타입':'02','정렬타입':'priceA',
       '매물거래구분':'1','면적일련번호':str(area_id),'전자계약여부':'0',
       '비대면대출여부':'0','클린주택여부':'0','honeyYn':'0','건물동명':''}
    # Exact known KB context for the first verification target.
    if int(c['complex_id'])==1947:
        p.update({'물건식별자':'KBM002217','이미지디렉토리':2217,'준공년월':'1997.03','준공년수':30,
          '총세대수':2064,'총동수':14,'최소전용면적':'59.92','최대전용면적':'84.69',
          '최소공급면적':'81.21','최대공급면적':'110.67','최소전용면적평':'18.1','최대전용면적평':'25.6',
          '최소공급면적평':'24','최대공급면적평':'33','최소계약면적':'94.75','최대계약면적':'129.80',
          '최소계약면적평':'28','최대계약면적평':'39','최소매매일반거래가':189500,'최대매매일반거래가':217500,
          '최소전세일반거래가':74500,'최대전세일반거래가':86500,'매매건수':410,'전세건수':51,'월세건수':30,
          '관심단지여부':'1','호실정보존재여부':'1','시군구명':'송파구','법정동명':'가락동','관심등록수':356,
          'viewCount':81,'입주년월':'199611','등수':2,'이미지파일명':'MjIxNzEwMDI4NTQ1NDA=.jpg',
          '이미지파일명_800':'MjIxNzEwMDI4NTQ1NzI=.jpg','이미지파일명_1920':'MjIxNzEwMDI4NTQ1MzE=.jpg',
          '컨텐츠경로':'/kbstar/land/img/alian/kms/complex/photo/objctidnfr/2217/','이미지도메인URL':'https://file.kbland.kr/image',
          '전자계약가능개수':'0'})
    return p



def get_integration_chart(complex_id,area_id):
    q=urllib.parse.urlencode({'단지기본일련번호':complex_id,'면적일련번호':area_id})
    req=urllib.request.Request('https://api.kbland.kr'+PRICE_PATH+'?'+q,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json','Referer':f'https://kbland.kr/c/{complex_id}'})
    with urllib.request.urlopen(req,timeout=25) as r:
        body=json.loads(r.read())
    return (body.get('dataBody') or {}).get('data') or {}

def latest_trade_from_chart(data):
    # KB integration payload schemas have changed; search recursively for the newest sale transaction.
    found=[]
    def walk(x):
        if isinstance(x,dict):
            date=x.get('거래일자') or x.get('계약일자') or x.get('거래년월일') or x.get('계약년월일')
            price=x.get('거래금액') or x.get('매매거래가') or x.get('실거래가') or x.get('매매가')
            if date and price:
                try:
                    p=int(str(price).replace(',','')); ds=re.sub(r'[^0-9]','',str(date))
                    if p>0 and len(ds)>=6: found.append((ds,p))
                except Exception: pass
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(data)
    if not found:return (None,None)
    ds,p=max(found,key=lambda z:z[0]);return (p,ds)

def collect_one(c,area_id,token):
    listings=[]; pages=1
    for page in range(1,51):
        data=post(payload_for(c,area_id,page),token)
        pages=int(data.get('페이지개수') or pages or 1)
        batch=data.get('propertyList') or []
        listings.extend(batch)
        if page>=pages or not batch: break
    sale=[x for x in listings if str(x.get('매물거래구분'))=='1' and int(x.get('면적일련번호') or 0)==int(area_id) and x.get('매매가')]
    if not sale: return {'lowest_ask_manwon':None,'avg_ask_manwon':None,'listing_count':0,'page_count':pages}
    x=min(sale,key=lambda y:int(y['매매가']))
    # KB listing rows already expose the asking prices used by KB's own listing-average display.
    # Deduplicate by listing id before averaging when the same listing is repeated across pages.
    uniq={str(y.get('매물일련번호') or i):y for i,y in enumerate(sale)}; prices=[int(y['매매가']) for y in uniq.values() if y.get('매매가')]
    return {'lowest_ask_manwon':int(x['매매가']),'avg_ask_manwon':int(round(sum(prices)/len(prices))) if prices else None,'listing_count':int(x.get('totalCnt') or len(sale)),
      'page_count':pages,'building':x.get('건물동명'),'floor':x.get('해당층수'),'direction':x.get('방향구분명'),
      'listing_id':x.get('매물일련번호'),'verified_date':x.get('매물확인년월일'),'registered_date':x.get('등록년월일'),
      'duplicate_count':x.get('중복개수'),'supply_m2':x.get('순공급면적'),'exclusive_m2':x.get('순전용면적')}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--complex-id',type=int); ap.add_argument('--area-id',type=int); ap.add_argument('--publish',action='store_true')
    a=ap.parse_args(); token=os.getenv('KB_AUTH_TOKEN')
    master=json.loads((ROOT/'data/buy_watchlist_master.json').read_text(encoding='utf-8'))
    target_payload=json.loads((ROOT/'data/buy_watchlist_targets.json').read_text(encoding='utf-8'))
    targets=target_payload.get('items') or []
    cmap={x.get('complex_id'):x for x in master['items'] if x.get('complex_id')}
    nmap={x.get('user_name'):x for x in master['items']}
    nnmap={norm_name(x.get('user_name')):x for x in master['items']}
    kbmap={norm_name(x.get('kb_name')):x for x in master['items'] if x.get('kb_name')}
    rows=[]; errors=[]; warnings=[]; resolved_targets=0; unresolved_targets=[]; known_unavailable_targets=[]
    for t in targets:
        c=cmap.get(t.get('complex_id')) or nmap.get(t.get('name')) or nnmap.get(norm_name(t.get('name'))) or kbmap.get(norm_name(t.get('name')))
        if c and not c.get('complex_id') and c.get('status') in ('confirmed_preoccupancy','preoccupancy'):
            known_unavailable_targets.append({'name':t.get('name'),'reason':'preoccupancy_no_kb_complex','status':c.get('status')})
            continue
        if not c or not c.get('complex_id'):
            unresolved_targets.append({'name':t.get('name'),'reason':'complex_not_resolved'})
            continue
        cid=c['complex_id']
        if a.complex_id and cid!=a.complex_id: continue
        aids=t.get('area_ids') or []
        if not aids:
            lo=t.get('min_pyeong'); hi=t.get('max_pyeong')
            for typ in c.get('types',[]):
                try: p=float(re.search(r'\d+(?:\.\d+)?',str(typ.get('type_label',''))).group())
                except Exception: continue
                if (lo is None or p>=float(lo)) and (hi is None or p<=float(hi)): aids.append(typ.get('area_id'))
        if not aids:
            unresolved_targets.append({'name':t.get('name'),'complex_id':cid,'reason':'target_area_not_resolved','selection':t.get('selection')})
            continue
        resolved_targets+=1
        for aid in aids:
            if not aid or (a.area_id and aid!=a.area_id): continue
            try:
                typ=next((z for z in c.get('types',[]) if int(z.get('area_id') or 0)==int(aid)),{})
                # Never copy the server page's default visible type into another area_id.
                # Exact KB general price comes from the validated master snapshot.
                r={'lowest_ask_manwon':None,'avg_ask_manwon':None,'listing_count':None,'page_count':None,
                   'kb_general_check_manwon':typ.get('general_price_manwon'),'kb_price_date':typ.get('price_date')}
                # Asking-price API is area-id scoped. Failure is non-fatal: downstream keeps last-good.
                try:
                    ask=collect_one(c,aid,token)
                    for k in ('lowest_ask_manwon','avg_ask_manwon','listing_count','page_count','building','floor','direction','listing_id','verified_date','registered_date','duplicate_count','supply_m2','exclusive_m2'):
                        if ask.get(k) is not None:r[k]=ask.get(k)
                except Exception as ae:
                    warnings.append({'complex_id':cid,'area_id':aid,'kind':'asking_price_unavailable','error':str(ae)})
                # Recent trade is read only from the exact area-id integration endpoint.
                try:
                    chart=get_integration_chart(cid,aid); trade,trade_date=latest_trade_from_chart(chart)
                except Exception as ce:
                    trade=trade_date=None; warnings.append({'complex_id':cid,'area_id':aid,'kind':'recent_trade_unavailable','error':str(ce)})
                r.update({'complex_id':cid,'area_id':aid,'name':c['user_name'],'recent_trade_manwon':trade,'recent_trade_date':trade_date,'collected_at':now()}); rows.append(r)
                print(json.dumps(r,ensure_ascii=False),flush=True)
            except Exception as e:
                errors.append({'complex_id':cid,'area_id':aid,'error':str(e)}); print(errors[-1],flush=True)
    coverage=round(resolved_targets*100/len(targets),1) if targets else 100.0
    snap={'schema_version':2,'source':'KB public complex page + target mapping','collected_at':now(),'items':rows,'errors':errors,'warnings':warnings,'unresolved_targets':unresolved_targets,'target_count':len(targets),'resolved_target_count':resolved_targets,'target_resolution_pct':coverage,'known_unavailable_targets':known_unavailable_targets}
    atomic_json(ROOT/'data/listing_asks_probe.json',snap)
    # Publish partial-but-audited coverage when network collection succeeded; never
    # silently claim 100% coverage. Previous downstream values are only overwritten
    # by matched rows, so unresolved targets do not become false zeros.
    if a.publish and rows: atomic_json(ROOT/'data/buy_watchlist_listings.json',snap)
    probe_mode=bool(a.complex_id or a.area_id)
    fatal = (not rows) or (coverage < 90 and not probe_mode)
    if unresolved_targets or known_unavailable_targets: print(json.dumps({'unresolved_targets':unresolved_targets,'known_unavailable_targets':known_unavailable_targets},ensure_ascii=False),flush=True)
    return 2 if fatal else 0
if __name__=='__main__': raise SystemExit(main())
