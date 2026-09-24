#!/usr/bin/env python3
"""Merge independent source adapters into the dashboard contract, retaining last-good values."""
import json,pathlib,datetime
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1];SRC=ROOT/'data_sources';OUT=ROOT/'dist/market_indicators.json'
def read(name):
 p=SRC/name
 return json.loads(p.read_text()) if p.exists() else None
def main():
 d=json.loads(OUT.read_text()) if OUT.exists() else {}
 m=read('molit.json')
 if m:
  for k in ('seoul_apt_trade_count','price_bands','matched_period'):d[k]=m[k]
  d.setdefault('data_status',{})['molit']='connected'
 r=read('ecos_mortgage_rate.json')
 if r and r.get('latest'):
  d['mortgage_rate_official']=r['latest'];d.setdefault('data_status',{})['ecos_mortgage_rate']='connected'
 e=read('ecos_m2.json')
 if e and e.get('series'):
  x=e['series'][-1];d['m2_official']={'period':x['period'],'mom_pct':x['mom_pct'],'yoy_pct':x['yoy_pct'],'source':'한국은행 ECOS 101Y003','definition':e.get('definition'),'selected_item':e.get('selected_item')}
  d.setdefault('data_status',{})['m2']='connected'
 v=read('kb_value_score.json')
 if not v or v.get('score_0_100') is None:
  p=ROOT/'dist/kb_value_score.json'; v=json.loads(p.read_text()) if p.exists() else v
 if v and v.get('score_0_100') is not None:
  d['kb_value']=v;d.setdefault('data_status',{})['kb_value']='connected'
 s=read('kb_sentiment_score.json')
 if s and s.get('score_0_100') is not None:
  d['kb_sentiment']=s;d.setdefault('data_status',{})['kb_sentiment']='connected'
  if s.get('jeonse_score_0_100') is not None: d.setdefault('data_status',{})['kb_jeonse_supply']='connected'
 sale=read('kb_weekly_sale_index.json');rent=read('kb_weekly_rent_index.json')
 if sale and sale.get('status')=='connected':
  d['kb_weekly_sale_index']=sale;d.setdefault('data_status',{})['kb_weekly_sale_index']='connected';d.setdefault('data_status',{})['kb_history']='connected'
 if rent and rent.get('status')=='connected':
  d['kb_weekly_rent_index']=rent;d.setdefault('data_status',{})['kb_weekly_rent_index']='connected'
 kb=read('kb_history_status.json')
 if kb and not sale:d.setdefault('data_status',{})['kb_history']=kb.get('status')
 d['updated_at']=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat();OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2))
 if e:(ROOT/'dist/m2_history.json').write_text(json.dumps(e,ensure_ascii=False,indent=2))
 if kb:(ROOT/'dist/kb_history_status.json').write_text(json.dumps(kb,ensure_ascii=False,indent=2))
 print(json.dumps({'built':str(OUT),'sources':{'molit':bool(m),'ecos_m2':bool(e),'kb_history':bool(kb)}},ensure_ascii=False))
if __name__=='__main__':main()
