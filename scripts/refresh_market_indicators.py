#!/usr/bin/env python3
import json, pathlib, datetime
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/market_indicators.json'
# Verified baseline. This exporter is intentionally conservative: only published values are emitted.
# Upcoming BOK releases are not guessed; the scheduled workflow republishes after source adapters update.
data={
 "updated_at":datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat(),
 "sources":[
  {"name":"서울특별시/국토교통부 실거래가","url":"https://www.seoul.go.kr/news/news_report.do?nttNo=466727"},
  {"name":"한국은행 통계공표일정","url":"https://www.bok.or.kr/portal/stats/statsPublictSchdul/listCldr.do?menuNo=200775"}
 ],
 "seoul_apt_trade_count":[["2026-03",5515,False],["2026-04",8661,False],["2026-05",8972,False],["2026-06",5303,False],["2026-07",5838,False],["2026-08",3143,True]],
 "under15_share":[["2026-05",72.4,False],["2026-08",79.9,True]],
 "m2":{"period":"2026-07","mom_pct":0.3,"yoy_pct":5.8,"household_nonprofit_change_trillion_krw":-11.6},
 "release_calendar":{"mortgage_rate_next":"2026-09-30","m2_next":"2026-10-15"},
 "price_bands":{"status":"awaiting_raw_trade_adapter","bands":["<=9eok","9-15eok","15-25eok","25eok+"]}
}
OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({"market_indicators":str(OUT),"updated_at":data["updated_at"]},ensure_ascii=False))
