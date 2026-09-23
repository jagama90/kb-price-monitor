#!/usr/bin/env python3
import json,urllib.request,urllib.parse,pathlib,datetime,time
R=pathlib.Path(__file__).resolve().parents[1]; M=R/'data/buy_watchlist_master.json'; O=R/'dist/kb_watchlist_history.json'
PREF={'가락금호':24,'올림픽훼밀리타운':31,'문정동 건영아파트':28,'송파파인타운 7단지':34,'송파파인타운 8단지':25,'송파파인타운 9단지':25,'송파파인타운 10단지':25,'힐스테이트e편한세상문정':25,'삼환가락':28,'가락쌍용1차':24,'잠실한솔':23,'송파더센트레':22,'송파꿈에그린위례24단지':25,'송파시그니처롯데캐슬':26,'E편한세상송파파크센트럴':25}
def fetch(cid,aid):
 q=urllib.parse.urlencode({'단지기본일련번호':cid,'면적일련번호':aid}); u='https://api.kbland.kr/land-price/price/complex/integrationChart?'+q
 req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json','Referer':f'https://kbland.kr/c/{cid}'})
 with urllib.request.urlopen(req,timeout=25) as r:return json.loads(r.read()).get('dataBody',{}).get('data')
def main():
 m=json.loads(M.read_text()); items=[]
 for x in m['items']:
  name=x.get('user_name') or x.get('kb_name') or x.get('name'); cid=x.get('complex_id')
  if not cid or not x.get('types'):continue
  target=PREF.get(name)
  def py(t): return (t.get('supply_m2') or 0)/3.3058
  candidates=x['types']; t=min(candidates,key=lambda z:abs(py(z)-(target if target else py(z)))) if target else candidates[0]
  try:d=fetch(cid,t['area_id'])
  except Exception as e: print(name,'ERR',e);continue
  if not d or not isinstance(d.get('시세'),list):continue
  series=[{'ym':r.get('기준년월'),'sale':r.get('매매일반거래가') or None,'rent':r.get('전세일반거래가') or None,'rent_ratio':r.get('전세가율')} for r in d['시세'] if r.get('기준년월') and (r.get('매매일반거래가') or r.get('전세일반거래가'))]
  items.append({'name':name,'complex_id':cid,'area_id':t['area_id'],'type_label':t.get('type_label'),'supply_pyeong':round(py(t),1),'series':series});print(name,len(series));time.sleep(.12)
 out={'source':'KB부동산 complex/integrationChart','frequency':'monthly','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'items':items}
 O.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')))
if __name__=='__main__':main()
