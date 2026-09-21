#!/usr/bin/env python3
import json,re,urllib.request,datetime,pathlib,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
MASTER=ROOT/'data/buy_watchlist_master.json'; TARGETS=ROOT/'data/buy_watchlist_targets.json'
OUT=ROOT/'data/buy_watchlist_market.json'; DIST=ROOT/'dist/buy_watchlist_market.json'
def money(s):
 s=s.replace(',','').strip(); total=0
 m=re.search(r'(\d+(?:\.\d+)?)억',s)
 if m: total+=float(m.group(1))*10000
 m2=re.search(r'억\s*(\d+)만?',s)
 if m2: total+=float(m2.group(1))
 elif not m:
  m3=re.search(r'(\d+)만',s)
  if m3: total+=float(m3.group(1))
 return round(total) if total else None
def text(cid):
 req=urllib.request.Request(f'https://kbland.kr/se/c/{cid}',headers={'User-Agent':'Mozilla/5.0','Accept-Language':'ko-KR,ko;q=0.9'})
 with urllib.request.urlopen(req,timeout=20) as r: return r.read().decode('utf-8','ignore')
def striphtml(s):
 s=re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>',' ',s,flags=re.I)
 s=re.sub(r'<[^>]+>',' ',s); return re.sub(r'\s+',' ',s)
def parse(cid,name):
 raw=text(cid); t=striphtml(raw)
 cnt=None
 m=re.search(r'매매\s*([\d,]+)\s*전세',t)
 if m: cnt=int(m.group(1).replace(',',''))
 sec=t[t.find('시세'):t.find('전세',t.find('시세')) if t.find('전세',t.find('시세'))>0 else len(t)]
 recent=avg=None; date=None
 m=re.search(r'최근 실거래가\s*([\d억만,\.\s]+?)\s+(\d{2}\.\d{2}\.\d{2})',sec)
 if m: recent=money(m.group(1)); date=m.group(2)
 m=re.search(r'매물평균가\s*([\d억만,\.\s]+?)(?:\s|$)',sec)
 if m: avg=money(m.group(1))
 return {'complex_id':cid,'name':name,'sale_listing_count':cnt,'avg_ask_manwon':avg,'recent_trade_manwon':recent,'recent_trade_date':date}
def main():
 d=json.loads(MASTER.read_text()); old={}
 if OUT.exists():
  try: old={str(x['complex_id']):x for x in json.loads(OUT.read_text()).get('items',[])}
  except: pass
 items=[]; errors=[]
 for x in d['items']:
  cid=x.get('complex_id')
  if not cid: continue
  try:
   v=parse(cid,x.get('user_name') or x.get('kb_name')); prev=old.get(str(cid),{})
   if prev:
    if v['avg_ask_manwon'] is not None and prev.get('avg_ask_manwon') is not None:v['avg_ask_week_delta_manwon']=v['avg_ask_manwon']-prev['avg_ask_manwon']
    if v['sale_listing_count'] is not None and prev.get('sale_listing_count') is not None:v['sale_listing_week_delta']=v['sale_listing_count']-prev['sale_listing_count']
   items.append(v); time.sleep(.15)
  except Exception as e: errors.append({'complex_id':cid,'name':x.get('user_name'),'error':str(e)})
 out={'collected_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'source':'KB public complex page','items':items,'errors':errors}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)); DIST.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 print(json.dumps({'items':len(items),'errors':len(errors),'with_avg':sum(x['avg_ask_manwon'] is not None for x in items),'with_trade':sum(x['recent_trade_manwon'] is not None for x in items)},ensure_ascii=False))
 if len(items)<30: raise SystemExit(2)
if __name__=='__main__':main()
