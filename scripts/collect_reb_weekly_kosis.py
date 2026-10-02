#!/usr/bin/env python3
"""Collect exact weekly Seoul apartment sale/rent indices from the public KOSIS table UI.

KOSIS OpenAPI requires a separately issued API key. This collector deliberately uses the
public CSV download route exposed by the table UI so production is not blocked on a new secret.
The downloaded tables are official 한국부동산원 전국주택가격동향조사 series.
"""
from __future__ import annotations
import csv,datetime,io,json,pathlib,re,tempfile,time
from playwright.sync_api import sync_playwright,TimeoutError as PlaywrightTimeoutError

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data_sources/reb_weekly.json'
ORG='408'
KNOWN_SALE='DT_304004_WEEK_002_C'
CANDIDATES=[KNOWN_SALE]+[f'DT_304004_WEEK_{i:03d}_C' for i in range(1,13) if f'DT_304004_WEEK_{i:03d}_C'!=KNOWN_SALE]

def decode_bytes(raw:bytes)->str:
    for enc in ('utf-8-sig','cp949','euc-kr','utf-8'):
        try:return raw.decode(enc)
        except UnicodeDecodeError:pass
    return raw.decode('utf-8',errors='replace')

def date8(v):
    s=''.join(re.findall(r'\d',str(v or '')))
    if len(s)>=8 and s[:4].startswith('20'):
        try:
            d=datetime.datetime.strptime(s[:8],'%Y%m%d').date()
            return d.strftime('%Y%m%d')
        except ValueError:return None
    return None

def num(v):
    s=str(v or '').strip().replace(',','')
    if not s or s in ('-','—','..'):return None
    try:return float(s)
    except ValueError:return None

def parse_seoul_series(text:str):
    rows=list(csv.reader(io.StringIO(text)))
    if not rows:raise ValueError('empty csv')
    date_row_idx=None;date_cols={}
    for ri,row in enumerate(rows[:80]):
        hits={ci:date8(cell) for ci,cell in enumerate(row)}
        hits={ci:d for ci,d in hits.items() if d}
        if len(hits)>len(date_cols):
            date_row_idx=ri;date_cols=hits
    if len(date_cols)<20:
        # KOSIS may use a two-line header: concatenate nearby header cells vertically.
        for ri in range(min(80,len(rows)-1)):
            mx=max(len(rows[ri]),len(rows[ri+1]))
            hits={}
            for ci in range(mx):
                a=rows[ri][ci] if ci<len(rows[ri]) else ''
                b=rows[ri+1][ci] if ci<len(rows[ri+1]) else ''
                d=date8(a+' '+b)
                if d:hits[ci]=d
            if len(hits)>len(date_cols):
                date_row_idx=ri+1;date_cols=hits
    if len(date_cols)<20:
        raise ValueError(f'date columns not found: {len(date_cols)}')
    best=None
    for ri,row in enumerate(rows):
        if ri<=date_row_idx:continue
        if not any(str(c).strip()=='서울' for c in row):continue
        pts=[]
        for ci,d in date_cols.items():
            if ci<len(row):
                v=num(row[ci])
                if v is not None and 40<=v<=160:pts.append((d,v))
        if best is None or len(pts)>len(best):best=pts
    if not best or len(best)<20:
        raise ValueError(f'Seoul index row not found; best={0 if best is None else len(best)}')
    by={d:v for d,v in best}
    return [{'date':d,'value':by[d]} for d in sorted(by)]

def classify(text:str):
    compact=re.sub(r'\s+','',text)
    if '전세가격지수' in compact:return 'rent'
    if '매매가격지수' in compact:return 'sale'
    return None

def download_csv(page,tbl_id,tmpdir:pathlib.Path):
    url=f'https://kosis.kr/statHtml/statHtml.do?orgId={ORG}&tblId={tbl_id}&conn_path=I2'
    page.goto(url,wait_until='domcontentloaded',timeout=30000)
    page.wait_for_timeout(1800)
    btn=page.locator('#ico_download')
    if btn.count()<1 or not btn.first.is_visible():return None
    btn.first.click()
    page.wait_for_timeout(700)
    csv_btn=page.locator('#csvFormat')
    if csv_btn.count()<1:return None
    csv_btn.first.click(force=True)
    page.wait_for_timeout(250)
    try:
        with page.expect_download(timeout=15000) as di:
            page.locator('#btnDown').first.click(force=True)
        dl=di.value
    except PlaywrightTimeoutError:
        return None
    p=tmpdir/f'{tbl_id}.csv';dl.save_as(str(p))
    raw=p.read_bytes();text=decode_bytes(raw)
    return {'table_id':tbl_id,'url':url,'text':text,'suggested_filename':dl.suggested_filename}

def pct(a,b):
    return round((b/a-1)*100,2) if a not in (None,0) and b is not None else None

def lag(series,n):
    return pct(series[-1-n]['value'],series[-1]['value']) if len(series)>n else None

def closest(series,target):
    exact=next((x for x in series if x['date']==target),None)
    if exact:return exact
    td=datetime.datetime.strptime(target,'%Y%m%d').date()
    later=[]
    for x in series:
        d=datetime.datetime.strptime(x['date'],'%Y%m%d').date()
        if d>=td:later.append((d,x))
    return later[0][1] if later and (later[0][0]-td).days<=14 else None

def main():
    found={}
    diagnostics=[]
    with tempfile.TemporaryDirectory() as td, sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        ctx=browser.new_context(accept_downloads=True,locale='ko-KR')
        page=ctx.new_page()
        for tbl in CANDIDATES:
            try:
                got=download_csv(page,tbl,pathlib.Path(td))
                if not got:
                    diagnostics.append({'table_id':tbl,'status':'no_download'})
                    continue
                kind=classify(got['text'])
                diagnostics.append({'table_id':tbl,'status':'downloaded','kind':kind,'filename':got['suggested_filename']})
                if kind in ('sale','rent') and kind not in found:
                    series=parse_seoul_series(got['text'])
                    found[kind]={'table_id':tbl,'series':series}
                    print(json.dumps({'found':kind,'table_id':tbl,'rows':len(series),'latest':series[-1]},ensure_ascii=False))
                if set(found)=={'sale','rent'}:break
            except Exception as e:
                diagnostics.append({'table_id':tbl,'status':'error','error':repr(e)})
        browser.close()
    if set(found)!={'sale','rent'}:
        raise RuntimeError('KOSIS weekly sale/rent tables incomplete: '+json.dumps({'found':list(found),'diagnostics':diagnostics},ensure_ascii=False))
    sale=found['sale']['series'];rent=found['rent']['series']
    sm={x['date']:x for x in sale};rm={x['date']:x for x in rent};common=sorted(set(sm)&set(rm))
    if len(common)<70:raise RuntimeError(f'common weekly history too short: {len(common)}')
    sale=[sm[d] for d in common];rent=[rm[d] for d in common]
    latest=common[-1]
    start_target='20250203';sb=closest(sale,start_target)
    if not sb:raise RuntimeError('2025-02-03 comparison start unavailable')
    start=sb['date'];idx=common.index(start)
    acc={'requested_start_date':start_target,'start_date':start,'end_date':latest,
         'interval_weeks':round((datetime.datetime.strptime(latest,'%Y%m%d').date()-datetime.datetime.strptime(start,'%Y%m%d').date()).days/7,1),
         'sale_pct':pct(sale[idx]['value'],sale[-1]['value']),'rent_pct':pct(rent[idx]['value'],rent[-1]['value'])}
    if acc['sale_pct'] is not None and acc['rent_pct'] is not None:acc['sale_minus_rent_pp']=round(acc['sale_pct']-acc['rent_pct'],2)
    out={'status':'connected','source':'KOSIS · 한국부동산원 전국주택가격동향조사',
         'scope':{'region':'서울','housing_type':'아파트'},'frequency':'weekly',
         'contracts':{'sale':{'org_id':ORG,'table_id':found['sale']['table_id']},
                      'rent':{'org_id':ORG,'table_id':found['rent']['table_id']}},
         'latest':{'date':latest,'sale_index':sale[-1]['value'],'rent_index':rent[-1]['value']},
         'momentum':{'sale_4w_pct':lag(sale,4),'sale_13w_pct':lag(sale,13),
                     'rent_4w_pct':lag(rent,4),'rent_13w_pct':lag(rent,13)},
         'accumulation':acc,'series':{'sale':sale,'rent':rent},
         'role':'crosscheck_context_only','production_model_weight_changed':False,
         'collection_method':'public_kosis_csv_ui',
         'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'ok','contracts':out['contracts'],'latest':out['latest'],'momentum':out['momentum'],'accumulation':acc},ensure_ascii=False))

if __name__=='__main__':main()
