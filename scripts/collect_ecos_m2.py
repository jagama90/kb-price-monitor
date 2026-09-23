#!/usr/bin/env python3
import os,json,urllib.request,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'dist/m2_history.json'
def main():
 key=os.getenv('BOK_ECOS_KEY')
 if not key: raise SystemExit('BOK_ECOS_KEY secret is required')
 # ECOS 101Y003: monetary aggregates; query broad M2 candidates and retain official monthly rows.
 url=f'https://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/10000/101Y003/M/201601/202612/'
 obj=json.load(urllib.request.urlopen(url,timeout=30));rows=obj.get('StatisticSearch',{}).get('row',[])
 out={'source':'한국은행 ECOS','table':'101Y003','rows':rows}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
