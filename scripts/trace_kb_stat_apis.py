#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,re,datetime
R=pathlib.Path(__file__).resolve().parents[1];O=R/'data_sources/kb_deep_api_trace.json'
URL='https://data.kbland.kr/kbstats/wmh?tIdx=HT10&tsIdx=aptSaleMedianPrice'
def get(u):
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'*/*','Referer':'https://data.kbland.kr/'})
 with urllib.request.urlopen(req,timeout=25) as r:return r.read().decode('utf-8','ignore')
def main():
 h=get(URL); scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',h); out={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'matches':[]}
 needles=['aptSaleMedianPrice','aptRentMedianPrice','apt5PorelaPrice','leadingApt','MedianPrice','Porela']
 for s in scripts:
  try:t=get(urllib.parse.urljoin(URL,s))
  except:continue
  if not any(n.lower() in t.lower() for n in needles):continue
  for n in needles:
   for m in re.finditer(re.escape(n),t,re.I):
    a=max(0,m.start()-2500);b=min(len(t),m.end()+2500);chunk=t[a:b]
    urls=sorted(set(re.findall(r'["\']([^"\']*(?:bfmstat|kbstats|api|price)[^"\']*)["\']',chunk,re.I)))
    out['matches'].append({'script':s,'needle':n,'context':chunk,'nearby_urls':urls[:50]})
 O.write_text(json.dumps(out,ensure_ascii=False,indent=2));print('matches',len(out['matches']))
if __name__=='__main__':main()
