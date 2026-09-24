#!/usr/bin/env python3
import json,pathlib,datetime,statistics
R=pathlib.Path(__file__).resolve().parents[1];O=R/'dist/final_backtest.json'
def clamp(x):return max(0,min(100,x))
def main():
 p=json.loads((R/'dist/garak_geumho_24a_history.json').read_text())['series']; pm={x['ym']:float(x['sale']) for x in p if x.get('sale')}
 s=json.loads((R/'data_sources/kb_sentiment.json').read_text()).get('rows',[])
 se=[x for x in s if x.get('region')=='서울']
 by={}
 for x in se:by.setdefault(x['date'][:6],{})[x['kind']]=x['values']
 rows=[]
 for ym in sorted(pm):
  hist=[pm[k] for k in sorted(pm) if k<=ym][-36:]
  if len(hist)<24:continue
  lo,hi=min(hist),max(hist);pos=(pm[ym]-lo)/(hi-lo) if hi>lo else .5; value=max(25,min(75,75-50*pos))
  z=by.get(ym,{})
  buy=z.get('매수우위',{}).get('매수우위지수'); je=z.get('전세수급',{}).get('전세수급지수')
  sentiment=clamp(float(buy)) if buy is not None else None;supply=clamp(float(je)) if je is not None else None
  comps={'sentiment':sentiment,'value':value,'supply':supply}; w={'sentiment':20,'value':20,'supply':15};a=[k for k,v in comps.items() if v is not None];cov=sum(w[k] for k in a);score=round(sum(comps[k]*w[k] for k in a)/cov,1) if cov>=35 else None
  row={'ym':ym,'partial_score':score,'coverage_weight':cov,'components':comps,'target_price':pm[ym]}
  for h in (1,3,6,12):
   y=int(ym[:4]);m=int(ym[4:]);q=y*12+m-1+h;k=f'{q//12:04d}{q%12+1:02d}';row[f'fwd_{h}m_pct']=round((pm[k]/pm[ym]-1)*100,2) if k in pm else None
  rows.append(row)
 chk=[x for x in rows if '202210'<=x['ym']<='202306']
 out={'status':'finance_history_required','certified_final':False,'reason':'Exact five-component historical formula still requires release-date-aligned M2 and mortgage-rate history; no proxy is substituted.','no_future_leakage':True,'target':'KB Garak Geumho 24A monthly sale general price','scored_partial_rows':sum(x['partial_score'] is not None for x in rows),'checkpoint_2022_10_to_2023_06':chk,'rows':rows,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 O.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'status':out['status'],'scored_partial_rows':out['scored_partial_rows'],'checkpoint_rows':len(chk)},ensure_ascii=False))
if __name__=='__main__':main()
