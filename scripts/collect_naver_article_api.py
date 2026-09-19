#!/usr/bin/env python3
import argparse,asyncio,json,re,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
UA='Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 Chrome/153 Mobile Safari/537.36'

def resolve_complex(name):
    url='https://m.land.naver.com/search/result/'+urllib.parse.quote(str(name))
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Referer':'https://m.land.naver.com/','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=20) as r:data=json.loads(r.read())
    found=[]
    def walk(x):
      if isinstance(x,dict):
        if x.get('hscpNo') and x.get('hscpNm'):found.append(x)
        for v in x.values():walk(v)
      elif isinstance(x,list):
        for v in x:walk(v)
    walk(data)
    key=re.sub(r'[^0-9a-z가-힣]','',str(name).lower())
    ranked=[]
    for x in found:
      n=re.sub(r'[^0-9a-z가-힣]','',str(x.get('hscpNm','')).lower())
      score=100 if n==key else 80 if key and (key in n or n in key) else 0
      if score:ranked.append((score,x))
    return max(ranked,key=lambda z:z[0])[1] if ranked else None

def price_to_manwon(v):
    s=str(v or '').replace(',','').strip()
    if not s:return 0
    if '억' in s:
        a,b=s.split('억',1)
        return int(float(a or 0)*10000 + float(re.sub(r'[^0-9.]','',b) or 0))
    try:return int(float(s))
    except:return 0

def f(v):
    try:return float(v)
    except:return 0.0

def api_url(cid,page):
    q={'realEstateType':'APT:ABYG:JGC','tradeType':'A1','tag':'::::::::','rentPriceMin':'0','rentPriceMax':'900000000',
       'priceMin':'0','priceMax':'900000000','areaMin':'0','areaMax':'900000000','oldBuildYears':'','recentlyBuildYears':'',
       'minHouseHoldCount':'','maxHouseHoldCount':'','showArticle':'false','sameAddressGroup':'false','minMaintenanceCost':'',
       'maxMaintenanceCost':'','priceType':'RETAIL','directions':'','page':str(page),'buildingNos':'','areaNos':'','type':'list','order':'rank'}
    return 'https://new.land.naver.com/api/articles/complex/'+str(cid)+'?'+urlencode(q)

async def collect(cid,max_pages=50):
    async with async_playwright() as pw:
      browser=await pw.chromium.launch(headless=True,args=['--disable-blink-features=AutomationControlled'])
      ctx=await browser.new_context(locale='ko-KR')
      page=await ctx.new_page(); cap={}; event=asyncio.Event()
      def onreq(req):
        if '/api/articles/complex/'+str(cid) in req.url and not event.is_set():
          cap['url']=req.url;cap['headers']=dict(req.headers);event.set()
      page.on('request',onreq)
      await page.goto('https://new.land.naver.com/complexes/'+str(cid),wait_until='domcontentloaded',timeout=30000)
      try:await asyncio.wait_for(event.wait(),8)
      except:pass
      headers={'accept':'application/json, text/plain, */*','accept-language':'ko-KR,ko;q=0.9','referer':'https://new.land.naver.com/complexes/'+str(cid)}
      auth=(cap.get('headers') or {}).get('authorization')
      if auth:headers['authorization']=auth
      rows=[]
      for n in range(1,max_pages+1):
        url=api_url(cid,n) if n>1 or not cap.get('url') else cap['url']
        r=await ctx.request.get(url,headers=headers,timeout=15000)
        if r.status>=400:raise RuntimeError('article api HTTP '+str(r.status))
        p=await r.json(); arr=p.get('articleList') or p.get('articles') or []
        if not isinstance(arr,list):raise RuntimeError('article list missing')
        rows.extend(arr)
        if not bool(p.get('isMoreData',p.get('moreData',len(arr)>=20))):break
        await asyncio.sleep(.25)
      await browser.close();return rows,bool(auth)

def normalize(a):
    price=price_to_manwon(a.get('dealOrWarrantPrc') or a.get('price') or a.get('priceText'))
    supply=f(a.get('area1') or a.get('spc1') or a.get('supplyArea') or a.get('articleArea'))
    exclusive=f(a.get('area2') or a.get('spc2') or a.get('exclusiveArea'))
    return {'article_no':str(a.get('articleNo') or a.get('atclNo') or ''),'price_manwon':price,'supply_m2':supply,'exclusive_m2':exclusive,
      'building':a.get('buildingName') or a.get('bildNm'),'floor':a.get('floorInfo') or a.get('floor'),'confirm_ymd':a.get('articleConfirmYmd') or a.get('atclCfmYmd')}

async def main():
    ap=argparse.ArgumentParser();ap.add_argument('--naver-complex-no');ap.add_argument('--kb-complex-id',type=int,default=1947);ap.add_argument('--publish',action='store_true')
    a=ap.parse_args()
    master=json.loads((ROOT/'data/buy_watchlist_master.json').read_text())
    c=next(x for x in master['items'] if x.get('complex_id')==a.kb_complex_id)
    targets=json.loads((ROOT/'data/buy_watchlist_targets.json').read_text())
    target=next(x for x in targets['items'] if x.get('complex_id')==a.kb_complex_id)
    wanted=set(target.get('area_ids') or [])
    types=[x for x in c.get('types',[]) if not wanted or x.get('area_id') in wanted]
    resolved=None
    if a.naver_complex_no:
      naver_complex_no=str(a.naver_complex_no)
    else:
      resolved=resolve_complex(c['user_name'])
      if not resolved:
        raise RuntimeError('Naver complex resolve failed: '+str(c['user_name']))
      naver_complex_no=str(resolved['hscpNo'])
    raw,auth=await collect(naver_complex_no); arts=[normalize(x) for x in raw]
    outtypes=[]
    for t in types:
      near=[x for x in arts if x['price_manwon'] and abs(x['supply_m2']-float(t['supply_m2']))<=1.2]
      low=min(near,key=lambda x:x['price_manwon']) if near else None
      outtypes.append({'kb_area_id':t['area_id'],'type_label':t['type_label'],'supply_m2':t['supply_m2'],'exclusive_m2':t['exclusive_m2'],
        'lowest_ask_manwon':low['price_manwon'] if low else None,'listing_count':len(near),'lowest_listing':low})
    snap={'schema_version':2,'source':'Naver new.land Article API auth-capture','collected_at':datetime.now(timezone.utc).isoformat(),
      'items':[{'complex_id':c['complex_id'],'name':c['user_name'],'naver_complex_no':naver_complex_no,'naver_name':(resolved or {}).get('hscpNm'),'authorization_captured':auth,'article_count':len(arts),'types':outtypes}],'errors':[]}
    path=ROOT/'data/naver_listing_asks_probe.json';path.write_text(json.dumps(snap,ensure_ascii=False,indent=2))
    if a.publish:(ROOT/'data/buy_watchlist_listings.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2))
    print(json.dumps(snap,ensure_ascii=False,indent=2))
if __name__=='__main__':asyncio.run(main())
