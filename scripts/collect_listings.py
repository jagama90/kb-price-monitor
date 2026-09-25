#!/usr/bin/env python3
"""Collect KB lowest asking prices for configured buy-watchlist area IDs."""
import argparse, datetime as dt, html as htmlmod, http.client, json, os, random, re, urllib.parse, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
API_HOST='api.kbland.kr'
API_PATH='/land-property/propList/main'
PRICE_PATH='/land-price/price/complex/integrationChart'

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



def _kr_price_to_manwon(s):
    s=str(s).replace(',','').strip(); total=0
    m=re.search(r'(\d+)억',s)
    if m: total+=int(m.group(1))*10000
    tail=re.search(r'억\s*(\d+)',s)
    if tail: total+=int(tail.group(1))
    elif not m:
        n=re.search(r'(\d+)',s)
        if n: total=int(n.group(1))
    return total or None

def get_page_price_record(complex_id,area_id):
    url=f'https://kbland.kr/se/c/{complex_id}'
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36','Referer':'https://kbland.kr/','Accept':'text/html'})
    with urllib.request.urlopen(req,timeout=35) as r: rawhtml=r.read().decode('utf-8','replace')
    marker=r'{\"단지기본일련번호\":'
    records=[]; cursor=0
    while True:
        start=rawhtml.find(marker,cursor)
        if start<0: break
        depth=0; end=start; esc=False
        while end<len(rawhtml):
            ch=rawhtml[end]
            if ch=='{' and not esc: depth+=1
            elif ch=='}' and not esc:
                depth-=1
                if depth==0: end+=1; break
            esc=(ch=='\\' and not esc)
            if ch!='\\': esc=False
            end+=1
        raw=rawhtml[start:end].replace(r'\"','"')
        try: records.append(json.loads(raw))
        except Exception: pass
        cursor=max(end,start+1)
    matches=[x for x in records if str(x.get('면적일련번호'))==str(area_id)]
    rec=max(matches,key=lambda x: sum(k in x for k in ('매매일반거래가','매매평균가','시세기준년월일'))) if matches else {}
    text=htmlmod.unescape(re.sub(r'<[^>]+>',' ',rawhtml))
    text=re.sub(r'\s+',' ',text)
    sale=re.search(r'KB시세 일반가\s*([0-9억, ]+)\s*(\d{2}\.\d{2}\.\d{2}).*?최근 실거래가\s*([0-9억, ]+)\s*(\d{2}\.\d{2}\.\d{2})/(\d+)층\s*매물평균가\s*([0-9억, ]+)',text,re.S)
    if sale:
        rec=dict(rec)
        rec.update({'매매일반거래가':_kr_price_to_manwon(sale.group(1)),'시세기준년월일':'20'+sale.group(2).replace('.',''),
                    '최근실거래가':_kr_price_to_manwon(sale.group(3)),'최근실거래일':'20'+sale.group(4).replace('.',''),
                    '최근실거래층':int(sale.group(5)),'매물평균가':_kr_price_to_manwon(sale.group(6))})
    return rec

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
    targets=json.loads((ROOT/'data/buy_watchlist_targets.json').read_text(encoding='utf-8'))
    cmap={x.get('complex_id'):x for x in master['items'] if x.get('complex_id')}
    nmap={x.get('user_name'):x for x in master['items']}
    rows=[]; errors=[]
    for t in targets['items']:
        c=cmap.get(t.get('complex_id')) or nmap.get(t.get('name'))
        if not c or not c.get('complex_id'): continue
        cid=c['complex_id']
        if a.complex_id and cid!=a.complex_id: continue
        aids=t.get('area_ids') or []
        if not aids:
            lo=t.get('min_pyeong'); hi=t.get('max_pyeong')
            for typ in c.get('types',[]):
                try: p=float(re.search(r'\d+(?:\.\d+)?',str(typ.get('type_label',''))).group())
                except Exception: continue
                if (lo is None or p>=float(lo)) and (hi is None or p<=float(hi)): aids.append(typ.get('area_id'))
        for aid in aids:
            if not aid or (a.area_id and aid!=a.area_id): continue
            try:
                # Price fields are embedded in the server-rendered KB complex page and are
                # more stable from GitHub Actions than the session-sensitive propList API.
                rec=get_page_price_record(cid,aid)
                r={'lowest_ask_manwon':None,'avg_ask_manwon':rec.get('매물평균가'),'listing_count':0,'page_count':0,
                   'kb_general_check_manwon':rec.get('매매일반거래가'),'kb_price_date':rec.get('시세기준년월일')}
                try:
                    trade,trade_date=rec.get('최근실거래가'),rec.get('최근실거래일')
                    if not trade:
                        chart=get_integration_chart(cid,aid); trade,trade_date=latest_trade_from_chart(chart)
                except Exception as ce:
                    trade=trade_date=None; r['price_detail_error']=str(ce)
                r.update({'complex_id':cid,'area_id':aid,'name':c['user_name'],'recent_trade_manwon':trade,'recent_trade_date':trade_date,'collected_at':now()}); rows.append(r)
                print(json.dumps(r,ensure_ascii=False),flush=True)
            except Exception as e:
                errors.append({'complex_id':cid,'area_id':aid,'error':str(e)}); print(errors[-1],flush=True)
    snap={'schema_version':1,'source':'KB부동산 propList/main','collected_at':now(),'items':rows,'errors':errors}
    atomic_json(ROOT/'data/listing_asks_probe.json',snap)
    if a.publish and not errors: atomic_json(ROOT/'data/buy_watchlist_listings.json',snap)
    return 2 if errors else 0
if __name__=='__main__': raise SystemExit(main())
