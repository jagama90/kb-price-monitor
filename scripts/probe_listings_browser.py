#!/usr/bin/env python3
import asyncio, json, os, datetime as dt
from playwright.async_api import async_playwright

PAYLOAD={"단지기본일련번호":1947,"물건식별자":"KBM002217","이미지디렉토리":2217,"단지명":"가락쌍용(1차)","매물종별구분":"01","매물종별구분명":"아파트","재건축여부":"0","도시형생활주택여부":"0","준공년월":"1997.03","준공년수":30,"총세대수":2064,"총동수":14,"최소전용면적":"59.92","최대전용면적":"84.69","최소공급면적":"81.21","최대공급면적":"110.67","최소전용면적평":"18.1","최대전용면적평":"25.6","최소공급면적평":"24","최대공급면적평":"33","최소계약면적":"94.75","최대계약면적":"129.80","최소계약면적평":"28","최대계약면적평":"39","최소매매일반거래가":189500,"최대매매일반거래가":217500,"최소전세일반거래가":74500,"최대전세일반거래가":86500,"매매건수":410,"전세건수":51,"월세건수":30,"시세여부":"Y","시세노출사용여부":"Y","관심단지여부":"1","단지알림수신여부":"0","wgs84경도":"127.1276237","wgs84위도":"37.4956217","호실정보존재여부":"1","시군구명":"송파구","법정동명":"가락동","관심등록수":356,"50세대미만여부":"0","AI시세여부":"0","단지AI시세여부":"0","viewCount":81,"입주년월":"199611","등수":2,"이미지파일명":"MjIxNzEwMDI4NTQ1NDA=.jpg","이미지파일명_800":"MjIxNzEwMDI4NTQ1NzI=.jpg","이미지파일명_1920":"MjIxNzEwMDI4NTQ1MzE=.jpg","컨텐츠경로":"/kbstar/land/img/alian/kms/complex/photo/objctidnfr/2217/","이미지도메인URL":"https://file.kbland.kr/image","전자계약가능개수":"0","페이지번호":1,"페이지목록수":10,"중복타입":"02","정렬타입":"priceA","매물거래구분":"1","면적일련번호":"1835","전자계약여부":"0","비대면대출여부":"0","클린주택여부":"0","honeyYn":"0","건물동명":""}

async def main():
  token=os.environ['KB_AUTH_TOKEN'].removeprefix('bearer ').removeprefix('Bearer ')
  trace=os.environ.get('KB_TRACE_ID','')
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True)
    page=await browser.new_page()
    await page.goto('https://kbland.kr/se/c/1947',wait_until='domcontentloaded',timeout=60000)
    await page.wait_for_timeout(3000)
    ts=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime('%Y%m%d%H%M%S%f')[:17]
    result=await page.evaluate("""async ({payload,token,trace,ts}) => {
      const r=await fetch('https://api.kbland.kr/land-property/propList/main',{method:'POST',headers:{
        'Accept':'application/json, text/plain, */*','Content-Type':'application/json',
        'Authorization':'bearer '+token,'Timestamp':ts,'Traceid':trace,'Webservice':'1'
      },body:JSON.stringify(payload)});
      return {status:r.status,ctype:r.headers.get('content-type'),text:await r.text()};
    }""",{"payload":PAYLOAD,"token":token,"trace":trace,"ts":ts})
    print('BROWSER_STATUS',result['status'],result['ctype'],'bytes',len(result['text']))
    print(result['text'][:12000])
    if not result['text']: raise SystemExit(2)
    data=json.loads(result['text']); rows=((data.get('dataBody') or {}).get('data') or {}).get('propertyList') or []
    if not rows: raise SystemExit(3)
    x=min(rows,key=lambda z:int(z.get('매매가') or 10**12))
    print('LOWEST',x.get('매매가'),x.get('건물동명'),x.get('해당층수'),x.get('매물일련번호'))
    await browser.close()
asyncio.run(main())
