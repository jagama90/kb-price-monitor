#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,re,datetime
R=pathlib.Path(__file__).resolve().parents[1]; O=R/'data_sources/kb_median_leading_probe.json'
PAGES={'sale_median':'https://data.kbland.kr/kbstats/wmh?tIdx=HT10&tsIdx=aptSaleMedianPrice','rent_median':'https://data.kbland.kr/kbstats/wmh?tIdx=HT10&tsIdx=aptRentMedianPrice','leading50':'https://data.kbland.kr/kbstats/wmh?tIdx=HT01&tsIdx=leadingApt50PriceInx'}
def get(u):
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'*/*','Referer':'https://data.kbland.kr/'})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read().decode('utf-8','ignore')
def main():
 out={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pages':{}}
 for k,u in PAGES.items():
  try:
   h=get(u); scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',h)
   hits=[]
   for s in scripts:
    try:t=get(urllib.parse.urljoin(u,s))
    except:continue
    for m in re.finditer(r'[^"\']{0,120}(?:aptSaleMedianPrice|aptRentMedianPrice|leadingApt50|선도아파트)[^"\']{0,180}',t,re.I):
     v=m.group(0)
     if v not in hits:hits.append(v)
   out['pages'][k]={'url':u,'script_count':len(scripts),'hits':hits[:100]}
  except Exception as e:out['pages'][k]={'url':u,'error':str(e)}
 O.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({k:len(v.get('hits',[])) for k,v in out['pages'].items()}))
if __name__=='__main__':main()
