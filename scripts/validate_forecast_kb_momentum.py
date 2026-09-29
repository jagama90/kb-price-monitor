#!/usr/bin/env python3
"""Validate whether live KB Seoul weekly momentum can replace stale local-price
momentum in the forecast engine after scale alignment.

Research-only. Collects historical KB Seoul weekly sale index, derives 4w/13w
momentum at each month-end, maps it onto the legacy research momentum scale,
and compares forecast ranking against forward returns. No production files are
modified.
"""
import json,pathlib,datetime,calendar,math,statistics,urllib.request,urllib.parse,concurrent.futures
R=pathlib.Path(__file__).resolve().parents[1]
TURN=R/'dist/turning_signal_research.json'
FINAL=R/'dist/final_backtest.json'
M2=R/'data_sources/ecos_m2.json'
MORT=R/'data_sources/ecos_mortgage_rate.json'
OUT=R/'dist/forecast_kb_momentum_validation.json'
BASE='https://data-api.kbland.kr/bfmstat/statusBoard/weeklyAptPrcIndx'

def clamp(x):return max(0.0,min(100.0,float(x)))
def n(v,d=0.0):
 try:return float(v)
 except:return d
def corr(a,b):
 z=[(float(x),float(y)) for x,y in zip(a,b) if x is not None and y is not None]
 if len(z)<3:return None
 ax=sum(x for x,_ in z)/len(z);ay=sum(y for _,y in z)/len(z)
 dx=sum((x-ax)**2 for x,_ in z);dy=sum((y-ay)**2 for _,y in z)
 return sum((x-ax)*(y-ay) for x,y in z)/math.sqrt(dx*dy) if dx and dy else None
def rmse(a,b):
 z=[(float(x),float(y)) for x,y in zip(a,b) if x is not None and y is not None]
 return math.sqrt(sum((x-y)**2 for x,y in z)/len(z)) if z else None
def fit_ols(xs,ys):
 z=[(float(x),float(y)) for x,y in zip(xs,ys) if x is not None and y is not None]
 if len(z)<3:return None
 ax=sum(x for x,_ in z)/len(z);ay=sum(y for _,y in z)/len(z)
 den=sum((x-ax)**2 for x,_ in z)
 b=sum((x-ax)*(y-ay) for x,y in z)/den if den else 0.0
 a=ay-b*ax
 pred=[a+b*x for x,_ in z]
 yy=[y for _,y in z];r=corr([x for x,_ in z],yy)
 return {'intercept':a,'slope':b,'r':r,'r2':None if r is None else r*r,'rmse':rmse(pred,yy),'n':len(z)}
def auc(scores,labels):
 z=[(float(s),int(y)) for s,y in zip(scores,labels) if s is not None and y is not None]
 pos=[s for s,y in z if y==1];neg=[s for s,y in z if y==0]
 if not pos or not neg:return None
 wins=0.0
 for p in pos:
  for q in neg:
   wins+=1 if p>q else .5 if p==q else 0
 return wins/(len(pos)*len(neg))
def norm(d):
 z=sum(max(0.0,v) for v in d.values()) or 1.0
 q={k:max(0.0,v)*100/z for k,v in d.items()}
 return q

def fetch(dt):
 q=urllib.parse.urlencode({'기준년월일':dt.strftime('%Y%m%d'),'법정동코드':'0000000000'})
 req=urllib.request.Request(BASE+'?'+q,headers={'User-Agent':'Mozilla/5.0','Referer':'https://data.kbland.kr/','Origin':'https://data.kbland.kr'})
 with urllib.request.urlopen(req,timeout=20) as r:data=json.load(r)
 rows=((((data or {}).get('dataBody') or {}).get('data') or {}).get('주간 매매지수') or [])
 z=next((x for x in rows if str(x.get('법정동코드'))=='1100000000' or str(x.get('지역명'))=='서울'),None)
 if not z:return None
 return {'date':str(z.get('통계기준년월일시') or ''),'value':float(z.get('현재데이터'))}

def mondays(start,end):
 d=start-datetime.timedelta(days=start.weekday())
 out=[]
 while d<=end:
  out.append(d);d+=datetime.timedelta(days=7)
 return out

def collect_weekly():
 dates=mondays(datetime.date(2022,5,2),datetime.date.today()+datetime.timedelta(days=7))
 rows=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
  futs={ex.submit(fetch,d):d for d in dates}
  for fut in concurrent.futures.as_completed(futs):
   try:
    x=fut.result()
    if x and x['date']:rows.append(x)
   except Exception:pass
 dedup={x['date']:x for x in rows}
 return sorted(dedup.values(),key=lambda x:x['date'])

def month_momentum(weekly,ym):
 y=int(ym[:4]);m=int(ym[4:]);cut=f'{ym}{calendar.monthrange(y,m)[1]:02d}'
 rows=[x for x in weekly if x['date']<=cut]
 if len(rows)<14:return None
 cur=rows[-1];p4=rows[-5];p13=rows[-14]
 return {'as_of':cur['date'],'index':cur['value'],'mom_4w_pct':(cur['value']/p4['value']-1)*100,'mom_13w_pct':(cur['value']/p13['value']-1)*100,
         'base4':p4['date'],'base13':p13['date']}

def shift(ym,nm):
 y=int(ym[:4]);m=int(ym[4:]);q=y*12+m-1+nm
 return f'{q//12:04d}{q%12+1:02d}'

def build_aux():
 m2=json.loads(M2.read_text()).get('series',[]) if M2.exists() else []
 mm={str(x.get('period','')).replace('-','')[:6]:x for x in m2 if x.get('period')}
 mort=json.loads(MORT.read_text()).get('series',[]) if MORT.exists() else []
 mr={str(x.get('period','')).replace('-','')[:6]:x for x in mort if x.get('item')=='주택담보대출'}
 return mm,mr

def forecast_weights(c,trow,m1,m3,mmrow=None,mortrow=None):
 finance=n(c.get('finance'),50);sent=n(c.get('sentiment'),50);demand=n(c.get('demand'),50);value=n(c.get('value'),50);supply=n(c.get('supply'),50)
 breadth=n(trow.get('breadth'),50);reaccel=n(trow.get('reaccel'),50)
 # Same live-engine transforms where source history is available; otherwise use
 # neutral/finance-derived values identically for both variants.
 yoy=n((mmrow or {}).get('yoy_pct'),(finance-50)/1.5 if finance else 0)
 liquidity=clamp(50+yoy*5)
 mortgage=n((mortrow or {}).get('rate_pct'),4.0)
 rate_pressure=clamp((mortgage-3.0)*28)
 # Historical demand score is already the live transform; recover only relative
 # pressure proxy from weakness so both variants share the same non-price input.
 trade_pressure=clamp(max(0,50-demand)*2)
 recent_peak=n(trow.get('recent_peak_3m_momentum_pct'),None)
 cooling=clamp(max(0,n(trow.get('_peak_m3'),m3)-max(m3,0))*6+max(0,50-breadth)*.8+max(0,50-reaccel)*.6)
 q4=norm({
  'consolidation':62+.18*finance+.14*supply+.22*clamp(100-abs(m3)*12)-.10*trade_pressure,
  'reacceleration':18+.34*reaccel+.22*breadth+.12*finance+.10*liquidity+max(0,m3)*2,
  'downturn':22+.24*(100-breadth)+.18*(100-demand)+.14*(100-sent)+.12*trade_pressure+.10*rate_pressure+.10*(100-value)-max(0,m1)*2
 })
 h1=norm({
  'consolidation':55+.16*finance+.14*supply+.16*clamp(100-cooling)+.08*liquidity,
  'reacceleration':28+.20*finance+.18*liquidity+.18*breadth+.14*reaccel+.10*sent,
  'downturn':24+.18*(100-demand)+.16*(100-sent)+.14*rate_pressure+.12*trade_pressure+.10*(100-value)-.12*liquidity
 })
 h2=norm({
  'consolidation':48+.14*finance+.12*supply+.10*clamp(100-abs(m3)*10),
  'reacceleration':34+.20*liquidity+.16*finance+.14*breadth+.10*sent,
  'downturn':26+.14*(100-demand)+.12*(100-sent)+.12*rate_pressure+.10*(100-value)-.14*liquidity+(12 if m3<0 else 0)
 })
 return q4,h1,h2

def eval_variant(rows,key):
 valid=[x for x in rows if x.get('fwd_3m_pct') is not None and x.get(key) is not None]
 s=[x[key] for x in valid];f=[x['fwd_3m_pct'] for x in valid]
 labels=[1 if x<0 else 0 for x in f]
 return {'n':len(valid),'corr_with_negative_fwd3':corr(s,[-x for x in f]),'auc_fwd3_negative':auc(s,labels),
         'mean_weight_when_fwd3_negative':statistics.mean([x[key] for x in valid if x['fwd_3m_pct']<0]) if any(x['fwd_3m_pct']<0 for x in valid) else None,
         'mean_weight_when_fwd3_nonnegative':statistics.mean([x[key] for x in valid if x['fwd_3m_pct']>=0]) if any(x['fwd_3m_pct']>=0 for x in valid) else None}

def main():
 turn=json.loads(TURN.read_text())['rows'];final=json.loads(FINAL.read_text())['rows']
 tmap={x['ym']:x for x in turn};fmap={x['ym']:x for x in final}
 weekly=collect_weekly()
 pairs=[]
 for x in turn:
  km=month_momentum(weekly,x['ym'])
  if not km:continue
  pairs.append({'ym':x['ym'],'kb4':km['mom_4w_pct'],'kb13':km['mom_13w_pct'],'old1':n(x.get('price_mom_pct')),'old3':n(x.get('momentum_3m_pct')),'as_of':km['as_of']})
 certified=[x for x in pairs if x['ym']<=json.loads(FINAL.read_text()).get('certified_through','999999')]
 fit1=fit_ols([x['kb4'] for x in certified],[x['old1'] for x in certified])
 fit3=fit_ols([x['kb13'] for x in certified],[x['old3'] for x in certified])
 # holdout: fit through 2025-12, test 2026 certified tail
 train=[x for x in certified if x['ym']<='202512'];test=[x for x in certified if x['ym']>'202512']
 h1=fit_ols([x['kb4'] for x in train],[x['old1'] for x in train]);h3=fit_ols([x['kb13'] for x in train],[x['old3'] for x in train])
 holdout={
  'n':len(test),
  'm1_rmse':rmse([h1['intercept']+h1['slope']*x['kb4'] for x in test],[x['old1'] for x in test]) if h1 and test else None,
  'm3_rmse':rmse([h3['intercept']+h3['slope']*x['kb13'] for x in test],[x['old3'] for x in test]) if h3 and test else None,
  'm1_direction_agreement':sum((h1['intercept']+h1['slope']*x['kb4']>=0)==(x['old1']>=0) for x in test)/len(test) if h1 and test else None,
  'm3_direction_agreement':sum((h3['intercept']+h3['slope']*x['kb13']>=0)==(x['old3']>=0) for x in test)/len(test) if h3 and test else None
 }
 mm,mr=build_aux()
 evalrows=[]
 histm3=[]
 for ym in sorted(set(tmap)&set(fmap)):
  tr=tmap[ym];fr=fmap[ym];km=month_momentum(weekly,ym)
  if not km:continue
  histm3.append(n(tr.get('momentum_3m_pct')))
  tr2=dict(tr);tr2['_peak_m3']=max(histm3[-6:])
  old1=n(tr.get('price_mom_pct'));old3=n(tr.get('momentum_3m_pct'))
  mapped1=fit1['intercept']+fit1['slope']*km['mom_4w_pct'] if fit1 else old1
  mapped3=fit3['intercept']+fit3['slope']*km['mom_13w_pct'] if fit3 else old3
  mk=shift(ym,-2)
  old=forecast_weights(fr['components'],tr2,old1,old3,mm.get(mk),mr.get(ym))
  new=forecast_weights(fr['components'],tr2,mapped1,mapped3,mm.get(mk),mr.get(ym))
  evalrows.append({'ym':ym,'old1':old1,'old3':old3,'kb4':km['mom_4w_pct'],'kb13':km['mom_13w_pct'],'mapped1':mapped1,'mapped3':mapped3,
                   'old_q4_down':old[0]['downturn'],'new_q4_down':new[0]['downturn'],'old_q4_reaccel':old[0]['reacceleration'],'new_q4_reaccel':new[0]['reacceleration'],
                   'fwd_3m_pct':fr.get('fwd_3m_pct'),'fwd_6m_pct':fr.get('fwd_6m_pct')})
 old_eval=eval_variant(evalrows,'old_q4_down');new_eval=eval_variant(evalrows,'new_q4_down')
 # Current live mapped values
 live=json.loads((R/'dist/market_indicators.json').read_text()).get('kb_weekly_sale_index',{}).get('momentum',{})
 live4=live.get('mom_4w_pct');live13=live.get('mom_13w_pct')
 current={'kb4':live4,'kb13':live13,
          'mapped_legacy_m1':fit1['intercept']+fit1['slope']*float(live4) if fit1 and live4 is not None else None,
          'mapped_legacy_m3':fit3['intercept']+fit3['slope']*float(live13) if fit3 and live13 is not None else None}
 # Apply only under a conservative gate: both scale relationships meaningful,
 # holdout direction mostly consistent, and downturn ranking does not degrade.
 gate=bool(fit1 and fit3 and fit1['r2']>=.35 and fit3['r2']>=.35 and holdout.get('m1_direction_agreement',0)>=.6 and holdout.get('m3_direction_agreement',0)>=.6 and
           new_eval.get('auc_fwd3_negative') is not None and old_eval.get('auc_fwd3_negative') is not None and new_eval['auc_fwd3_negative']>=old_eval['auc_fwd3_negative']-.02)
 payload={'status':'research_validation','weekly_points':len(weekly),'paired_months':len(pairs),'certified_paired_months':len(certified),
          'scale_fit':{'m1_from_kb4w':fit1,'m3_from_kb13w':fit3},'holdout_2026':holdout,
          'forecast_validation':{'original':old_eval,'kb_scale_aligned':new_eval,'auc_tolerance':-.02},
          'current_mapping':current,'apply_recommended':gate,
          'apply_gate':'R2>=0.35 both; 2026 holdout direction agreement>=60% both; 3m downturn AUC no worse than original by >0.02',
          'sample':evalrows,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 print(json.dumps({k:payload[k] for k in ('weekly_points','paired_months','certified_paired_months','scale_fit','holdout_2026','forecast_validation','current_mapping','apply_recommended')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
