#!/usr/bin/env python3
"""Verify KB DataHub official weekly apartment jeonse-price-index source."""
import urllib.request,pathlib,datetime,json
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/kb_weekly_rent_index.json'
URLS=['https://data.kbland.kr/stats-screen/weekAptRentPriceInxInc','https://data.kbland.kr/kbstats/wmh?tIdx=HT02&tsIdx=weekAptRentPriceInxInc']
def main():
 found=None
 for u in URLS:
  try:
   h=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/'}),timeout=30).read().decode('utf-8','ignore')
   if '전세' in h and ('가격지수' in h or 'weekAptRentPriceInxInc' in h):found=u;break
  except Exception:pass
 if not found:raise SystemExit('official KB weekly rent index page contract not found')
 p={'status':'official_source_connected','source':'KB부동산 데이터허브','series':'주간 아파트 전세가격지수','official_url':found,'frequency':'weekly','page_verified':True,'value_endpoint_status':'pending','collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(p,ensure_ascii=False,indent=2));print(json.dumps(p,ensure_ascii=False))
if __name__=='__main__':main()
