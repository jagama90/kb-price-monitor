#!/usr/bin/env python3
import json,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]; S=R/'dist/garak_geumho_24a_history.json'; O=R/'dist/kb_price_backtest_target.json'
d=json.loads(S.read_text()); rows=[x for x in d.get('series',[]) if x.get('ym') and x.get('sale')]
out={'status':'connected' if len(rows)>=52 else 'insufficient_history','source':'KB부동산 가락금호 24A 월별 일반거래가','observations':len(rows),'start':rows[0]['ym'] if rows else None,'end':rows[-1]['ym'] if rows else None,'horizons_months':[1,3,6,12],'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
O.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
