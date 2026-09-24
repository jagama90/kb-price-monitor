#!/usr/bin/env python3
"""Fail-closed walk-forward validation of the production five-component index.
The checkpoint intentionally covers the 2022 decline through the 2023 turn."""
import json,pathlib,datetime,calendar,math
R=pathlib.Path(__file__).resolve().parents[1];O=R/'dist/final_backtest.json'
W={'finance':25,'sentiment':20,'demand':20,'value':20,'supply':15}
def clamp(x):return max(0,min(100,x))
def shift(ym,n):
 y=int(ym[:4]);m=int(ym[4:]);q=y*12+m-1+n
 return f'{q//12:04d}{q%12+1:02d}'
def scalar(vals):
 for k,v in (vals or {}).items():
  if isinstance(v,(int,float)) and ('지수' in k or '값' in k): return float(v)
 return None
def corr(a,b):
 z=[(x,y) for x,y in zip(a,b) if x is not None and y is not None]
 if len(z)<3:return None
 ax=sum(x for x,_ in z)/len(z);ay=sum(y for _,y in z)/len(z)
 num=sum((x-ax)*(y-ay) for x,y in z);dx=sum((x-ax)**2 for x,_ in z);dy=sum((y-ay)**2 for _,y in z)
 return round(num/math.sqrt(dx*dy),3) if dx and dy else None
def main():
 prices=json.loads((R/'dist/garak_geumho_24a_history.json').read_text())['series']
 pm={x['ym']:float(x['sale']) for x in prices if x.get('sale')}
 sr=json.loads((R/'data_sources/kb_sentiment.json').read_text()).get('rows',[])
 se=sorted([x for x in sr if x.get('region')=='서울' and x.get('date')],key=lambda x:x['date'])
 m2=json.loads((R/'data_sources/ecos_m2.json').read_text()).get('series',[])
 mm={str(x['period']).replace('-','')[:6]:x for x in m2}
 demand=json.loads((R/'dist/molit_historical_backtest.json').read_text()).get('rows',[])
 dm={x['ym']:x for x in demand}
 rows=[]
 for ym in sorted(k for k in pm if '202210'<=k<='202306'):
  hist=[pm[k] for k in sorted(pm) if k<=ym][-36:]
  lo,hi=min(hist),max(hist);pos=(pm[ym]-lo)/(hi-lo) if hi>lo else .5
  value=max(25,min(75,75-50*pos))
  # KB weekly sentiment: only observations dated on/before that month's end.
  lastday=calendar.monthrange(int(ym[:4]),int(ym[4:]))[1];cut=f'{ym}{lastday:02d}'
  latest={}
  for x in se:
   if x['date']>cut:break
   latest[x['kind']]=x
  sale=[scalar((latest.get(k) or {}).get('values')) for k in ('매수우위','매매거래활발')]
  rent=[scalar((latest.get(k) or {}).get('values')) for k in ('전세수급','전세거래활발')]
  sentiment=round(sum(sale)/len(sale)/2,1) if all(v is not None for v in sale) else None
  supply=round(sum(rent)/len(rent)/2,1) if all(v is not None for v in rent) else None
  # Conservative no-leakage rule: M2 for month t-2 is safely available by month t end.
  mk=shift(ym,-2);mx=mm.get(mk)
  finance=clamp(50+float(mx['mom_pct'])*8+float(mx['yoy_pct'])*1.5) if mx and mx.get('mom_pct') is not None and mx.get('yoy_pct') is not None else None
  d=dm.get(ym)
  demand_score=clamp(50+float(d['trade_count_pct'])*.35+float(d['under15_share_pp'])*1.5) if d and d.get('trade_count_pct') is not None and d.get('under15_share_pp') is not None else None
  comps={'finance':finance,'sentiment':sentiment,'demand':demand_score,'value':value,'supply':supply}
  missing=[k for k,v in comps.items() if v is None];cov=sum(W[k] for k,v in comps.items() if v is not None)
  score=round(sum(comps[k]*W[k] for k in W)/100,1) if not missing else None
  row={'ym':ym,'score':score,'coverage_weight':cov,'missing':missing,'components':{k:(round(v,2) if v is not None else None) for k,v in comps.items()},'target_price':pm[ym],'m2_vintage_period':mk}
  for h in (1,3,6,12):
   k=shift(ym,h);row[f'fwd_{h}m_pct']=round((pm[k]/pm[ym]-1)*100,2) if k in pm else None
  rows.append(row)
 complete=[x for x in rows if x['score'] is not None];certified=len(rows)==9 and len(complete)==9
 metrics={}
 for h in (1,3,6,12):metrics[f'score_vs_fwd_{h}m_corr']=corr([x['score'] for x in complete],[x[f'fwd_{h}m_pct'] for x in complete])
 if complete:
  ordered=sorted(complete,key=lambda x:x['score']);n=max(1,len(ordered)//3)
  metrics['low_score_mean_fwd_6m_pct']=round(sum(x['fwd_6m_pct'] for x in ordered[:n] if x['fwd_6m_pct'] is not None)/max(1,sum(x['fwd_6m_pct'] is not None for x in ordered[:n])),2)
  metrics['high_score_mean_fwd_6m_pct']=round(sum(x['fwd_6m_pct'] for x in ordered[-n:] if x['fwd_6m_pct'] is not None)/max(1,sum(x['fwd_6m_pct'] is not None for x in ordered[-n:])),2)
 out={'status':'certified' if certified else 'incomplete','certified_final':certified,
  'formula':'finance25 + sentiment20 + demand20 + value20 + supply15; identical to production dashboard',
  'no_future_leakage':True,'vintage_rules':{'kb_sentiment':'latest observation dated <= month end','m2':'t-2 conservative publication lag','demand':'completed calendar month vs previous completed month','value':'trailing 36 months through score month only'},
  'target':'KB Garak Geumho 24A monthly sale general price','checkpoint':'2022-10..2023-06',
  'checkpoint_rows':rows,'metrics':metrics,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 O.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({'status':out['status'],'certified_final':certified,'complete_rows':len(complete),'metrics':metrics},ensure_ascii=False))
 if not certified: raise SystemExit('historical validation incomplete: '+json.dumps({x['ym']:x['missing'] for x in rows if x['missing']},ensure_ascii=False))
if __name__=='__main__':main()
