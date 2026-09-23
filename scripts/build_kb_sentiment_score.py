#!/usr/bin/env python3
"""Normalize verified KB Seoul sentiment series into the dashboard 0-100 component."""
import json,pathlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];SRC=ROOT/'data_sources/kb_sentiment.json';OUT=ROOT/'data_sources/kb_sentiment_score.json'
def scalar(vals):
 for k,v in vals.items():
  if isinstance(v,(int,float)) and ('지수' in k or '값' in k): return float(v),k
 nums=[(k,float(v)) for k,v in vals.items() if isinstance(v,(int,float))]
 return nums[-1][1::-1] if nums else (None,None)
def main():
 d=json.loads(SRC.read_text());rows=[x for x in d.get('rows',[]) if x.get('region')=='서울']
 latest={}
 for kind in ('매수우위','매매거래활발','전세수급','전세거래활발'):
  a=sorted([x for x in rows if x.get('kind')==kind and x.get('date')],key=lambda x:x['date'])
  if a:
   v,key=scalar(a[-1].get('values') or {});latest[kind]={'date':a[-1]['date'],'value':v,'field':key}
 sale=[latest[k]['value'] for k in ('매수우위','매매거래활발') if k in latest and latest[k].get('value') is not None]
 rent=[latest[k]['value'] for k in ('전세수급','전세거래활발') if k in latest and latest[k].get('value') is not None]
 # KB indices are 0..200 with 100 neutral. Map them linearly to 0..100.
 score=round(sum(sale)/len(sale)/2,1) if len(sale)==2 else None
 jeonse_score=round(sum(rent)/len(rent)/2,1) if len(rent)==2 else None
 payload={'status':'connected' if score is not None else 'sample_only','region':'서울','latest':latest,'score_0_100':score,'jeonse_score_0_100':jeonse_score,'method':'mean(KB buyer superiority, transaction activity) / 2','source':'KB부동산 데이터허브','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2));print(json.dumps(payload,ensure_ascii=False))
 if score is None: raise SystemExit('latest Seoul sentiment scalar not resolved')
if __name__=='__main__':main()
