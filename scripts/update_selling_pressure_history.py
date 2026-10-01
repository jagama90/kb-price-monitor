#!/usr/bin/env python3
import datetime,json,pathlib,statistics
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'data/buy_watchlist_market.json'
OUT=ROOT/'data_sources/watchlist_selling_pressure_history.json'
def f(v):
 try:return float(v)
 except:return None
def make_snapshot(raw):
 items=raw.get('items') or [];listing=[];ask=[];trade=[];listing_delta=[];ask_delta=[];gaps=[];paired=[];statuses={};dates=[]
 for x in items:
  lc=f(x.get('sale_listing_count'));a=f(x.get('avg_ask_manwon'));t=f(x.get('recent_trade_manwon'));ld=f(x.get('sale_listing_week_delta'));ad=f(x.get('avg_ask_week_delta_manwon'))
  if lc is not None:listing.append(lc)
  if a is not None:ask.append(a)
  if t is not None:trade.append(t)
  if ld is not None:listing_delta.append(ld)
  if ad is not None:ask_delta.append(ad)
  if a is not None and t not in (None,0):gaps.append((a/t-1)*100)
  if ld is not None and ad is not None:paired.append((ld,ad))
  st=str(x.get('listing_refresh_status') or 'unknown');statuses[st]=statuses.get(st,0)+1
  dt=str(x.get('listing_collected_at') or '')
  if dt:dates.append(dt[:10])
 n=len(items);as_of=max(dates) if dates else str(raw.get('collected_at') or datetime.date.today().isoformat())[:10]
 return {'as_of':as_of,'configured_items':n,'listing_observed_rows':len(listing),'listing_coverage_pct':round(100*len(listing)/n,1) if n else None,
  'ask_observed_rows':len(ask),'trade_matched_rows':len(trade),'listing_delta_rows':len(listing_delta),'ask_delta_rows':len(ask_delta),
  'listing_increase_share_pct':round(100*sum(x>0 for x in listing_delta)/len(listing_delta),1) if listing_delta else None,
  'listing_decrease_share_pct':round(100*sum(x<0 for x in listing_delta)/len(listing_delta),1) if listing_delta else None,
  'median_listing_week_delta':round(statistics.median(listing_delta),2) if listing_delta else None,
  'ask_cut_share_pct':round(100*sum(x<0 for x in ask_delta)/len(ask_delta),1) if ask_delta else None,
  'median_ask_week_delta_manwon':round(statistics.median(ask_delta),1) if ask_delta else None,
  'listing_up_and_ask_down_share_pct':round(100*sum(ld>0 and ad<0 for ld,ad in paired)/len(paired),1) if paired else None,
  'median_ask_vs_recent_trade_gap_pct':round(statistics.median(gaps),2) if gaps else None,
  'listing_source_status':statuses,'representative_market_sample':False,
  'sample_definition':'configured watchlist target types; not a probability sample of the active market',
  'forced_selling':{'status':'not_observable','reason':'seller leverage, delinquency, insolvency, and sale motive are absent from the source; no forced-sale identity is inferred'}}
def main():
 raw=json.loads(SRC.read_text(encoding='utf-8'));cur=make_snapshot(raw)
 try:old=json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
 except Exception:old={}
 hist={str(x.get('as_of')):x for x in (old.get('snapshots') or []) if x.get('as_of')};hist[cur['as_of']]=cur
 snaps=[hist[k] for k in sorted(hist)][-180:]
 out={'version':1,'status':'connected_local_context','source':'KB public complex page + MOLIT recent trade for configured watchlist',
      'representative_market_sample':False,'snapshots':snaps,'latest':cur,
      'history_validation':{'available_snapshots':len(snaps),'minimum_for_time_series_research':12,'sufficient':len(snaps)>=12},
      'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 OUT.parent.mkdir(exist_ok=True);OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':out['status'],'as_of':cur['as_of'],'coverage':cur['listing_coverage_pct'],'history':len(snaps)},ensure_ascii=False))
if __name__=='__main__':main()
