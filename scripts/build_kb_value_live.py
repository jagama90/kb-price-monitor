#!/usr/bin/env python3
import json,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]; S=R/'dist/garak_geumho_24a_history.json'; O=R/'dist/kb_value_score.json'
d=json.loads(S.read_text()); rows=[x for x in d.get('series',[]) if x.get('ym') and x.get('sale')]
# Fail closed unless 52+ actual monthly observations. Value = current price position in trailing 36m range.
# Higher price position => lower buying-condition score. Capped to avoid price decline alone dominating the model.
if len(rows)<52:
 out={'status':'insufficient_history','score_0_100':None,'observations':len(rows)}
else:
 w=rows[-36:]; vals=[float(x['sale']) for x in w]; cur=vals[-1]; lo=min(vals); hi=max(vals)
 pos=(cur-lo)/(hi-lo) if hi>lo else .5
 score=max(25,min(75,75-50*pos))
 out={'status':'connected','score_0_100':round(score,1),'method':'trailing_36m_price_position_inverse_capped_25_75','observations':len(rows),'window_months':36,'current_manwon':cur,'window_low_manwon':lo,'window_high_manwon':hi,'current_position_0_1':round(pos,4),'source':'KB부동산 가락금호 24A 월별 일반거래가','period':rows[-1]['ym'],'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
O.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
