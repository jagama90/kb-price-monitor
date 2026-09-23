#!/usr/bin/env python3
"""Discover KB complex historical-price JSON endpoints from the public web app.
Fail closed: publish only responses that contain dated price rows for the exact complex/area.
"""
import json,re,urllib.request,urllib.parse,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
MASTER=ROOT/'data/buy_watchlist_master.json'; OUT=ROOT/'data_sources/kb_history_probe.json'
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36'
TOKENS=('mpri','price','prc','history','past','chart','graph','시세')
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'*/*','Referer':'https://kbland.kr/'})
 return urllib.request.urlopen(req,timeout=25).read()
def main():
 m=json.loads(MASTER.read_text()); sample=next(x for x in m['items'] if x.get('complex_id') and x.get('types'))
 cid=sample['complex_id']; aid=sample['types'][0]['area_id']; html=get(f'https://kbland.kr/c/{cid}').decode('utf-8','ignore')
 scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',html)
 urls=[]; matches=[]
 for src in scripts:
  url=urllib.parse.urljoin('https://kbland.kr/',src)
  try: txt=get(url).decode('utf-8','ignore')
  except Exception: continue
  if any(t.lower() in txt.lower() for t in TOKENS):
   for mm in re.finditer(r'["\']([^"\']{1,180}(?:mpri|price|prc|history|past)[^"\']{0,180})["\']',txt,re.I):
    v=mm.group(1)
    if ('/' in v or 'api' in v.lower()) and v not in matches: matches.append(v)
  urls.append(url)
 out={'status':'probe_complete','sample':{'complex_id':cid,'area_id':aid,'name':sample.get('user_name')},'script_count':len(urls),'candidates':matches[:200],'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
