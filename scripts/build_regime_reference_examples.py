#!/usr/bin/env python3
import json,pathlib,datetime
R=pathlib.Path(__file__).resolve().parents[1]
SRC=R/'dist/turning_signal_research.json';OUT=R/'dist/regime_reference_examples.json'
LABELS=['하락','둔화','바닥','상승·보합','가속']
DESC=[
 '월간·3개월 가격 모멘텀이 함께 음수이고 반전 신호도 약했던 구간입니다.',
 '가격은 계속 내렸지만 하락 속도가 둔화되고 반전 점수가 올라오기 시작한 구간입니다.',
 '월간 가격이 멈추거나 플러스로 돌아서며 하락 종료를 확인하던 구간입니다.',
 '앞선 상승 뒤 3개월 모멘텀이 0% 부근으로 식으며 가격이 쉬어가던 구간입니다.',
 '가격 모멘텀과 시장 확산·재가속 신호가 동시에 강했던 구간입니다.'
]
def addm(ym,d):
 y=int(ym[:4]);m=int(ym[4:])+d
 while m>12:y+=1;m-=12
 while m<1:y-=1;m+=12
 return f'{y:04d}{m:02d}'
def classify(rows,i):
 x=rows[i];recent=rows[max(0,i-3):i];was=any(float(r.get('momentum_3m_pct') or 0)>0 for r in recent)
 m1=float(x.get('price_mom_pct') or 0);m3=float(x.get('momentum_3m_pct') or 0);s=0
 if x.get('bottom_zone'):s=1
 if m1>=0 and m3<=0 and not was:s=2
 if m3>0:s=3
 if was and m3<=0 and m1>=0:s=3
 if x.get('momentum_zone'):s=4
 return s,was
def score(x):
 m1=float(x.get('price_mom_pct') or 0);m3=float(x.get('momentum_3m_pct') or 0);acc=float(x.get('price_accel_pp') or 0)
 turn=float(x.get('turn') or 0);setup=float(x.get('setup') or 0);breadth=float(x.get('breadth') or 0);rea=float(x.get('reaccel') or 0);s=x['stage']
 if s==0:return max(0,-m1)*12+max(0,-m3)*4+(100-turn)*.15
 if s==1:return max(0,acc)*10+turn*.5+setup*.25+max(0,-m3)*1.5
 if s==2:return turn*.55+setup*.35-abs(m1)*4-abs(m3)*2+(20 if m1>0 and m3<0 else 0)
 if s==3:return (100 if x['was_rising'] and m3<=0 and m1>=0 else 0)+(100-min(100,rea))*.15+(100-min(100,breadth))*.1-abs(m1)*2
 return rea*.45+breadth*.3+max(0,m3)*2+max(0,m1)*2
def main():
 d=json.loads(SRC.read_text());rows=d.get('rows') or []
 for i,x in enumerate(rows):
  x['stage'],x['was_rising']=classify(rows,i);x['_i']=i
 cutoff=addm(rows[-1]['ym'],-9)
 eligible=[x for x in rows if not x.get('source_provisional') and x['ym']<=cutoff]
 pick=lambda a:max(a,key=score)
 decline=pick([x for x in eligible if x['stage']==0])
 def within(stage,after,n):
  a=[x for x in eligible if x['stage']==stage and after<x['ym']<=addm(after,n)]
  return pick(a) if a else pick([x for x in eligible if x['stage']==stage and x['ym']>after])
 slow=within(1,decline['ym'],4);bottom=within(2,slow['ym'],4)
 a=[x for x in eligible if x['stage']==3 and x['ym']>bottom['ym'] and x['was_rising'] and float(x.get('momentum_3m_pct') or 0)<=0 and float(x.get('price_mom_pct') or 0)>=0]
 flat=pick(a or [x for x in eligible if x['stage']==3 and x['ym']>bottom['ym']])
 accel=pick([x for x in eligible if x['stage']==4 and x['ym']>flat['ym']])
 refs=[]
 for idx,x in enumerate([decline,slow,bottom,flat,accel]):
  a=b=x['_i']
  while a>0 and rows[a-1]['stage']==x['stage'] and b-a<4:a-=1
  while b<len(rows)-1 and rows[b+1]['stage']==x['stage'] and b-a<4:b+=1
  seg=rows[a:b+1];p0=seg[0].get('target_price');p1=seg[-1].get('target_price')
  refs.append({'stage':idx,'label':LABELS[idx],'anchor_ym':x['ym'],'period_start':seg[0]['ym'],'period_end':seg[-1]['ym'],'months':len(seg),'description':DESC[idx],
   'market_state':round(float(x.get('market_state') or 0),1),'price_mom_1m_pct':round(float(x.get('price_mom_pct') or 0),2),'price_mom_3m_pct':round(float(x.get('momentum_3m_pct') or 0),2),
   'breadth_0_100':round(float(x.get('breadth') or 0),1),'reaccel_0_100':round(float(x.get('reaccel') or 0),1),'turn_0_100':round(float(x.get('turn') or 0),1),
   'period_price_change_pct':round((p1/p0-1)*100,2) if p0 and p1 else None,
   'series':[{'ym':z['ym'],'price':z.get('target_price'),'price_mom_1m_pct':z.get('price_mom_pct'),'price_mom_3m_pct':z.get('momentum_3m_pct')} for z in seg]})
 payload={'status':'research_reference','source':'dist/turning_signal_research.json','classification_rule':'same five-stage rule as renderCycleStage; retrospective representative examples only',
  'selection_rule':'exclude latest 9 months; strongest decline, then strongest subsequent slowdown and bottom within 4 months, strongest post-rally consolidation, strongest later acceleration',
  'latest_source_month':rows[-1]['ym'],'candidate_cutoff':cutoff,'references':refs,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'cutoff':cutoff,'references':[(x['label'],x['period_start'],x['period_end'],x['anchor_ym']) for x in refs]},ensure_ascii=False))
if __name__=='__main__':main()
