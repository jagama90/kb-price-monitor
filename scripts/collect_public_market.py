#!/usr/bin/env python3
import json,re,datetime,pathlib,time,argparse
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
MASTER=ROOT/'data/buy_watchlist_master.json'
TARGETS=ROOT/'data/buy_watchlist_targets.json'
OUT=ROOT/'data/buy_watchlist_market.json'
DIST=ROOT/'dist/buy_watchlist_market.json'

def money(s):
    raw=str(s or '').strip()
    s=raw.replace(',','')
    total=0.0
    m=re.search(r'(\d+(?:\.\d+)?)억',s)
    if m:
        total+=float(m.group(1))*10000
        tail=s[m.end():].strip()
        # KB now renders e.g. "18억 9,500" without the trailing "만".
        m2=re.match(r'(\d{1,4})(?:\s*만)?(?:\s|$)',tail)
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
    if not t:return ts
    aids={int(z) for z in (t.get('area_ids') or []) if z}
    if aids:return [a for a in ts if int(a.get('area_id') or 0) in aids]
    if t.get('min_pyeong') is None:return ts
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

def select_type(page,label,area=None):
    # KB changed its visible type control in Sep-2026 from a plain "24평" label
    # to a combined button such as "81m² / 59.92m²", with a separate 평 toggle.
    # Match both presentations so collection is resilient to the display unit.
    m=re.search(r'\d+(?:\.\d+)?',str(label or ''))
    if not m: raise RuntimeError(f'invalid type label: {label}')
    pyeong=m.group(0)
    wanted=pyeong+'평'
    page.wait_for_timeout(250)

    def click_visible(locator):
        for i in range(locator.count()-1,-1,-1):
            try:
                el=locator.nth(i)
                if el.is_visible():
                    el.click(force=True,timeout=3000)
                    return True
            except Exception:
                pass
        return False

    # Legacy exact text.
    if click_visible(page.get_by_text(wanted,exact=True)):
        page.wait_for_timeout(900); return

    # Current UI exposes a separate unit toggle. Switch to 평 and accept
    # combined labels such as "24평 / 18평".
    try:
        toggle=page.get_by_role('button',name='평',exact=True)
        if click_visible(toggle): page.wait_for_timeout(350)
    except Exception:
        pass
    pat=re.compile(r'^\s*'+re.escape(pyeong)+r'(?:[A-Za-z])?(?:\.0+)?평')
    if click_visible(page.get_by_role('button',name=pat)):
        page.wait_for_timeout(900); return

    # Metric-mode fallback: the same current control can remain as
    # "81m² / 59.92m²". Match the target supply area from the master snapshot.
    supply=(area or {}).get('supply_m2')
    if supply:
        n=int(round(float(supply)))
        mpat=re.compile(r'^\s*'+str(n)+r'(?:\.\d+)?m²',re.I)
        if click_visible(page.get_by_role('button',name=mpat)):
            page.wait_for_timeout(900); return

    raise RuntimeError(f'visible type tab not found: {wanted} / supply={supply}')



def field_money(t,label):
    # Current KB DOM renders labels and values on separate lines.
    lines=[x.strip() for x in str(t or '').splitlines()]
    for i,line in enumerate(lines):
        if line==label:
            for j in range(i+1,min(i+4,len(lines))):
                v=money(lines[j])
                if v is not None:return v
    # Legacy same-line fallback.
    m=re.search(re.escape(label)+r'[ \t]*([^\n\r]+)',str(t or ''))
    return money(m.group(1)) if m else None

def field_text_after(t,label,limit=4):
    lines=[x.strip() for x in str(t or '').splitlines()]
    for i,line in enumerate(lines):
        if line==label:
            return lines[i+1:min(i+1+limit,len(lines))]
    return []

def parse_selected(page,cid,name,a):
    t=body(page)
    avg=field_money(t,'매물평균가')
    kb=field_money(t,'KB시세 일반가')
    recent=None; date=None
    nxt=field_text_after(t,'최근 실거래가',3)
    if nxt:
        recent=money(nxt[0])
        for q in nxt[1:]:
            dm=re.search(r'(\d{2}\.\d{2}\.\d{2})',q)
            if dm:
                date=dm.group(1);break

    # The page contains both complex-wide counts and selected-type counts.
    # Use the last 매매→전세 count pair, which is the selected type detail block.
    cnt=None
    pairs=re.findall(r'매매\s*([\d,]+)\s*전세',t,re.S)
    if pairs:
        try:cnt=int(pairs[-1].replace(',',''))
        except Exception:pass

    expected=a.get('general_price_manwon')
    if expected is not None and kb is not None and int(expected)!=int(kb):
        raise RuntimeError(f'KB price/type validation failed area={a.get("area_id")} label={a.get("type_label")} expected={expected} got={kb}')
    return {'complex_id':cid,'area_id':a.get('area_id'),'type_label':a.get('type_label'),'name':name,'sale_listing_count':cnt,'avg_ask_manwon':avg,'recent_trade_manwon':recent,'recent_trade_date':date,'kb_general_check_manwon':kb,'market_scope':'target_area_id'}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--sample',action='store_true'); args=ap.parse_args()
    d=json.loads(MASTER.read_text()); targets=json.loads(TARGETS.read_text()).get('items',[])
    old={}
    if OUT.exists():
        try: old={(str(x['complex_id']),str(x.get('area_id'))):x for x in json.loads(OUT.read_text()).get('items',[])}
        except Exception: pass
    items=[]; errors=[]; validated=0
    sample_pairs={(1960,1847),(1947,1835)}
    pw=sync_playwright().start(); browser=pw.chromium.launch(headless=True); page=browser.new_page(locale='ko-KR'); page.set_default_timeout(5000)
    for x in d['items']:
        cid=x.get('complex_id')
        if not cid: continue
        if args.sample:
            areas=[z for z in (x.get('types') or []) if (int(cid),int(z.get('area_id') or 0)) in sample_pairs]
            if not areas: continue
        else:
            areas=target_types(x,target_for(x,targets))
            # Use the exact same representative-area rule as the live watchlist
            # and monthly history: largest household count within the user's target group.
            # This prevents ask/listing fields from being merged onto a different type.
            if areas:
                areas=[max(areas,key=lambda z:(int(z.get('type_households') or 0),-int(z.get('area_id') or 0)))]
        try:
            page.goto(f'https://kbland.kr/se/c/{cid}',wait_until='domcontentloaded',timeout=20000); page.wait_for_timeout(1200)
            for z in areas:
                try:
                    select_type(page,z.get('type_label'),z); v=parse_selected(page,cid,x.get('user_name') or x.get('kb_name'),z)
                    prev=old.get((str(cid),str(z.get('area_id'))),{})
                    if prev and v['avg_ask_manwon'] is not None and prev.get('avg_ask_manwon') is not None: v['avg_ask_week_delta_manwon']=v['avg_ask_manwon']-prev['avg_ask_manwon']
                    if prev and v['sale_listing_count'] is not None and prev.get('sale_listing_count') is not None: v['sale_listing_week_delta']=v['sale_listing_count']-prev['sale_listing_count']
                    if v['kb_general_check_manwon'] is not None: validated+=1
                    items.append(v)
                except Exception as e: errors.append({'complex_id':cid,'area_id':z.get('area_id'),'type_label':z.get('type_label'),'name':x.get('user_name'),'error':str(e)})
        except Exception as e: errors.append({'complex_id':cid,'name':x.get('user_name'),'error':str(e)})
    browser.close(); pw.stop()
    stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
    out={'collected_at':stamp,'listing_collected_at':stamp,'source':'KB public complex page / explicitly selected target type','items':items,'errors':errors}
    stats={'items':len(items),'errors':len(errors),'validated_type_price':validated,'with_avg':sum(x['avg_ask_manwon'] is not None for x in items),'with_trade':sum(x['recent_trade_manwon'] is not None for x in items)}
    print(json.dumps(stats,ensure_ascii=False))
    if args.sample:
        p=ROOT/'data/market_sample_validation.json'; p.write_text(json.dumps(out,ensure_ascii=False,indent=2))
        expected=set(sample_pairs)
        got={(int(x['complex_id']),int(x['area_id'])):x for x in items}; bad=[]
        for key in expected:
            x=got.get(key)
            if not x: bad.append(f'missing {key}'); continue
            # Dynamic contract only: parse_selected already verifies the live KB
            # general price against the current master row. Asking price and trade
            # values are market data and must never be hard-coded in a sample test.
            if x.get('kb_general_check_manwon') is None:
                bad.append(f'{key} live KB general price unavailable')
        print(json.dumps({'sample_values':items,'sample_errors':errors},ensure_ascii=False))
        fatal=[e for e in errors if 'mismatch' in str(e.get('error') or '').lower()]
        if fatal:
            out['validation_status']='failed_integrity'
            out['validation_details']=fatal
            p.write_text(json.dumps(out,ensure_ascii=False,indent=2))
            print(json.dumps({'sample_validation':'FAIL_INTEGRITY','details':fatal},ensure_ascii=False)); raise SystemExit(2)
        if bad:
            out['validation_status']='degraded_source'
            out['validation_details']=bad
            p.write_text(json.dumps(out,ensure_ascii=False,indent=2))
            print(json.dumps({'sample_validation':'DEGRADED_SOURCE','details':bad},ensure_ascii=False)); return
        out['validation_status']='pass'
        p.write_text(json.dumps(out,ensure_ascii=False,indent=2))
        print(json.dumps({'sample_validation':'PASS'},ensure_ascii=False)); return
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)); DIST.write_text(json.dumps(out,ensure_ascii=False,indent=2))
    if len(items)<30 or validated<25 or stats['with_avg']<20 or stats['with_trade']<20:
        print(json.dumps(errors[:20],ensure_ascii=False,indent=2)); raise SystemExit(2)

if __name__=='__main__': main()
