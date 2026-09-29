#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,re,datetime
R=pathlib.Path(__file__).resolve().parents[1]
O=R/'data_sources/kb_pir_module_trace.json'
URL='https://data.kbland.kr/kbstats/wmh?tIdx=HT10&tsIdx=pir'
def get(u):
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'*/*','Referer':'https://data.kbland.kr/'})
 with urllib.request.urlopen(req,timeout=30) as r:return r.read().decode('utf-8','ignore')
def snippets(t,pattern,span=7000):
 out=[]
 for m in re.finditer(pattern,t,re.I):
  a=max(0,m.start()-span);b=min(len(t),m.end()+span)
  out.append(t[a:b])
 return out
def main():
 h=get(URL);scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',h)
 out={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scripts':[]}
 for s in scripts:
  u=urllib.parse.urljoin(URL,s)
  try:t=get(u)
  except:continue
  if 'weekMnthlyHuseTrnd/pir' not in t and 'pir:Ja' not in t and 'aptHuseLnPir' not in t:continue
  hits=[]
  pats=[r'weekMnthlyHuseTrnd/pir',r'pir:Ja',r'Ja=\{namespaced',r'Ja=\{',r'const Ja=',r'var Ja=',r'aptHuseLnPir:Xa',r'Xa=\{namespaced']
  for p in pats:
   ss=snippets(t,p)
   if ss:hits.append({'pattern':p,'snippets':ss[:4]})
  out['scripts'].append({'url':u,'hits':hits})
 O.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({'scripts':len(out['scripts']),'patterns':[(x['url'],[h['pattern'] for h in x['hits']]) for x in out['scripts']]},ensure_ascii=False))
if __name__=='__main__':main()
