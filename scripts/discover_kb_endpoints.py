#!/usr/bin/env python3
import urllib.request,re,json,pathlib,datetime,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/kb_endpoint_discovery.json'
PAGES=['https://data.kbland.kr/stats-screen/weekAptSalePriceInx','https://data.kbland.kr/share/kbstats/wmh?tIdx=HT01&tsIdx=weekAptSalePriceInx']
def fetch(u):
 return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/'}),timeout=30).read().decode('utf-8','ignore')
def main():
 urls=set();contexts=[]
 for p in PAGES:
  h=fetch(p)
  for x in re.findall(r'<script[^>]+src=["\']([^"\']+)',h):
   urls.add(urllib.parse.urljoin(p,x))
 for u in list(urls):
  try:
   t=fetch(u)
   for m in re.finditer(r'[^"\']{0,100}(?:weekMnthlyHuseTrnd|weekAptSalePriceInx|data-api\.kbland\.kr)[^"\']{0,180}',t,re.I):
    contexts.append(m.group(0))
  except Exception:pass
 eps=sorted(set(re.findall(r'/bfmstat/[A-Za-z0-9_/?=&.{}$:-]+','\n'.join(contexts))))
 out={'status':'discovered' if eps else 'no_endpoint_found','scripts':len(urls),'endpoints':eps,'contexts':contexts[:100],'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'scripts':len(urls),'endpoints':eps,'contexts':len(contexts)},ensure_ascii=False))
 if not eps:raise SystemExit('no KB endpoint discovered')
if __name__=='__main__':main()
