#!/usr/bin/env python3
"""Verify official KB DataHub valuation/statistics source pages in one pass."""
import urllib.request,pathlib,datetime,json
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/kb_valuation_sources.json'
TARGETS={
 'rent_to_sale_ratio':('아파트 전세가율',['https://data.kbland.kr/kbstats/wmh?tIdx=HT04']),
 'avg_median_price':('평균·중위가격',['https://data.kbland.kr/kbstats/wmh?tIdx=HT03']),
 'leading50':('KB선도50',['https://data.kbland.kr/kbstats/wmh?tIdx=HT01'])
}
def main():
 out={}
 for k,(label,urls) in TARGETS.items():
  hit=None
  for u in urls:
   try:
    h=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/'}),timeout=30).read().decode('utf-8','ignore')
    if len(h)>500:hit=u;break
   except Exception:pass
  out[k]={'label':label,'status':'official_source_connected' if hit else 'unavailable','official_url':hit,'value_endpoint_status':'pending'}
 p={'source':'KB부동산 데이터허브','targets':out,'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(p,ensure_ascii=False,indent=2));print(json.dumps(p,ensure_ascii=False))
 if not any(v['status']=='official_source_connected' for v in out.values()):raise SystemExit('no official source page verified')
if __name__=='__main__':main()
