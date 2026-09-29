#!/usr/bin/env python3
"""Collect valuation inputs from public KB DataHub endpoints.

Sources:
- KB apartment mortgage-loan PIR (Seoul, quarterly)
- Seoul apartment sale-to-jeonse ratio (monthly)
- Seoul apartment average sale price (monthly)
"""
import json,urllib.request,urllib.parse,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]
OUT=R/'data_sources/kb_valuation_sources.json'
BASE='https://data-api.kbland.kr/bfmstat/weekMnthlyHuseTrnd/'
HEAD={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/plain,*/*','Referer':'https://data.kbland.kr/','Origin':'https://data.kbland.kr'}

def get(ep,params=None):
    u=BASE+ep
    if params:u+='?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(u,headers=HEAD)
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def payload(raw):
    return ((raw or {}).get('dataBody') or {}).get('data') or (raw or {}).get('dataBody') or raw

def seoul_series(raw):
    d=payload(raw);dates=d.get('날짜리스트') or [];rows=d.get('데이터리스트') or []
    row=next((x for x in rows if isinstance(x,dict) and (str(x.get('지역코드'))=='1100000000' or x.get('지역명')=='서울')),None)
    if not row:raise RuntimeError('Seoul row missing')
    vals=row.get('dataList') or []
    if len(vals)!=len(dates):raise RuntimeError(f'date/value length mismatch {len(dates)} != {len(vals)}')
    return d,dates,vals

def main():
    pir_raw=get('husScurlnPir',{'메뉴코드':'01'})
    ratio_raw=get('dealCntstTnantRato')
    avg_raw=get('avgPrc',{'매매전세코드':'01','매물종별구분':'01','면적별코드':'02','월간주간구분코드':'01'})

    pd,pdates,pvals=seoul_series(pir_raw)
    rd,rdates,rvals=seoul_series(ratio_raw)
    ad,adates,avals=seoul_series(avg_raw)

    pir=[]
    for dt,v in zip(pdates,pvals):
        if not isinstance(v,dict) or v.get('KB아파트PIR') is None:continue
        pir.append({'period':str(dt),'pir':float(v['KB아파트PIR']),
                    'house_price_manwon':float(v['주택가격']) if v.get('주택가격') is not None else None,
                    'annual_income_manwon':float(v['가구소득']) if v.get('가구소득') is not None else None})
    ratio=[{'period':str(dt),'rent_to_sale_pct':float(v)} for dt,v in zip(rdates,rvals) if v is not None]
    avg=[{'period':str(dt),'avg_sale_price_manwon':float(v)} for dt,v in zip(adates,avals) if v is not None]

    if len(pir)<40 or len(ratio)<120 or len(avg)<120:raise RuntimeError('valuation history unexpectedly short')
    out={
      'status':'connected',
      'source':'KB부동산 데이터허브',
      'region':'서울',
      'pir':{
        'label':'KB아파트담보대출 PIR','frequency':'quarterly','series':pir,'latest':pir[-1],
        'updated_at':pd.get('업데이트일자'),
        'definition':'KB 담보대출 아파트 주택가격 중위값 / 대출자 연소득 중위값',
        'endpoint':BASE+'husScurlnPir'
      },
      'rent_to_sale_ratio':{
        'label':'서울 아파트 전세가율','frequency':'monthly','series':ratio,'latest':ratio[-1],
        'updated_at':rd.get('업데이트일자'),
        'definition':'아파트 매매가격 대비 전세가격 비율',
        'endpoint':BASE+'dealCntstTnantRato'
      },
      'avg_sale_price':{
        'label':'서울 아파트 평균 매매가격','frequency':'monthly','series':avg,'latest':avg[-1],
        'updated_at':ad.get('업데이트일자'),
        'definition':'KB 서울 아파트 평균 매매가격',
        'endpoint':BASE+'avgPrc'
      },
      'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'pir':len(pir),'ratio':len(ratio),'avg':len(avg),'latest':{'pir':pir[-1],'ratio':ratio[-1],'avg':avg[-1]}},ensure_ascii=False))
if __name__=='__main__':main()
