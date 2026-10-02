#!/usr/bin/env python3
"""Collect the exact official REB weekly apartment sale/rent time series.

Source: 한국부동산원 R-ONE 공개자료실 > 주간아파트가격동향조사 시계열통계표.
The workbook is downloaded from the public attachment UI and parsed without a private API.
"""
from __future__ import annotations
import datetime,json,pathlib,re,tempfile
from openpyxl import load_workbook
from playwright.sync_api import sync_playwright,TimeoutError as PlaywrightTimeoutError

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data_sources/reb_weekly.json'
LIST_URL='https://www.reb.or.kr/r-one/portal/bbs/statdata/searchBulletinPage.do'
TARGET_TITLE='주간아파트가격동향조사'

def norm_date(v):
    if isinstance(v,(datetime.datetime,datetime.date)):
        return v.strftime('%Y%m%d')
    s=''.join(re.findall(r'\d',str(v or '')))
    if len(s)>=8:
        try:return datetime.datetime.strptime(s[:8],'%Y%m%d').strftime('%Y%m%d')
        except ValueError:return None
    if len(s)==6:
        # workbook can encode dates as YYMMDD in older rows
        try:return datetime.datetime.strptime('20'+s,'%Y%m%d').strftime('%Y%m%d')
        except ValueError:return None
    return None

def number(v):
    if v is None:return None
    if isinstance(v,(int,float)):return float(v)
    s=str(v).strip().replace(',','')
    if not s or s in ('-','—'):return None
    try:return float(s)
    except ValueError:return None

def download_workbook(dest:pathlib.Path):
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        ctx=browser.new_context(accept_downloads=True,locale='ko-KR')
        page=ctx.new_page()
        page.goto(LIST_URL,wait_until='domcontentloaded',timeout=45000)
        page.wait_for_timeout(5000)
        rows=page.locator('table tbody tr')
        if rows.count()==0:
            print(json.dumps({'debug':'reb_board_empty','url':page.url,'title':page.title(),'body':page.locator('body').inner_text()[:5000]},ensure_ascii=False))
        hit=None
        for i in range(rows.count()):
            row=rows.nth(i)
            txt=row.inner_text().strip()
            if TARGET_TITLE in txt:
                hit=row
                break
        if hit is None:
            texts=[rows.nth(i).inner_text().strip() for i in range(min(rows.count(),30))]
            print(json.dumps({'debug':'reb_board_rows','url':page.url,'rows':texts},ensure_ascii=False))
            raise RuntimeError('REB weekly time-series bulletin row not found')
        # Open attachment layer from the title cell/link.
        links=hit.locator('a')
        if links.count():
            links.first.click()
        else:
            tds=hit.locator('td')
            if tds.count()<3:raise RuntimeError('REB bulletin row malformed')
            tds.nth(2).click()
        page.wait_for_timeout(900)
        frame=None
        for _ in range(20):
            frame=page.frame(name='raonkuploader_frame_kupload')
            if frame:break
            page.wait_for_timeout(250)
        if frame is None:
            raise RuntimeError('REB attachment frame not available')
        files=frame.locator('#file_list > li')
        if files.count()<1:
            raise RuntimeError('REB attachment list empty')
        chosen=None
        file_names=[]
        for i in range(files.count()):
            li=files.nth(i)
            txt=li.inner_text().strip()
            file_names.append(txt)
            low=txt.lower()
            if '.xlsx' in low or '.xls' in low or '시계열' in txt:
                chosen=li
                if '.xlsx' in low:break
        if chosen is None:
            # Legacy uploader convention: the second attachment is the workbook.
            chosen=files.nth(1 if files.count()>1 else 0)
        # Clicking the file row/select control marks it for download.
        try:
            chosen.locator('ul li').nth(1).click()
        except Exception:
            chosen.click()
        frame.locator('#button_download').wait_for(state='visible',timeout=10000)
        try:
            with page.expect_download(timeout=20000) as di:
                frame.locator('#button_download').click()
            dl=di.value
        except PlaywrightTimeoutError:
            raise RuntimeError('REB workbook download did not start; files='+json.dumps(file_names,ensure_ascii=False))
        dl.save_as(str(dest))
        browser.close()

def sheet_for(wb,kind):
    exact='매매지수' if kind=='sale' else '전세지수'
    if exact in wb.sheetnames:return wb[exact]
    needle='매매' if kind=='sale' else '전세'
    for name in wb.sheetnames:
        if needle in name and '지수' in name and '변동' not in name:
            return wb[name]
    raise RuntimeError(f'{kind} index sheet missing: {wb.sheetnames}')

def find_seoul_col(ws):
    candidates=[]
    for c in range(1,ws.max_column+1):
        vals=[]
        exact=False
        for r in range(1,min(ws.max_row,12)+1):
            v=ws.cell(r,c).value
            if v is None:continue
            s=str(v).strip()
            vals.append(s)
            if s=='서울':exact=True
        if exact:candidates.append(c)
    if not candidates:
        raise RuntimeError(f'Seoul column not found in {ws.title}')
    # Prefer the left-most exact 서울 aggregate column.
    return min(candidates)

def extract(ws):
    c=find_seoul_col(ws)
    out=[]
    for r in range(1,ws.max_row+1):
        d=norm_date(ws.cell(r,1).value)
        v=number(ws.cell(r,c).value)
        if d and v is not None and 40<=v<=180:
            out.append({'date':d,'value':v})
    by={x['date']:x for x in out}
    out=[by[k] for k in sorted(by)]
    if len(out)<100:
        raise RuntimeError(f'{ws.title} Seoul history too short: {len(out)}')
    return out,c

def pct(a,b):
    return round((b/a-1)*100,2) if a not in (None,0) and b is not None else None

def lag(series,n):
    return pct(series[-1-n]['value'],series[-1]['value']) if len(series)>n else None

def main():
    with tempfile.TemporaryDirectory() as td:
        book=pathlib.Path(td)/'reb_weekly.xlsx'
        download_workbook(book)
        wb=load_workbook(book,read_only=True,data_only=True)
        sws=sheet_for(wb,'sale');rws=sheet_for(wb,'rent')
        sale,scol=extract(sws);rent,rcol=extract(rws)
    sm={x['date']:x for x in sale};rm={x['date']:x for x in rent}
    common=sorted(set(sm)&set(rm))
    if len(common)<100:raise RuntimeError(f'common REB weekly history too short: {len(common)}')
    sale=[sm[d] for d in common];rent=[rm[d] for d in common]
    latest=common[-1];start='20250203'
    if start not in common:
        later=[d for d in common if d>=start]
        if not later:raise RuntimeError('2025-02-03 start unavailable')
        start=later[0]
        gap=(datetime.datetime.strptime(start,'%Y%m%d')-datetime.datetime.strptime('20250203','%Y%m%d')).days
        if gap>14:raise RuntimeError(f'2025-02-03 start gap too large: {start}')
    i=common.index(start)
    acc={'requested_start_date':'20250203','start_date':start,'end_date':latest,
         'interval_weeks':round((datetime.datetime.strptime(latest,'%Y%m%d')-datetime.datetime.strptime(start,'%Y%m%d')).days/7,1),
         'sale_pct':pct(sale[i]['value'],sale[-1]['value']),'rent_pct':pct(rent[i]['value'],rent[-1]['value'])}
    if acc['sale_pct'] is not None and acc['rent_pct'] is not None:
        acc['sale_minus_rent_pp']=round(acc['sale_pct']-acc['rent_pct'],2)
    out={'status':'connected','source':'한국부동산원 R-ONE 주간아파트가격동향조사 시계열통계표',
         'scope':{'region':'서울','housing_type':'아파트'},'frequency':'weekly',
         'latest':{'date':latest,'sale_index':sale[-1]['value'],'rent_index':rent[-1]['value']},
         'momentum':{'sale_4w_pct':lag(sale,4),'sale_13w_pct':lag(sale,13),
                     'rent_4w_pct':lag(rent,4),'rent_13w_pct':lag(rent,13)},
         'accumulation':acc,'series':{'sale':sale,'rent':rent},
         'workbook':{'bulletin_title':TARGET_TITLE,'sale_sheet':sws.title,'rent_sheet':rws.title,
                     'sale_seoul_column':scol,'rent_seoul_column':rcol},
         'role':'crosscheck_context_only','production_model_weight_changed':False,
         'collection_method':'public_reb_timeseries_workbook',
         'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'ok','latest':out['latest'],'momentum':out['momentum'],'accumulation':acc,'workbook':out['workbook']},ensure_ascii=False))

if __name__=='__main__':main()
