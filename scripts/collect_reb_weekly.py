#!/usr/bin/env python3
"""Collect REB R-ONE weekly Seoul apartment sale/rent indices as cross-check context."""
from __future__ import annotations
import datetime,json,os,pathlib,random,time,urllib.parse,urllib.request
from zoneinfo import ZoneInfo

R=pathlib.Path(__file__).resolve().parents[1]
OUT=R/'data_sources/reb_weekly.json'
BASE='https://www.reb.or.kr/r-one/openapi/'
TABLES={'sale':'T244183133223976','rent':'T247713133046872'}
KNOWN_PAIR=('500008','100001')

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

def norm_date(v):
    z=''.join(ch for ch in str(v or '') if ch.isdigit())
    return z[:8] if len(z)>=8 else None

def fetch_series(key,table,cls_id,itm_id,start_date,end_date):
    out=[]
    for page in range(1,5):
        raw=get('SttsApiTblData.do',{'KEY':key,'Type':'json','STATBL_ID':table,'DTACYCLE_CD':'WK',
            'CLS_ID':cls_id,'ITM_ID':itm_id,'START_WRTTIME':str(start_date),'END_WRTTIME':str(end_date),
            'pIndex':page,'pSize':1000})
        rr=rows(raw)
        for x in rr:
            d=norm_date(x.get('WRTTIME_IDTFR_ID'));v=x.get('DTA_VAL')
            if d and v not in (None,''):
                out.append({'date':d,'value':float(v),'cls_id':str(x.get('CLS_ID') or cls_id),
                    'cls_name':x.get('CLS_NM'),'itm_id':str(x.get('ITM_ID') or itm_id),
                    'itm_name':x.get('ITM_NM'),'unit':x.get('UI_NM')})
        if len(rr)<1000:break
    by={x['date']:x for x in out}
    return [by[k] for k in sorted(by)]

def discover_pair(key,table,today):
    monday=today-datetime.timedelta(days=today.weekday())
    for back in range(0,8):
        probe=(monday-datetime.timedelta(days=7*back)).strftime('%Y%m%d')
        for page in range(1,5):
            raw=get('SttsApiTblData.do',{'KEY':key,'Type':'json','STATBL_ID':table,'DTACYCLE_CD':'WK',
                'WRTTIME_IDTFR_ID':probe,'pIndex':page,'pSize':1000})
            rr=rows(raw)
            for x in rr:
                region=str(x.get('CLS_FULLNM') or x.get('CLS_NM') or '')
                item=str(x.get('ITM_FULLNM') or x.get('ITM_NM') or '')
                if '서울' in region and ('지수' in item or item in ('가격','')):
                    return str(x.get('CLS_ID')),str(x.get('ITM_ID')),probe
            if len(rr)<1000:break
    return None

def pct(a,b):
    return round((b/a-1)*100,2) if a not in (None,0) and b is not None else None

def enrich(series):
    for i,x in enumerate(series):x['change_pct']=pct(series[i-1]['value'],x['value']) if i else None
    return series

def lag_pct(series,weeks):
    return pct(series[-1-weeks]['value'],series[-1]['value']) if len(series)>weeks else None

def closest_start(series,target):
    exact=next((x for x in series if x['date']==target),None)
    if exact:return exact
    later=[x for x in series if x['date']>=target]
    if not later:return None
    d0=datetime.datetime.strptime(target,'%Y%m%d').date();d1=datetime.datetime.strptime(later[0]['date'],'%Y%m%d').date()
    return later[0] if (d1-d0).days<=14 else None

def main():
    key=os.getenv('RONE_API_KEY','').strip()
    if not key:raise RuntimeError('RONE_API_KEY is required')
    today=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date()
    end_date=today.strftime('%Y%m%d')
    start_date=(today-datetime.timedelta(days=7*110)).strftime('%Y%m%d')
    series={};contracts={}
    for kind,table in TABLES.items():
        cls_id,itm_id=KNOWN_PAIR
        data=fetch_series(key,table,cls_id,itm_id,start_date,end_date)
        probe_date=None
        if not data:
            pair=discover_pair(key,table,today)
            if not pair:raise RuntimeError(f'R-ONE weekly {kind}: Seoul index pair not found')
            cls_id,itm_id,probe_date=pair
            data=fetch_series(key,table,cls_id,itm_id,start_date,end_date)
        if len(data)<40:raise RuntimeError(f'R-ONE weekly {kind}: insufficient rows {len(data)}')
        series[kind]=enrich(data);contracts[kind]={'statbl_id':table,'dtacycle_cd':'WK','cls_id':cls_id,'itm_id':itm_id,'probe_date':probe_date}
    sm={x['date']:x for x in series['sale']};rm={x['date']:x for x in series['rent']};common=sorted(set(sm)&set(rm))
    if len(common)<40:raise RuntimeError('R-ONE weekly: insufficient common sale/rent dates')
    latest_date=common[-1];latest_s=sm[latest_date];latest_r=rm[latest_date]
    target='20250203';sb=closest_start([sm[d] for d in common],target);rb=rm.get(sb['date']) if sb else None
    accum=None
    if sb and rb:
        d0=datetime.datetime.strptime(sb['date'],'%Y%m%d').date();d1=datetime.datetime.strptime(latest_date,'%Y%m%d').date()
        accum={'requested_start_date':target,'start_date':sb['date'],'end_date':latest_date,'weeks':round((d1-d0).days/7,1),
            'sale_pct':pct(sb['value'],latest_s['value']),'rent_pct':pct(rb['value'],latest_r['value'])}
        if accum['sale_pct'] is not None and accum['rent_pct'] is not None:accum['sale_minus_rent_pp']=round(accum['sale_pct']-accum['rent_pct'],2)
    sale_common=[sm[d] for d in common];rent_common=[rm[d] for d in common]
    out={'status':'connected','source':'한국부동산원 R-ONE','scope':{'region':'서울','housing_type':'아파트'},'frequency':'weekly',
        'contracts':contracts,'latest':{'date':latest_date,'sale_index':latest_s['value'],'rent_index':latest_r['value'],
            'sale_change_pct':latest_s.get('change_pct'),'rent_change_pct':latest_r.get('change_pct')},
        'momentum':{'sale_4w_pct':lag_pct(sale_common,4),'sale_13w_pct':lag_pct(sale_common,13),
            'rent_4w_pct':lag_pct(rent_common,4),'rent_13w_pct':lag_pct(rent_common,13)},
        'accumulation':accum,'series':{'sale':sale_common,'rent':rent_common},
        'role':'crosscheck_context_only','production_model_weight_changed':False,
        'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'ok','latest':out['latest'],'momentum':out['momentum'],'accumulation':accum},ensure_ascii=False))
if __name__=='__main__':main()
