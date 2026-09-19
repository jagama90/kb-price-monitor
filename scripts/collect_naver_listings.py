#!/usr/bin/env python3
import argparse,json,re,subprocess,sys,time,urllib.parse,urllib.request
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
UA='Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 Chrome/153 Mobile Safari/537.36'
def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def norm(s): return re.sub(r'[^0-9a-z가-힣]','',str(s or '').lower())
def get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Referer':'https://m.land.naver.com/','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=25) as r:return json.loads(r.read())
def find_complex(name):
    data=get_json('https://m.land.naver.com/search/result/'+urllib.parse.quote(name))
    found=[]
    def walk(x):
        if isinstance(x,dict):
            if x.get('hscpNo') and x.get('hscpNm'):found.append(x)
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    walk(data)
    key=norm(name); scored=[]
    for x in found:
        n=norm(x.get('hscpNm')); score=100 if n==key else 80 if key and (key in n or n in key) else 0
        if score:scored.append((score,x))
    return max(scored,key=lambda z:z[0])[1] if scored else None
def start_browser():
    p=subprocess.Popen(['node','scripts/naver-browser-fetch.js'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=sys.stderr,text=True,bufsize=1)
    ready=json.loads(p.stdout.readline())
    if not ready.get('ready'):raise RuntimeError(ready.get('error') or 'browser failed')
    return p
def fetch_pages(p,no,max_pages):
    p.stdin.write(json.dumps({'id':1,'complexNo':str(no),'maxPages':max_pages})+'\n');p.stdin.flush()
    r=json.loads(p.stdout.readline())
    if r.get('error'):raise RuntimeError(r['error'])
    return r.get('pages') or []
def number(v):
    if isinstance(v,(int,float)):return float(v)
    m=re.search(r'[0-9,.]+',str(v or ''));return float(m.group(0).replace(',','')) if m else 0.0
def rows_from_pages(pages):
    out=[]
    for body in pages:
        result=(json.loads(body).get('result') or {})
        arr=result.get('list') or result.get('articleList') or []
        for item in arr:
            rep=item.get('representativeArticleInfo') if isinstance(item,dict) else None
            if isinstance(rep,dict):
                out.append(rep)
                out.extend([x for x in ((item.get('duplicatedArticleInfo') or {}).get('articleInfoList') or []) if isinstance(x,dict)])
            elif isinstance(item,dict):out.append(item)
    rows=[]
    for a in out:
        p=number((a.get('priceInfo') or {}).get('dealPrice'));sp=a.get('spaceInfo') or a.get('sizeInfo') or {}
        supply=number(sp.get('supplySpace'));exclusive=number(sp.get('exclusiveSpace'))
        if p<=0 or (supply<=0 and exclusive<=0):continue
        rows.append({'article_no':str(a.get('articleNumber') or ''),'price_manwon':int(round(p/10000)) if p>1000000 else int(round(p)),
                     'supply_m2':round(supply,2),'exclusive_m2':round(exclusive,2),
                     'url':'https://fin.land.naver.com/articles/'+str(a.get('articleNumber') or '')})
    return rows
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--complex-id',type=int);ap.add_argument('--max-pages',type=int,default=4);ap.add_argument('--publish',action='store_true')
    a=ap.parse_args()
    master=json.loads((ROOT/'data/buy_watchlist_master.json').read_text(encoding='utf-8'))
    targets=json.loads((ROOT/'data/buy_watchlist_targets.json').read_text(encoding='utf-8'))
    target_ids={x.get('complex_id') for x in targets.get('items',[])}
    complexes=[x for x in master.get('items',[]) if x.get('complex_id') and (a.complex_id==x.get('complex_id') if a.complex_id else x.get('complex_id') in target_ids)]
    proc=start_browser();items=[];errors=[]
    try:
      for c in complexes:
        try:
          n=find_complex(c.get('user_name') or c.get('kb_name'))
          if not n:raise RuntimeError('Naver complex match not found')
          arts=rows_from_pages(fetch_pages(proc,n['hscpNo'],a.max_pages))
          types=[]
          for t in c.get('types',[]):
            target=float(t.get('supply_m2') or 0)
            near=[x for x in arts if target and abs(x['supply_m2']-target)<=1.2]
            low=min(near,key=lambda x:x['price_manwon']) if near else None
            types.append({'kb_area_id':t.get('area_id'),'type_label':t.get('type_label'),'supply_m2':t.get('supply_m2'),
                          'exclusive_m2':t.get('exclusive_m2'),'lowest_ask_manwon':low['price_manwon'] if low else None,
                          'listing_count':len(near),'lowest_listing':low})
          row={'complex_id':c['complex_id'],'name':c.get('user_name'),'naver_complex_no':str(n['hscpNo']),'naver_name':n.get('hscpNm'),'types':types,'article_count':len(arts)}
          items.append(row);print(json.dumps(row,ensure_ascii=False),flush=True);time.sleep(1)
        except Exception as e:
          errors.append({'complex_id':c.get('complex_id'),'name':c.get('user_name'),'error':str(e)});print(errors[-1],flush=True)
    finally:
      try:proc.stdin.close();proc.wait(timeout=15)
      except Exception:proc.kill()
    snap={'schema_version':1,'source':'Naver fin.land via apt-price-tracker browser pattern','collected_at':now(),'items':items,'errors':errors}
    (ROOT/'data/naver_listing_asks_probe.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8')
    if a.publish and not errors:(ROOT/'data/buy_watchlist_listings.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8')
    return 2 if errors else 0
if __name__=='__main__':raise SystemExit(main())
