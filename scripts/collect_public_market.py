#!/usr/bin/env python3
import json,re,datetime,pathlib,time
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
MASTER=ROOT/'data/buy_watchlist_master.json'
TARGETS=ROOT/'data/buy_watchlist_targets.json'
OUT=ROOT/'data/buy_watchlist_market.json'
DIST=ROOT/'dist/buy_watchlist_market.json'

def money(s):
    s=str(s or '').replace(',','').strip()
    total=0.0
    m=re.search(r'(\d+(?:\.\d+)?)억',s)
    if m:
        total+=float(m.group(1))*10000
        tail=s[m.end():]
        m2=re.search(r'(\d+)\s*만?',tail)
        if m2: total+=float(m2.group(1))
    else:
        m3=re.search(r'(\d+)\s*만',s)
        if m3: total+=float(m3.group(1))
    return round(total) if total else None

def norm(s):
    return re.sub(r'\s+','',str(s or '')).replace('아파트','').replace('(','').replace(')','').replace('마천역','')

def target_for(x,targets):
    n=norm(x.get('user_name') or x.get('kb_name'))
    for t in targets:
        tn=norm(t.get('name'))
        if tn==n or tn in n or n in tn: return t
    return None

def target_types(x,t):
    ts=x.get('types') or []
    if not t or t.get('min_pyeong') is None: return ts
    lo,hi=float(t['min_pyeong']),float(t['max_pyeong'])
    out=[]
    for a in ts:
        m=re.search(r'\d+(?:\.\d+)?',str(a.get('type_label') or ''))
        if m and lo<=float(m.group())<=hi: out.append(a)
    return out

def body(page):
    return page.locator('body').inner_text()

def current_type_text(t):
    m=re.search(r'\b(\d+[A-Za-z]?)평/',t)
    return m.group(1) if m else None

def select_type(page,label):
    wanted=str(label).upper()
    t=body(page)
    if current_type_text(t)==wanted: return
    # Open the currently selected area dropdown (e.g. "24A평/18.12평").
    cur=page.get_by_text(re.compile(r'^\d+[A-Za-z]?평/\d'),exact=False)
    if cur.count()==0: raise RuntimeError('type dropdown not found')
    cur.first.click()
    page.wait_for_timeout(250)
    # Choose the requested supply-area label. Prefer text beginning with "24A평/".
    opt=page.get_by_text(re.compile(r'^'+re.escape(wanted)+r'평(?:/|\s|$)',re.I),exact=False)
    if opt.count()==0:
        opt=page.get_by_text(re.compile(r'^'+re.escape(wanted)+r'평',re.I),exact=False)
    if opt.count()==0: raise RuntimeError(f'type option not found: {wanted}')
    opt.last.click()
    page.wait_for_timeout(700)
    got=current_type_text(body(page))
    if got!=wanted: raise RuntimeError(f'type selection mismatch: wanted={wanted}, got={got}')

def field_money(t,label):
    # Keep the whole price line so "19억 4,500만" is never truncated at the space.
    m=re.search(re.escape(label)+r'[ \t]*([^\n\r]+)',t)
    return money(m.group(1)) if m else None

def parse_selected(page,cid,name,a):
    t=body(page)
    avg=field_money(t,'매물평균가')
    kb=field_money(t,'KB시세 일반가')
    recent=None; date=None
    m=re.search(r'최근 실거래가[ \t]*([^\n\r]+)',t)
    if m:
        recent=money(m.group(1))
        dm=re.search(r'(\d{2}\.\d{2}\.\d{2})',m.group(1))
        if dm: date=dm.group(1)
    cnt=None
    m=re.search(r'매매\s*([\d,]+)\s*전세',t)
    if m: cnt=int(m.group(1).replace(',',''))
    expected=a.get('general_price_manwon')
    if expected is not None and kb is not None and int(expected)!=int(kb):
        raise RuntimeError(f'KB price/type validation failed area={a.get("area_id")} label={a.get("type_label")} expected={expected} got={kb}')
    return {
        'complex_id':cid,'area_id':a.get('area_id'),'type_label':a.get('type_label'),'name':name,
        'sale_listing_count':cnt,'avg_ask_manwon':avg,'recent_trade_manwon':recent,
        'recent_trade_date':date,'kb_general_check_manwon':kb,'market_scope':'target_area_id'
    }

def main():
    d=json.loads(MASTER.read_text())
    targets=json.loads(TARGETS.read_text()).get('items',[])
    old={}
    if OUT.exists():
        try: old={(str(x['complex_id']),str(x.get('area_id'))):x for x in json.loads(OUT.read_text()).get('items',[])}
        except Exception: pass
    items=[]; errors=[]; validated=0
    pw=sync_playwright().start()
    browser=pw.chromium.launch(headless=True)
    page=browser.new_page(locale='ko-KR')
    for x in d['items']:
        cid=x.get('complex_id')
        if not cid: continue
        areas=target_types(x,target_for(x,targets))
        if not areas: continue
        try:
            page.goto(f'https://kbland.kr/se/c/{cid}',wait_until='domcontentloaded',timeout=30000)
            page.wait_for_timeout(1200)
            for a in areas:
                try:
                    select_type(page,a.get('type_label'))
                    v=parse_selected(page,cid,x.get('user_name') or x.get('kb_name'),a)
                    prev=old.get((str(cid),str(a.get('area_id'))),{})
                    if prev and v['avg_ask_manwon'] is not None and prev.get('avg_ask_manwon') is not None:
                        v['avg_ask_week_delta_manwon']=v['avg_ask_manwon']-prev['avg_ask_manwon']
                    if prev and v['sale_listing_count'] is not None and prev.get('sale_listing_count') is not None:
                        v['sale_listing_week_delta']=v['sale_listing_count']-prev['sale_listing_count']
                    if v['kb_general_check_manwon'] is not None: validated+=1
                    items.append(v)
                except Exception as e:
                    errors.append({'complex_id':cid,'area_id':a.get('area_id'),'type_label':a.get('type_label'),'name':x.get('user_name'),'error':str(e)})
            time.sleep(.1)
        except Exception as e:
            errors.append({'complex_id':cid,'name':x.get('user_name'),'error':str(e)})
    browser.close(); pw.stop()
    out={'collected_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
         'source':'KB public complex page / explicitly selected target type','items':items,'errors':errors}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)); DIST.write_text(json.dumps(out,ensure_ascii=False,indent=2))
    stats={'items':len(items),'errors':len(errors),'validated_type_price':validated,
           'with_avg':sum(x['avg_ask_manwon'] is not None for x in items),
           'with_trade':sum(x['recent_trade_manwon'] is not None for x in items)}
    print(json.dumps(stats,ensure_ascii=False))
    # Never publish a superficially successful refresh if type selection is not proven.
    if len(items)<30 or validated<25 or stats['with_avg']<20 or stats['with_trade']<20:
        print(json.dumps(errors[:20],ensure_ascii=False,indent=2))
        raise SystemExit(2)

if __name__=='__main__': main()
