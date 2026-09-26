#!/usr/bin/env python3
"""Build a standardized housing affordability engine from official mortgage rates.

The DSR calculation is a fixed benchmark (income 100m KRW, DSR 40%, 30-year
amortizing mortgage) for comparability, not an individual credit-limit estimate.
"""
import json,math,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]
M=R/'data_sources/ecos_mortgage_rate.json';P=R/'data_sources/reb_long_cycle.json';O=R/'dist/affordability_engine.json'
def payment(principal,annual,years=30):
 r=annual/100/12;n=years*12
 return principal/n if r==0 else principal*r*(1+r)**n/((1+r)**n-1)
def principal_for_payment(monthly,annual,years=30):
 r=annual/100/12;n=years*12
 return monthly*n if r==0 else monthly*((1+r)**n-1)/(r*(1+r)**n)
def pct(a,b):return None if a in (None,0) or b is None else (b/a-1)*100
def main():
 md=json.loads(M.read_text());pd=json.loads(P.read_text())
 rates={}
 fixed={};variable={}
 for x in md.get('series',[]):
  ym=x.get('period');item=str(x.get('item') or '');v=x.get('rate_pct')
  if not ym or v is None:continue
  if item=='주택담보대출':rates[ym]=float(v)
  elif '고정형' in item:fixed[ym]=float(v)
  elif '변동형' in item:variable[ym]=float(v)
 prices={x['ym']:float(x['value']) for x in pd.get('series',{}).get('price',[]) if x.get('ym') and x.get('value') is not None}
 ys=sorted(set(rates)&set(prices))
 rows=[];budget=100_000_000*.40/12
 for ym in ys:
  rate=rates[ym];pay5=payment(500_000_000,rate);maxloan=principal_for_payment(budget,rate)
  rows.append({'ym':ym,'mortgage_rate_pct':rate,'fixed_rate_pct':fixed.get(ym),'variable_rate_pct':variable.get(ym),
    'payment_5eok_won':round(pay5),'max_loan_income100m_dsr40_won':round(maxloan),'seoul_price_index':prices[ym]})
 for i,x in enumerate(rows):
  for lag in (1,3,6,12):
   if i>=lag:
    z=rows[i-lag]
    x[f'rate_change_{lag}m_pp']=round(x['mortgage_rate_pct']-z['mortgage_rate_pct'],3)
    x[f'payment_change_{lag}m_pct']=round(pct(z['payment_5eok_won'],x['payment_5eok_won']),3)
    x[f'loan_capacity_change_{lag}m_pct']=round(pct(z['max_loan_income100m_dsr40_won'],x['max_loan_income100m_dsr40_won']),3)
    old=z['max_loan_income100m_dsr40_won']/z['seoul_price_index'];new=x['max_loan_income100m_dsr40_won']/x['seoul_price_index']
    x[f'affordability_change_{lag}m_pct']=round(pct(old,new),3)
 latest=rows[-1] if rows else {}
 out={'status':'research_only','source':['한국은행 ECOS 주택담보대출 신규취급액 금리','R-ONE 서울 아파트 가격지수'],
  'benchmark':{'annual_income_won':100000000,'dsr_pct':40,'term_years':30,'example_loan_won':500000000,
    'note':'비교용 고정 가정이며 개인별 실제 대출가능액이 아님'},'latest':latest,'rows':rows,
  'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 O.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'rows':len(rows),'latest':latest},ensure_ascii=False))
if __name__=='__main__':main()
