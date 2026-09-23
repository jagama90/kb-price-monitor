#!/usr/bin/env python3
import json,pathlib,statistics,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];SRC=ROOT/'data/seoul_snapshot.json';OUT=ROOT/'data_sources/kb_value_sample.json'
def main():
 d=json.loads(SRC.read_text());rows=[x for x in d.get('items',[]) if x.get('district')=='송파구' and x.get('min_price_manwon') is not None];vals=[float(x['min_price_manwon']) for x in rows];med=statistics.median(vals) if vals else None
 out={'status':'sample_connected' if med is not None else 'unavailable','scope':'송파구 KB 단지 최소시세 cross-section','as_of':d.get('collected_at'),'complex_count':len(rows),'median_min_price_manwon':med,'score_0_100':50 if med is not None else None,'score_status':'neutral_sample_only','note':'Historical drawdown/peak-distance is not yet available; neutral 50 is sample-only and is NOT eligible for production index contribution.','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
