#!/usr/bin/env python3
import os,json,datetime,urllib.parse,urllib.request,xml.etree.ElementTree as ET,pathlib,calendar,time,random
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data_sources/molit.json'; VINTAGE=ROOT/'data_sources/molit_daily_history.json'
SEOUL=['11110','11140','11170','11200','11215','11230','11260','11290','11305','11320','11350','11380','11410','11440','11470','11500','11530','11545','11560','11590','11620','11650','11680','11710','11740']
def request_page(code,ym,key,page):
 q=urllib.parse.urlencode({'serviceKey':key,'LAWD_CD':code,'DEAL_YMD':ym,'numOfRows':1000,'pageNo':page},safe='%')
 url='https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev?'+q
 last=None
 for attempt in range(5):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'kb-price-monitor/1.0'})
   return ET.fromstring(urllib.request.urlopen(req,timeout=60).read())
  except Exception as e:
   last=e
   if attempt==4: break
   time.sleep(min(20,2**attempt+random.random()))
 raise last
def item_value(it,*names):
 for n in names:
  v=it.findtext(n)
  if v is not None and str(v).strip():return str(v).strip()
 return ''
def fetch_all(code,ym,key):
 rows=[];page=1;fetched=0
 while True:
  root=request_page(code,ym,key,page);items=root.findall('.//item');fetched+=len(items)
  for it in items:
   s=item_value(it,'dealAmount','거래금액').replace(',','').strip();day=item_value(it,'dealDay','일')
   if s.isdigit():
    try:dd=int(day)
    except:dd=0
    rows.append((dd,int(s)))
  total=int(root.findtext('.//totalCount') or len(rows))
  if not items or fetched>=total:break
  page+=1
  if page>100:raise RuntimeError(f'pagination guard {code} {ym}')
 return rows
def summarize(rows):
 prices=[p for _,p in rows];n=len(prices)
 keys={'<=9eok':sum(p<=90000 for p in prices),'9-15eok':sum(90000<p<=150000 for p in prices),'15-25eok':sum(150000<p<=250000 for p in prices),'25eok+':sum(p>250000 for p in prices)}
 boundary={'13-15eok':sum(130000<p<=150000 for p in prices),'15-17eok':sum(150000<p<=170000 for p in prices),'23-25eok':sum(230000<p<=250000 for p in prices),'25-27eok':sum(250000<p<=270000 for p in prices)}
 return {'total':n,'counts':keys,'boundary_counts':boundary,'under15_share':round((keys['<=9eok']+keys['9-15eok'])*100/n,1) if n else None}
def shift_month(d,delta):
 y=d.year+(d.month-1+delta)//12;m=(d.month-1+delta)%12+1;return y,m
def main():
 key=os.getenv('MOLIT_SERVICE_KEY')
 if not key:raise SystemExit('MOLIT_SERVICE_KEY secret is required')
 OUT.parent.mkdir(exist_ok=True);now=datetime.datetime.now(ZoneInfo('Asia/Seoul')).date();months=[]
 for back in range(7):
  y,m=shift_month(now,-back);months.append(f'{y:04d}{m:02d}')
 monthly={};series=[];bands=[]
 for ym in reversed(months):
  rows=[]
  for code in SEOUL:rows.extend(fetch_all(code,ym,key))
  monthly[ym]=rows;sm=summarize(rows);series.append([ym[:4]+'-'+ym[4:],sm['total'],ym==months[0]]);bands.append({'period':ym[:4]+'-'+ym[4:],**sm})
 cy,cm=now.year,now.month;py,pm=shift_month(now,-1);cutoff=min(now.day,calendar.monthrange(py,pm)[1]);cur=f'{cy:04d}{cm:02d}';prev=f'{py:04d}{pm:02d}'
 cs=summarize([r for r in monthly.get(cur,[]) if 1<=r[0]<=cutoff]);ps=summarize([r for r in monthly.get(prev,[]) if 1<=r[0]<=cutoff])
 pct=lambda a,b:round((a/b-1)*100,1) if b else None
 matched={'as_of':now.isoformat(),'cutoff_day':cutoff,'basis':'contract_date_equal_calendar_days','current':{'period':f'{cy:04d}-{cm:02d}','range':f'1~{cutoff}일',**cs},'previous':{'period':f'{py:04d}-{pm:02d}','range':f'1~{cutoff}일',**ps},'changes':{'trade_count_pct':pct(cs['total'],ps['total']),'under15_share_pp':round(cs['under15_share']-ps['under15_share'],1) if cs['under15_share'] is not None and ps['under15_share'] is not None else None},'warning':'당월은 계약 후 신고가 추가될 수 있어 조기신호로 사용'}
 out={'source':'MOLIT apartment trade OpenAPI','collected_at':datetime.datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),'seoul_apt_trade_count':series,'price_bands':{'status':'connected','months':bands},'matched_period':matched}
 OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2))
 history=json.loads(VINTAGE.read_text()) if VINTAGE.exists() else {'snapshots':[]};history['snapshots']=[x for x in history.get('snapshots',[]) if x.get('as_of')!=now.isoformat()];history['snapshots'].append({'as_of':now.isoformat(),'matched_period':matched,'current_month':bands[-1]});history['snapshots']=history['snapshots'][-400:];VINTAGE.write_text(json.dumps(history,ensure_ascii=False,indent=2))
 print(json.dumps({'collector':'MOLIT','months':len(months),'latest_total':bands[-1]['total'],'matched':matched['changes']},ensure_ascii=False))
if __name__=='__main__':main()
