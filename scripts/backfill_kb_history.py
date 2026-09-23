#!/usr/bin/env python3
"""Probe KB's own complex page for its public historical-price download.
No synthetic history is emitted. The status file records which watchlist complexes
expose the official download control; automated bytes are only published after a
stable, verifiable download endpoint is discovered.
"""
import pathlib,json,urllib.request,re,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];MASTER=ROOT/'data/buy_watchlist_master.json';OUT=ROOT/'data_sources/kb_history_status.json'
def main():
 m=json.loads(MASTER.read_text());found=[];errors=[]
 for x in m.get('items',[]):
  cid=x.get('complex_id')
  if not cid: continue
  try:
   req=urllib.request.Request(f'https://kbland.kr/c/{cid}',headers={'User-Agent':'Mozilla/5.0'})
   html=urllib.request.urlopen(req,timeout=15).read().decode('utf-8','ignore')
   if 'KB시세 다운로드' in html or '과거 KB시세 보기' in html: found.append({'complex_id':cid,'name':x.get('user_name') or x.get('kb_name'),'page':f'https://kbland.kr/c/{cid}'})
  except Exception as e: errors.append({'complex_id':cid,'error':str(e)[:120]})
 OUT.parent.mkdir(exist_ok=True)
 status={'status':'official_ui_verified_endpoint_pending','requested_years':3,'verified_download_ui_count':len(found),'watchlist_count':len(m.get('items',[])),'verified_pages':found,'errors':errors,'reason':'KB complex pages expose 과거 KB시세 보기/KB시세 다운로드, but a stable public file endpoint is not yet verified. No synthetic backfill is used.','collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.write_text(json.dumps(status,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in status.items() if k not in ('verified_pages','errors')},ensure_ascii=False))
if __name__=='__main__':main()
