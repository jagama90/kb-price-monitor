#!/usr/bin/env python3
"""Collect official REB R-ONE monthly Seoul apartment sale/rent indices for cross-check context."""
from __future__ import annotations
import datetime,json,os,pathlib,random,time,urllib.parse,urllib.request
from zoneinfo import ZoneInfo

R=pathlib.Path(__file__).resolve().parents[1]
OUT=R/'data_sources/reb_crosscheck.json'
BASE='https://www.reb.or.kr/r-one/openapi/'
CONTRACTS={
    'sale':{'statbl_id':'A_2024_00045','cls_id':'500008','itm_id':'100001'},
    'rent':{'statbl_id':'A_2024_00050','cls_id':'500008','itm_id':'100001'},
}

def get(ep,p):
    q=urllib.parse.urlencode(p);last=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(BASE+ep+'?'+q,headers={'User-Agent':'kb-price-monitor/1.0'})
            with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
        except Exception as e:
            last=e
            if attempt<3:time.sleep(min(12,2**attempt+random.random()))
    raise last

def rows(x):
    v=x.get('SttsApiTblData',[])
    if isinstance(v,list):
        for z in v:
            if isinstance(z,dict) and isinstance(z.get('row'),list):return z['row']
    return []

def norm(x):
    ym=''.join(ch for ch in str(x.get('WRTTIME_IDTFR_ID') or '') if ch.isdigit())[:6]
    v=x.get('DTA_VAL')
    return {'ym':ym,'value':float(v) if v not in (None,'') else None,
            'cls_id':str(x.get('CLS_ID') or ''),'cls_name':x.get('CLS_NM'),
            'itm_id':str(x.get('ITM_ID') or ''),'itm_name':x.get('ITM_NM'),'unit':x.get('UI_NM')}

def fetch_series(key,contract,start_year,end_year):
    raw=get('SttsApiTblData.do',{'KEY':key,'Type':'json','STATBL_ID':contract['statbl_id'],'DTACYCLE_CD':'MM',
        'CLS_ID':contract['cls_id'],'ITM_ID':contract['itm_id'],'START_WRTTIME':str(start_year),'END_WRTTIME':str(end_year),
        'pIndex':1,'pSize':1000})
    data=[norm(x) for x in rows(raw)]
    data=[x for x in data if x['ym'] and x['value'] is not None]
    if not data:
        raise RuntimeError(f"R-ONE {contract['statbl_id']}: no monthly Seoul data")
    by={x['ym']:x for x in data}
    return [by[k] for k in sorted(by)]

def pct(a,b):
    return round((b/a-1)*100,2) if a not in (None,0) and b is not None else None

def change(series,months):
    return pct(series[-1-months]['value'],series[-1]['value']) if len(series)>months else None

def main():
    key=os.getenv('RONE_API_KEY','').strip()
    if not key:raise RuntimeError('RONE_API_KEY is required')
    today=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date()
    start_year=today.year-3;end_year=today.year
    sale=fetch_series(key,CONTRACTS['sale'],start_year,end_year)
    rent=fetch_series(key,CONTRACTS['rent'],start_year,end_year)
    sm={x['ym']:x for x in sale};rm={x['ym']:x for x in rent};common=sorted(set(sm)&set(rm))
    if len(common)<24:raise RuntimeError(f'R-ONE sale/rent common history too short: {len(common)}')
    sale=[sm[m] for m in common];rent=[rm[m] for m in common]
    latest=common[-1];start='202502' if '202502' in common else common[max(0,len(common)-20)]
    si=common.index(start)
    accumulation={'start_ym':start,'end_ym':latest,
                  'sale_pct':pct(sale[si]['value'],sale[-1]['value']),
                  'rent_pct':pct(rent[si]['value'],rent[-1]['value'])}
    if accumulation['sale_pct'] is not None and accumulation['rent_pct'] is not None:
        accumulation['sale_minus_rent_pp']=round(accumulation['sale_pct']-accumulation['rent_pct'],2)
    out={'status':'connected','source':'한국부동산원 R-ONE','scope':{'region':'서울','housing_type':'아파트'},
         'frequency':'monthly','contracts':CONTRACTS,'latest':{'ym':latest,'sale_index':sale[-1]['value'],'rent_index':rent[-1]['value']},
         'momentum':{'sale_1m_pct':change(sale,1),'sale_3m_pct':change(sale,3),
                     'rent_1m_pct':change(rent,1),'rent_3m_pct':change(rent,3)},
         'accumulation':accumulation,'series':{'sale':sale,'rent':rent},
         'role':'crosscheck_context_only','production_model_weight_changed':False,
         'weekly_exact_status':'not_connected_rone_weekly_tables_return_INFO-200',
         'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'ok','latest':out['latest'],'momentum':out['momentum'],'accumulation':accumulation},ensure_ascii=False))

if __name__=='__main__':main()
