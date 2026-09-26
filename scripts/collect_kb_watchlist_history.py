#!/usr/bin/env python3
"""Collect monthly KB histories for the exact representative watchlist areas.

The representative area is intentionally identical to merge_watchlist_details.py:
within each user target group, choose the type with the largest household count.
Per-complex last-good history is preserved only when the area_id still matches.
"""
import json,urllib.request,urllib.parse,pathlib,datetime,time,re
R=pathlib.Path(__file__).resolve().parents[1]
M=R/'data/buy_watchlist_master.json'
T=R/'data/buy_watchlist_targets.json'
O=R/'dist/kb_watchlist_history.json'

def norm(s):
    return re.sub(r'[^0-9A-Za-z가-힣]','',str(s or '')).replace('아파트','').lower()

def pyeong(t):
    m=re.search(r'\d+(?:\.\d+)?',str(t.get('type_label') or ''))
    return float(m.group()) if m else None

def allowed_types(c,t):
    types=c.get('types') or []
    aids={int(x) for x in (t.get('area_ids') or []) if x}
    if aids:return [x for x in types if int(x.get('area_id') or 0) in aids]
    lo,hi=t.get('min_pyeong'),t.get('max_pyeong')
    if lo is None and hi is None:return types
    out=[]
    for x in types:
        py=pyeong(x)
        if py is not None and (lo is None or py>=float(lo)) and (hi is None or py<=float(hi)):out.append(x)
    return out

def fetch(cid,aid):
    q=urllib.parse.urlencode({'단지기본일련번호':cid,'면적일련번호':aid})
    u='https://api.kbland.kr/land-price/price/complex/integrationChart?'+q
    req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json','Referer':f'https://kbland.kr/c/{cid}'})
    with urllib.request.urlopen(req,timeout=25) as r:
        return json.loads(r.read()).get('dataBody',{}).get('data')

def main():
    master=json.loads(M.read_text(encoding='utf-8'))
    targets=json.loads(T.read_text(encoding='utf-8')).get('items',[])
    try:old=json.loads(O.read_text(encoding='utf-8')) if O.exists() else {}
    except Exception:old={}
    old_idx={int(x.get('complex_id')):x for x in old.get('items',[]) if x.get('complex_id')}
    masters=master.get('items') or []
    by_name={norm(x.get('user_name')):x for x in masters}
    by_kb={norm(x.get('kb_name')):x for x in masters if x.get('kb_name')}
    attempted=datetime.datetime.now(datetime.timezone.utc).isoformat()
    items=[];errors=[];unresolved=[];live=fallback=0

    for target in targets:
        c=by_name.get(norm(target.get('name'))) or by_kb.get(norm(target.get('name')))
        if not c or not c.get('complex_id'):
            if not (c and c.get('status') in ('confirmed_preoccupancy','preoccupancy')):
                unresolved.append(target.get('name'))
            continue
        types=allowed_types(c,target)
        if not types:
            unresolved.append(target.get('name'))
            continue
        typ=max(types,key=lambda x:(int(x.get('type_households') or 0),-int(x.get('area_id') or 0)))
        cid=int(c['complex_id']);aid=int(typ['area_id'])
        name=c.get('user_name') or c.get('kb_name') or target.get('name')
        try:
            d=fetch(cid,aid)
            if not d or not isinstance(d.get('시세'),list):raise RuntimeError('KB returned no monthly history')
            series=[{'ym':r.get('기준년월'),'sale':r.get('매매일반거래가') or None,'rent':r.get('전세일반거래가') or None,'rent_ratio':r.get('전세가율')}
                    for r in d['시세'] if r.get('기준년월') and (r.get('매매일반거래가') or r.get('전세일반거래가'))]
            if not series:raise RuntimeError('KB returned empty usable series')
            items.append({'name':name,'complex_id':cid,'area_id':aid,'type_label':typ.get('type_label'),
                          'supply_pyeong':round(float(typ.get('supply_m2') or 0)/3.3058,1) if typ.get('supply_m2') else None,
                          'refresh_status':'live','refresh_attempted_at':attempted,'series':series})
            live+=1
        except Exception as e:
            prev=old_idx.get(cid)
            if prev and int(prev.get('area_id') or 0)==aid and prev.get('series'):
                keep=dict(prev);keep['refresh_status']='fallback_last_good';keep['refresh_attempted_at']=attempted;keep['refresh_error']=str(e)
                items.append(keep);fallback+=1
            else:
                errors.append({'name':name,'complex_id':cid,'area_id':aid,'error':str(e)})
        time.sleep(.12)

    expected=live+fallback+len(errors)
    status='connected' if not errors and fallback==0 else ('partial_last_good' if not errors else 'partial')
    out={'source':'KB부동산 complex/integrationChart','frequency':'monthly','selection':'same representative target area as watchlist market',
         'generated_at':attempted,'refresh_status':status,'live_rows':live,'fallback_rows':fallback,
         'expected_rows':expected,'unresolved_targets':unresolved,'errors':errors,'items':items}
    O.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps({'status':status,'items':len(items),'live':live,'fallback':fallback,'errors':len(errors),'unresolved':unresolved},ensure_ascii=False))
    if errors:raise SystemExit('KB watchlist history has unresolved rows without same-area last-good fallback')

if __name__=='__main__':main()
