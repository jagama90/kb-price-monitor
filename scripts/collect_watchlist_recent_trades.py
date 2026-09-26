#!/usr/bin/env python3
"""Collect exact recent MOLIT apartment trades for configured watchlist area IDs."""
import os,json,re,datetime,time,random,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor,as_completed
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data_sources/watchlist_recent_trades.json'
API='https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev'
DIST={
'종로구':'11110','중구':'11140','용산구':'11170','성동구':'11200','광진구':'11215','동대문구':'11230','중랑구':'11260','성북구':'11290',
'강북구':'11305','도봉구':'11320','노원구':'11350','은평구':'11380','서대문구':'11410','마포구':'11440','양천구':'11470','강서구':'11500',
'구로구':'11530','금천구':'11545','영등포구':'11560','동작구':'11590','관악구':'11620','서초구':'11650','강남구':'11680','송파구':'11710','강동구':'11740'}

def norm(s):
    s=re.sub(r'[^0-9A-Za-z가-힣]','',str(s or '')).lower()
    for z in ('아파트','주공','주택'): # preserve most identity; only generic suffix cleanup below
        if s.endswith(z): s=s[:-len(z)]
    return s
def val(it,*names):
    for n in names:
        x=it.findtext(n)
        if x is not None and str(x).strip(): return str(x).strip()
    return ''
def month_shift(d,delta):
    q=d.year*12+d.month-1+delta
    return f'{q//12:04d}{q%12+1:02d}'
def fetch(code,ym,key):
    rows=[];page=1;fetched=0
    while True:
        q=urllib.parse.urlencode({'serviceKey':key,'LAWD_CD':code,'DEAL_YMD':ym,'numOfRows':1000,'pageNo':page},safe='%')
        last=None
        for attempt in range(4):
            try:
                req=urllib.request.Request(API+'?'+q,headers={'User-Agent':'kb-price-monitor/1.0'})
                root=ET.fromstring(urllib.request.urlopen(req,timeout=60).read());break
            except Exception as e:
                last=e
                if attempt==3: raise
                time.sleep(min(12,2**attempt+random.random()))
        items=root.findall('.//item');fetched+=len(items)
        for it in items:
            amt=val(it,'dealAmount','거래금액').replace(',','').strip()
            area=val(it,'excluUseAr','전용면적')
            apt=val(it,'aptNm','아파트')
            dong=val(it,'umdNm','법정동')
            cancel=val(it,'cdealDay','해제사유발생일')
            if not amt.isdigit() or not apt or cancel: continue
            try: ar=float(area)
            except: continue
            y=val(it,'dealYear','년') or ym[:4];m=val(it,'dealMonth','월') or ym[4:];day=val(it,'dealDay','일') or '1'
            ds=f'{int(y):04d}{int(m):02d}{int(day):02d}'
            rows.append({'date':ds,'price_manwon':int(amt),'exclusive_m2':ar,'apt_name':apt,'dong':dong})
        total=int(root.findtext('.//totalCount') or len(rows))
        if not items or fetched>=total: break
        page+=1
        if page>50: break
    return rows

ALIASES={
    norm('가락쌍용1차'):{norm('가락(1차)쌍용아파트')},
    norm('송파꿈에그린위례24단지'):{norm('위례24단지(꿈에그린)')},
    norm('금호타운아파트 (마천역)'):{norm('마천동금호타운1')},
}

def similarity(a,b):
    a,b=norm(a),norm(b)
    if not a or not b:return 0
    if a==b:return 1.0
    if a in b or b in a:return .92
    return SequenceMatcher(None,a,b).ratio()

def identity_tokens(s):
    raw=str(s or '')
    return {
      '단지':set(re.findall(r'(\d+)\s*단지',raw)),
      '차':set(re.findall(r'(\d+)\s*차',raw)),
    }

def identity_conflict(a,b):
    ta,tb=identity_tokens(a),identity_tokens(b)
    for k in ('단지','차'):
        if ta[k] and tb[k] and ta[k]!=tb[k]: return True
    return False

def alias_match(a,b):
    a,b=norm(a),norm(b)
    return b in ALIASES.get(a,set()) or a in ALIASES.get(b,set())

def identity_score(a,b):
    if not a or not b or identity_conflict(a,b): return -1.0
    if alias_match(a,b): return 1.0
    return similarity(a,b)

def main():
    key=os.getenv('MOLIT_SERVICE_KEY')
    if not key: raise SystemExit('MOLIT_SERVICE_KEY required')
    master=json.loads((ROOT/'data/buy_watchlist_master.json').read_text(encoding='utf-8')).get('items',[])
    targets=json.loads((ROOT/'data/buy_watchlist_targets.json').read_text(encoding='utf-8')).get('items',[])
    by_name={norm(x.get('user_name')):x for x in master}
    by_kb={norm(x.get('kb_name')):x for x in master if x.get('kb_name')}
    resolved=[]
    for t in targets:
        c=by_name.get(norm(t.get('name'))) or by_kb.get(norm(t.get('name')))
        if not c or not c.get('complex_id') or not DIST.get(c.get('district')): continue
        aids=list(t.get('area_ids') or [])
        if not aids:
            lo,hi=t.get('min_pyeong'),t.get('max_pyeong')
            for typ in c.get('types') or []:
                mm=re.search(r'\d+(?:\.\d+)?',str(typ.get('type_label') or ''))
                if mm and (lo is None or float(mm.group())>=float(lo)) and (hi is None or float(mm.group())<=float(hi)):
                    aids.append(typ.get('area_id'))
        for aid in aids:
            typ=next((z for z in c.get('types') or [] if int(z.get('area_id') or 0)==int(aid or 0)),None)
            if typ and typ.get('exclusive_m2'):
                resolved.append({'complex_id':int(c['complex_id']),'area_id':int(aid),'name':c.get('user_name'),'kb_name':c.get('kb_name'),
                  'district':c.get('district'),'dong':c.get('dong'),'exclusive_m2':float(typ['exclusive_m2']),'type_label':typ.get('type_label')})
    today=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date()
    try: prior=json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    except Exception: prior={}
    prior_items={(int(x['complex_id']),int(x['area_id'])):x for x in prior.get('items') or [] if x.get('complex_id') and x.get('area_id')}
    months=[month_shift(today,-i) for i in range(3 if prior_items else 8)]
    districts=sorted({x['district'] for x in resolved})
    raw={d:[] for d in districts}
    fetch_errors=[]; failed_districts=set()
    tasks=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for district in districts:
            for ym in months:
                tasks.append((district,ym,pool.submit(fetch,DIST[district],ym,key)))
        for district,ym,fut in tasks:
            try: raw[district].extend(fut.result())
            except Exception as e:
                failed_districts.add(district)
                fetch_errors.append({'district':district,'ym':ym,'error':str(e)})
                print(json.dumps({'warning':'MOLIT target fetch failed','district':district,'ym':ym,'error':str(e)},ensure_ascii=False),flush=True)
    items=[];unmatched=[]
    for x in resolved:
        candidates=[]; exact_area=[]
        for r in raw.get(x['district'],[]):
            ad=abs(float(r['exclusive_m2'])-x['exclusive_m2'])
            if ad>0.8: continue
            if x.get('dong') and r.get('dong') and norm(x['dong'])!=norm(r['dong']): continue
            sim=max(identity_score(x.get('name'),r['apt_name']),identity_score(x.get('kb_name'),r['apt_name']))
            if ad<=0.05: exact_area.append((sim,-ad,r))
            # Conservative complex identity gate: area/dong alone must never identify
            # a complex, and numbered blocks/phases must agree.
            if sim>=0.80:candidates.append((sim,-ad,r))
        method='name_area'
        if not candidates:
            old=prior_items.get((x['complex_id'],x['area_id']))
            old_name=old.get('molit_apt_name') if old else None
            old_sim=max(identity_score(x.get('name'),old_name),identity_score(x.get('kb_name'),old_name)) if old_name else -1
            if old and old.get('recent_trade_manwon') is not None and old_sim>=0.80:
                items.append({**x,'recent_trade_manwon':old.get('recent_trade_manwon'),'recent_trade_date':old.get('recent_trade_date'),
                  'molit_apt_name':old_name,'matched_exclusive_m2':old.get('matched_exclusive_m2'),
                  'name_similarity':round(old_sim,3),'match_method':'last_good_no_newer_trade',
                  'trade_refresh_status':'fallback_last_good' if x['district'] in failed_districts else 'connected_no_newer_trade',
                  'source':'MOLIT apartment trade OpenAPI'})
                continue
            unmatched.append({'complex_id':x['complex_id'],'area_id':x['area_id'],'name':x['name'],'exclusive_m2':x['exclusive_m2'],
              'candidate_names':sorted({z[2]['apt_name'] for z in exact_area})[:8]});continue
        candidates.sort(key=lambda z:(z[2]['date'],z[0],z[1]),reverse=True)
        sim,_,r=candidates[0]
        items.append({**x,'recent_trade_manwon':r['price_manwon'],'recent_trade_date':r['date'],'molit_apt_name':r['apt_name'],
          'matched_exclusive_m2':r['exclusive_m2'],'name_similarity':round(sim,3),'match_method':method,
          'trade_refresh_status':'partial_source' if x['district'] in failed_districts else 'connected',
          'source':'MOLIT apartment trade OpenAPI'})
    out={'status':'partial' if fetch_errors else 'connected','source':'MOLIT apartment trade OpenAPI','months':months,'items':items,'unmatched':unmatched,
      'fetch_errors':fetch_errors,'matched_count':len(items),'target_area_count':len(resolved),'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'matched':len(items),'target_areas':len(resolved),'unmatched':len(unmatched)},ensure_ascii=False))
if __name__=='__main__':main()
