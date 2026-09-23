#!/usr/bin/env python3
import os,json,datetime,urllib.parse,urllib.request,xml.etree.ElementTree as ET,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'dist/market_indicators.json'
SEOUL=['11110','11140','11170','11200','11215','11230','11260','11290','11305','11320','11350','11380','11410','11440','11470','11500','11530','11545','11560','11590','11620','11650','11680','11710','11740']
def fetch(code,ym,key):
 u='https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev?'+urllib.parse.urlencode({'serviceKey':key,'LAWD_CD':code,'DEAL_YMD':ym,'numOfRows':9999,'pageNo':1},safe='%')
 return urllib.request.urlopen(u,timeout=30).read()
def item_value(it,*names):
 for n in names:
  v=it.findtext(n)
  if v is not None and str(v).strip(): return str(v).strip()
 return ''
def summarize(rows):
 prices=[p for _,p in rows];n=len(prices)
 cuts=[sum(p<=90000 for p in prices),sum(90000<p<=150000 for p in prices),sum(150000<p<=250000 for p in prices),sum(p>250000 for p in prices)]
 return {'total':n,'counts':{'<=9eok':cuts[0],'9-15eok':cuts[1],'15-25eok':cuts[2],'25eok+':cuts[3]},'under15_share':round((cuts[0]+cuts[1])*100/n,1) if n else None}
def shift_month(d,delta):
 y=d.year+(d.month-1+delta)//12;m=(d.month-1+delta)%12+1
 return y,m
def main():
 key=os.getenv('MOLIT_SERVICE_KEY')
 if not key: raise SystemExit('MOLIT_SERVICE_KEY secret is required')
 d=json.loads(OUT.read_text());now=datetime.date.today();months=[]
 for back in range(0,7):
  y,m=shift_month(now,-back);months.append(f'{y:04d}{m:02d}')
 monthly={};series=[];bands=[]
 for ym in reversed(months):
  rows=[]
  for code in SEOUL:
   root=ET.fromstring(fetch(code,ym,key))
   for it in root.findall('.//item'):
    s=item_value(it,'dealAmount','거래금액').replace(',','').strip()
    day=item_value(it,'dealDay','일')
    if s.isdigit():
     try: dd=int(day)
     except: dd=0
     rows.append((dd,int(s)))
  monthly[ym]=rows;sm=summarize(rows)
  series.append([ym[:4]+'-'+ym[4:],sm['total'],ym==months[0]])
  bands.append({'period':ym[:4]+'-'+ym[4:],**sm})
 # Equal-calendar-day comparison is an early signal, not a cure for reporting lag:
 # current-month contracts can still be reported for up to 30 days. We retain this
 # explicitly in metadata and build daily vintages from each collection onward.
 cy,cm=now.year,now.month;py,pm=shift_month(now,-1);cutoff=now.day
 cur=f'{cy:04d}{cm:02d}';prev=f'{py:04d}{pm:02d}'
 cur_rows=[r for r in monthly.get(cur,[]) if 1<=r[0]<=cutoff]
 prev_rows=[r for r in monthly.get(prev,[]) if 1<=r[0]<=cutoff]
 cs,ps=summarize(cur_rows),summarize(prev_rows)
 def pct(a,b): return round((a/b-1)*100,1) if b else None
 matched={'as_of':now.isoformat(),'cutoff_day':cutoff,'basis':'contract_date_equal_calendar_days','current':{'period':f'{cy:04d}-{cm:02d}','range':f'1~{cutoff}일',**cs},'previous':{'period':f'{py:04d}-{pm:02d}','range':f'1~{cutoff}일',**ps},'changes':{'trade_count_pct':pct(cs['total'],ps['total']),'under15_share_pp':round(cs['under15_share']-ps['under15_share'],1) if cs['under15_share'] is not None and ps['under15_share'] is not None else None},'warning':'동일 계약일 구간 비교도 당월은 계약 후 30일 이내 신고가 추가될 수 있어 과소집계될 수 있음. 방향성 조기 신호로 사용.'}
 d['seoul_apt_trade_count']=series
 d['price_bands']={'status':'connected','source':'MOLIT apartment trade OpenAPI','months':bands}
 d['matched_period']=matched
 d['updated_at']=now.isoformat()
 OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2))
 print(json.dumps({'collector':'MOLIT','months':len(months),'matched_period':matched},ensure_ascii=False))
if __name__=='__main__':main()
