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
  for k in ('seoul_apt_trade_count','price_bands','matched_period','signal_matched_period','signal_matched_period_status'):
   if k in m:d[k]=m[k]
  d.setdefault('data_status',{})['molit']='connected'
 r=read('ecos_mortgage_rate.json')
 if r and r.get('latest'):
  mr=dict(r['latest']);series=[x for x in (r.get('series') or []) if x.get('item')=='주택담보대출']
  if len(series)>1:
   prev=series[-2];mr['previous_period']=prev.get('period');mr['previous_rate_pct']=prev.get('rate_pct');mr['change_pp']=round(float(mr['rate_pct'])-float(prev['rate_pct']),2)
  d['mortgage_rate_official']=mr;d.setdefault('data_status',{})['ecos_mortgage_rate']='connected'
 base=read('ecos_base_rate.json')
 if base and base.get('latest'):
  d['base_rate_official']=base;d.setdefault('data_status',{})['ecos_base_rate']='connected'
 e=read('ecos_m2.json')
 if e and e.get('series'):
  x=e['series'][-1];px=e['series'][-2] if len(e['series'])>1 else {}
  d['m2_official']={'period':x['period'],'mom_pct':x['mom_pct'],'yoy_pct':x['yoy_pct'],'previous_period':px.get('period'),'previous_mom_pct':px.get('mom_pct'),'previous_yoy_pct':px.get('yoy_pct'),'mom_change_pp':round(float(x['mom_pct'])-float(px['mom_pct']),2) if px.get('mom_pct') is not None else None,'yoy_change_pp':round(float(x['yoy_pct'])-float(px['yoy_pct']),2) if px.get('yoy_pct') is not None else None,'source':'한국은행 ECOS 101Y003','definition':e.get('definition'),'selected_item':e.get('selected_item')}
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
 # Fallback directly to the already-connected statusBoard payload so the dashboard
 # never shows "수집 대기" merely because an adapter filename is missing.
 sb=read('kb_statusboard_live.json')
 def from_status(kind,label,key):
  try:
   hit=(sb.get('targets') or {}).get(kind) or {}
   rows=((((hit.get('payload') or {}).get('dataBody') or {}).get('data') or {}).get(label) or [])
   z=next((x for x in rows if str(x.get('법정동코드'))=='1100000000' or str(x.get('지역명'))=='서울'),None)
   if not z:return None
   return {'status':'connected','source':'KB부동산 데이터허브 statusBoard','region':'서울','frequency':'weekly',
    'latest':{'date':str(z.get('통계기준년월일시') or hit.get('date') or ''),'value':float(z.get('현재데이터') or z.get(key)),
              'display_value':z.get(key),'change_pct':float(z.get('변동률')) if z.get('변동률') not in (None,'') else None}}
  except Exception:return None
 if not sale or sale.get('status')!='connected': sale=from_status('sale','주간 매매지수','매매지수')
 if not rent or rent.get('status')!='connected': rent=from_status('rent','주간 전세지수','전세지수')
 if sale and sale.get('status')=='connected':
  d['kb_weekly_sale_index']=sale;d.setdefault('data_status',{})['kb_weekly_sale_index']='connected';d.setdefault('data_status',{})['kb_history']='connected'
 if rent and rent.get('status')=='connected':
  d['kb_weekly_rent_index']=rent;d.setdefault('data_status',{})['kb_weekly_rent_index']='connected'
 unsold=read('molit_unsold.json')
 if unsold and unsold.get('seoul_units') is not None:
  d['unsold_seoul']=unsold;d.setdefault('data_status',{})['molit_unsold']='connected'
 kb=read('kb_history_status.json')
 if kb and not sale:d.setdefault('data_status',{})['kb_history']=kb.get('status')
 refresh=read('refresh_run_status.json')
 if refresh:
  d['refresh_run']=refresh
  for name,status in (refresh.get('sources') or {}).items():
   d.setdefault('data_status',{})[name+'_refresh']=status
 d['updated_at']=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat();OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2))
 if e:(ROOT/'dist/m2_history.json').write_text(json.dumps(e,ensure_ascii=False,indent=2))
 if kb:(ROOT/'dist/kb_history_status.json').write_text(json.dumps(kb,ensure_ascii=False,indent=2))
 print(json.dumps({'built':str(OUT),'sources':{'molit':bool(m),'ecos_m2':bool(e),'kb_history':bool(kb)}},ensure_ascii=False))
if __name__=='__main__':main()
