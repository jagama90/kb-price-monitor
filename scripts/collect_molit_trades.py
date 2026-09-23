#!/usr/bin/env python3
import os,json,datetime,urllib.parse,urllib.request,xml.etree.ElementTree as ET,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; OUT=ROOT/'dist/market_indicators.json'
SEOUL=['11110','11140','11170','11200','11215','11230','11260','11290','11305','11320','11350','11380','11410','11440','11470','11500','11530','11545','11560','11590','11620','11650','11680','11710','11740']
def fetch(code,ym,key):
 u='https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev?'+urllib.parse.urlencode({'serviceKey':key,'LAWD_CD':code,'DEAL_YMD':ym,'numOfRows':9999,'pageNo':1},safe='%')
 return urllib.request.urlopen(u,timeout=30).read()
def main():
 key=os.getenv('MOLIT_SERVICE_KEY'); 
 if not key: raise SystemExit('MOLIT_SERVICE_KEY secret is required')
 d=json.loads(OUT.read_text()); now=datetime.date.today(); months=[]
 for back in range(0,7):
  y=now.year+(now.month-1-back)//12;m=(now.month-1-back)%12+1;months.append(f'{y:04d}{m:02d}')
 series=[];bands=[]
 for ym in reversed(months):
  prices=[]
  for code in SEOUL:
   root=ET.fromstring(fetch(code,ym,key))
   for it in root.findall('.//item'):
    s=(it.findtext('dealAmount') or it.findtext('거래금액') or '').replace(',','').strip()
    if s.isdigit(): prices.append(int(s))
  n=len(prices); cuts=[sum(p<=90000 for p in prices),sum(90000<p<=150000 for p in prices),sum(150000<p<=250000 for p in prices),sum(p>250000 for p in prices)]
  series.append([ym[:4]+'-'+ym[4:],n,ym==months[0]])
  bands.append({'period':ym[:4]+'-'+ym[4:],'total':n,'counts':{'<=9eok':cuts[0],'9-15eok':cuts[1],'15-25eok':cuts[2],'25eok+':cuts[3]},'under15_share':round((cuts[0]+cuts[1])*100/n,1) if n else None})
 d['seoul_apt_trade_count']=series;d['price_bands']={'status':'connected','source':'MOLIT apartment trade OpenAPI','months':bands};d['updated_at']=now.isoformat()
 OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
