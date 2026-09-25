#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime,time
R=pathlib.Path(__file__).resolve().parents[1]; O=R/'dist/garak_geumho_24a_history.json'
CID=1960; AID=1847
q=urllib.parse.urlencode({'단지기본일련번호':CID,'면적일련번호':AID})
u='https://api.kbland.kr/land-price/price/complex/integrationChart?'+q
req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json','Referer':f'https://kbland.kr/c/{CID}'})
last=None
for attempt in range(3):
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            d=json.loads(r.read()).get('dataBody',{}).get('data') or {}
        series=[{'ym':x.get('기준년월'),'sale':x.get('매매일반거래가') or None,'rent':x.get('전세일반거래가') or None,'rent_ratio':x.get('전세가율')} for x in d.get('시세',[]) if x.get('기준년월') and (x.get('매매일반거래가') or x.get('전세일반거래가'))]
        if not series: raise RuntimeError('KB returned empty series')
        out={'name':'가락금호','type':'24A','complex_id':CID,'area_id':AID,'frequency':'monthly','source':'KB부동산','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'refresh_status':'live','series':series}
        O.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
        print('live rows',len(series),series[-1]);break
    except Exception as e:
        last=e; print(f'KB attempt {attempt+1}/3 failed: {e}')
        if attempt<2: time.sleep(5*(attempt+1))
else:
    if O.exists():
        old=json.loads(O.read_text())
        if old.get('series'):
            old['refresh_status']='fallback_last_good'
            old['refresh_error']=str(last)
            old['refresh_attempted_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            O.write_text(json.dumps(old,ensure_ascii=False,separators=(',',':')))
            print('KB unavailable; preserved last-good rows',len(old['series']))
        else: raise SystemExit(f'KB unavailable and fallback empty: {last}')
    else: raise SystemExit(f'KB unavailable and no fallback file: {last}')
