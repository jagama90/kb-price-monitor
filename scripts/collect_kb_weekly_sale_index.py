#!/usr/bin/env python3
"""Collect KB official weekly apartment sale-price-index page as a verified official source.
The official stats page is stable even while its internal JSON endpoint is being reverse-engineered.
"""
import urllib.request,pathlib,datetime,json,re
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'data_sources/kb_weekly_sale_index.json'
URL='https://data.kbland.kr/stats-screen/weekAptSalePriceInx'
def main():
 req=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/'})
 html=urllib.request.urlopen(req,timeout=30).read().decode('utf-8','ignore')
 ok=('주간 아파트 매매가격지수' in html and ('가격지수' in html or 'weekAptSalePriceInx' in html))
 if not ok:raise SystemExit('official KB weekly sale index page contract not found')
 base=re.search(r'기준[^<]{0,80}',html)
 p={'status':'official_source_connected','source':'KB부동산 데이터허브','series':'주간 아파트 매매가격지수','official_url':URL,'definition':'기준시점 대비 조사 시점 가격 비율(주택별·지역별 가중)','frequency':'weekly','page_verified':True,'base_text':base.group(0) if base else None,'value_endpoint_status':'pending','collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(p,ensure_ascii=False,indent=2));print(json.dumps(p,ensure_ascii=False))
if __name__=='__main__':main()
