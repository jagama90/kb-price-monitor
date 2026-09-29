#!/usr/bin/env python3
"""Build a research candidate for the 20% Price/Value component.

Composite prior:
  40% income valuation (inverse PIR percentile)
  30% rent support (rent-to-sale percentile)
  30% long-run price deviation (inverse percentile of 60m log-trend gap)

Every historical month uses only observations available at or before that month.
"""
import json,pathlib,datetime,math,statistics,argparse
R=pathlib.Path(__file__).resolve().parents[1]
SRC=R/'data_sources/kb_valuation_sources.json'
OUT=R/'dist/kb_value_composite_candidate.json'
W={'pir':.40,'rent_ratio':.30,'trend_gap':.30}

def mid_pct_rank(hist,v):
    z=[float(x) for x in hist if x is not None and math.isfinite(float(x))]
    if not z:return None
    less=sum(x<v for x in z);eq=sum(x==v for x in z)
    return 100*(less+.5*eq)/len(z)

def lintrend_gap(vals):
    if len(vals)<60:return None
    w=[float(x) for x in vals[-60:]]
    if any(x<=0 for x in w):return None
    ys=[math.log(x) for x in w];xs=list(range(len(w)))
    ax=sum(xs)/len(xs);ay=sum(ys)/len(ys)
    den=sum((x-ax)**2 for x in xs)
    b=sum((x-ax)*(y-ay) for x,y in zip(xs,ys))/den if den else 0
    a=ay-b*ax
    fit=math.exp(a+b*xs[-1])
    return (w[-1]/fit-1)*100

def latest_le(series,period,key):
    rows=[x for x in series if x.get('period') and x['period']<=period and x.get(key) is not None]
    return rows[-1] if rows else None

def clamp(v,lo=15,hi=85):return max(lo,min(hi,float(v)))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--publish',action='store_true');args=ap.parse_args()
    d=json.loads(SRC.read_text())
    pir=d['pir']['series'];ratio=d['rent_to_sale_ratio']['series'];avg=d['avg_sale_price']['series']
    pvals=[];rvals=[];gaps=[];rows=[];prices=[]
    pir_unique=[]
    for a in avg:
        ym=a['period'];price=float(a['avg_sale_price_manwon']);prices.append(price)
        gap=lintrend_gap(prices)
        pr=latest_le(pir,ym,'pir');rr=latest_le(ratio,ym,'rent_to_sale_pct')
        if not pr or not rr or gap is None:continue
        # Unique quarterly PIR history through the selected vintage.
        ph=[float(x['pir']) for x in pir if x['period']<=pr['period']]
        rh=[float(x['rent_to_sale_pct']) for x in ratio if x['period']<=ym]
        # Trend-gap history is accumulated only from past/current observations.
        gaps.append(gap)
        ps=100-mid_pct_rank(ph,float(pr['pir']))
        rs=mid_pct_rank(rh,float(rr['rent_to_sale_pct']))
        gs=100-mid_pct_rank(gaps,gap)
        raw=W['pir']*ps+W['rent_ratio']*rs+W['trend_gap']*gs
        score=clamp(raw)
        rows.append({
          'ym':ym,'score_0_100':round(score,1),'raw_score_0_100':round(raw,1),
          'pir_period':pr['period'],'pir':round(float(pr['pir']),3),'pir_score':round(ps,1),
          'rent_ratio_pct':round(float(rr['rent_to_sale_pct']),2),'rent_ratio_score':round(rs,1),
          'avg_sale_price_manwon':round(price,1),'trend_gap_pct':round(gap,2),'trend_gap_score':round(gs,1)
        })
    if not rows:raise SystemExit('no composite valuation rows')
    z=rows[-1]
    out={
      'status':'research_candidate',
      'score_0_100':z['score_0_100'],
      'period':z['ym'],
      'source':'KB 서울: 아파트담보대출 PIR + 아파트 전세가율 + 아파트 평균매매가격',
      'method':'40% inverse PIR historical percentile + 30% rent-to-sale historical percentile + 30% inverse 60m log-trend-gap historical percentile; expanding-window, no future observations; composite capped 15..85',
      'weights':W,
      'components':{
        'pir':{'value':z['pir'],'period':z['pir_period'],'score_0_100':z['pir_score']},
        'rent_ratio':{'value_pct':z['rent_ratio_pct'],'period':z['ym'],'score_0_100':z['rent_ratio_score']},
        'trend_gap':{'value_pct':z['trend_gap_pct'],'avg_sale_price_manwon':z['avg_sale_price_manwon'],'period':z['ym'],'score_0_100':z['trend_gap_score'],'window_months':60}
      },
      'history':rows,
      'observations':len(rows),
      'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    published=False
    if args.publish:
        vp=R/'dist/kb_value_composite_validation.json'
        vd=json.loads(vp.read_text()) if vp.exists() else {}
        if not vd.get('apply_recommended'):
            raise SystemExit('composite valuation validation gate not passed; keep last-good production score')
        prod={
          'status':'connected','model':'kb_seoul_composite_value_v1',
          'score_0_100':out['score_0_100'],'period':out['period'],
          'source':out['source'],'method':out['method'],'weights':out['weights'],
          'components':out['components'],'observations':out['observations'],
          'validation':{
            'apply_recommended':True,'rows_compared':vd.get('rows_compared'),
            'generated_at':vd.get('generated_at')
          },
          'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        text=json.dumps(prod,ensure_ascii=False,indent=2)+'\n'
        (R/'data_sources/kb_value_score.json').write_text(text,encoding='utf-8')
        (R/'dist/kb_value_score.json').write_text(text,encoding='utf-8')
        published=True
    print(json.dumps({**{k:out[k] for k in ('score_0_100','period','components','observations')},'published':published},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
