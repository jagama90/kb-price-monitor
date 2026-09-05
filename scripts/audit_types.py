#!/usr/bin/env python3
"""Cross-check area-list prices against KB's separate area detail endpoint."""
import concurrent.futures
import json
from pathlib import Path
import sys
from collect_types import ROOT,api_get,atomic_json,normalize,now

def main():
    run=Path(sys.argv[1])
    catalog=json.loads((ROOT/'data/seoul_snapshot.json').read_text())['items']
    selected=[]
    for cid,aid in [(1913,1801),(1913,171537),(15758,15498),(15758,134592)]:
        c=next(c for c in catalog if c['complex_id']==cid)
        saved=json.loads((run/f'{cid}.json').read_text())
        selected.append(next(r for r in normalize(c,saved['raw'],saved['collected_at']) if r['area_id']==aid))
    for district in sorted({c['district'] for c in catalog}):
        for c in sorted((c for c in catalog if c['district']==district),key=lambda c:c['complex_id']):
            file=run/f"{c['complex_id']}.json"
            if not file.exists():continue
            saved=json.loads(file.read_text())
            items=[r for r in normalize(c,saved['raw'],saved['collected_at']) if r['general_price_manwon'] is not None]
            if items:
                selected.append(items[-1]);break
    def check(r):
        detail=api_get('/land-price/price/BasePrcInfoNew',{'단지기본일련번호':r['complex_id'],'면적일련번호':r['area_id']})
        exact=[x for x in (detail or {}).get('시세',[]) if x.get('단지기본일련번호')==r['complex_id'] and x.get('면적일련번호')==r['area_id']]
        d=exact[0] if len(exact)==1 else {}
        ok=bool(d) and d.get('매매일반거래가')==r['general_price_manwon'] and abs(float(d.get('공급면적',0))-r['supply_m2'])<0.011
        return {'complex_id':r['complex_id'],'area_id':r['area_id'],'name':r['name'],'district':r['district'],
            'supply_pyeong':r['supply_pyeong'],'supply_m2':r['supply_m2'],'list_price':r['general_price_manwon'],
            'detail_price':d.get('매매일반거래가'),'detail_supply_m2':d.get('공급면적'),'price_date':d.get('시세기준년월일'),'matched':ok}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        checks=list(pool.map(check,selected))
    report={'checked_at':now(),'checks':checks,'passed':sum(c['matched'] for c in checks),'total':len(checks)}
    atomic_json(ROOT/'data/type_audit.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['passed']==report['total'] else 2

if __name__=='__main__':raise SystemExit(main())
