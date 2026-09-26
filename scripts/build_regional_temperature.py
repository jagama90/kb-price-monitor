#!/usr/bin/env python3
"""Build monthly Seoul-vs-local market temperature and breadth proxies.

Current official district breadth is collected separately. Historical breadth
uses the user's fixed watchlist KB histories and is explicitly labelled proxy.
"""
import json,pathlib,datetime,statistics,re
R=pathlib.Path(__file__).resolve().parents[1]
H=R/'dist/kb_watchlist_history.json';M=R/'data/buy_watchlist_master.json';P=R/'data_sources/reb_long_cycle.json';O=R/'dist/regional_temperature_history.json'
def pct(a,b):return None if a in (None,0) or b is None else (b/a-1)*100
def median(a):return round(statistics.median(a),3) if a else None
def main():
 h=json.loads(H.read_text());master=json.loads(M.read_text());price=json.loads(P.read_text())
 md={int(x['complex_id']):x for x in master.get('items',[]) if x.get('complex_id')}
 series={}
 for item in h.get('items',[]):
  meta=md.get(int(item.get('complex_id') or 0),{})
  rows={x['ym']:float(x['sale']) for x in item.get('series',[]) if x.get('ym') and x.get('sale') not in (None,0)}
  series[int(item['complex_id'])]={'name':item.get('name'),'district':meta.get('district'),'rows':rows}
 seoul={x['ym']:float(x['value']) for x in price.get('series',{}).get('price',[]) if x.get('ym') and x.get('value') is not None}
 months=sorted(seoul)
 out=[]
 for ym in months:
  y=int(ym[:4]);m=int(ym[4:]);q=y*12+m-1
  def shift(k):
   z=q+k;return f'{z//12:04d}{z%12+1:02d}'
  p1,p3=shift(-1),shift(-3)
  if p1 not in seoul or p3 not in seoul:continue
  seoul_m1=pct(seoul[p1],seoul[ym]);seoul_m3=pct(seoul[p3],seoul[ym])
  groups={'songpa':[],'non_songpa':[],'all_interest':[]}
  fwd={g:{3:[],6:[],12:[]} for g in groups}
  for cid,z in series.items():
   rr=z['rows']
   if ym not in rr or p3 not in rr:continue
   r3=pct(rr[p3],rr[ym])
   g='songpa' if z.get('district')=='송파구' else 'non_songpa'
   groups[g].append(r3);groups['all_interest'].append(r3)
   for horizon in (3,6,12):
    fy=shift(horizon)
    if fy in rr:
     fr=pct(rr[ym],rr[fy]);fwd[g][horizon].append(fr);fwd['all_interest'][horizon].append(fr)
  row={'ym':ym,'seoul_m1_pct':round(seoul_m1,3),'seoul_m3_pct':round(seoul_m3,3)}
  for g,vals in groups.items():
   row[g+'_n']=len(vals);row[g+'_m3_median_pct']=median(vals)
   row[g+'_breadth_up_pct']=round(100*sum(v>0 for v in vals)/len(vals),1) if vals else None
   for horizon in (3,6,12):row[f'{g}_fwd_{horizon}m_median_pct']=median(fwd[g][horizon])
  sm=row.get('songpa_m3_median_pct');nm=row.get('non_songpa_m3_median_pct')
  row['songpa_vs_seoul_gap_pp']=round(sm-seoul_m3,3) if sm is not None else None
  row['non_songpa_vs_seoul_gap_pp']=round(nm-seoul_m3,3) if nm is not None else None
  out.append(row)
 latest=out[-1] if out else {}
 payload={'status':'research_only','historical_breadth_is_watchlist_proxy':True,
  'method':'fixed watchlist KB monthly general-price histories; breadth = share with positive trailing 3m change; Seoul = R-ONE index',
  'latest':latest,'rows':out,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 O.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 print(json.dumps({'rows':len(out),'latest':latest},ensure_ascii=False))
if __name__=='__main__':main()
