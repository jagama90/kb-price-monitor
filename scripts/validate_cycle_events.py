#!/usr/bin/env python3
"""Event-study validation of price-only bottom signals across completed drawdown cycles.\nTrigger event-study run.\n"""
import json,pathlib,statistics
R=pathlib.Path(__file__).resolve().parents[1]; OUT=R/'dist/long_cycle_event_validation.json'
def pct(a,b): return (a/b-1)*100 if b else None
def ym_index(ym): return int(ym[:4])*12+int(ym[4:])-1
def main():
 rows=json.loads((R/'dist/long_cycle_master.json').read_text())['rows']
 P=[float(x['price']['value']) for x in rows]; Y=[x['ym'] for x in rows]
 # trailing-only signal already validated: 3m <= 0 and 1m >= 0
 sig=[False]*len(rows)
 for i in range(3,len(rows)): sig[i]=pct(P[i],P[i-3])<=0 and pct(P[i],P[i-1])>=0
 # Completed peak-to-trough cycles: running peak -> >=2% drawdown -> recovery to prior peak.
 cycles=[]; peak=0; i=1
 while i<len(P):
  if P[i]>=P[peak]: peak=i; i+=1; continue
  dd=pct(P[i],P[peak])
  if dd>-2: i+=1; continue
  j=i
  while j+1<len(P) and P[j+1]<P[peak]: j+=1
  if j+1>=len(P): break
  rec=j+1; trough=min(range(peak,rec+1),key=lambda k:P[k])
  ss=[k for k in range(peak+1,rec+1) if sig[k]]
  first=ss[0] if ss else None
  if first is not None:
   post_end=min(len(P)-1,first+12); post_min=min(P[first:post_end+1])
   maxdd=pct(post_min,P[first])
   entry_vs_bottom=pct(P[first],P[trough])
   lead=ym_index(Y[first])-ym_index(Y[trough])
  else: maxdd=entry_vs_bottom=lead=None
  cycles.append({'peak_ym':Y[peak],'trough_ym':Y[trough],'recovery_ym':Y[rec],
   'cycle_drawdown_pct':round(pct(P[trough],P[peak]),2),'signal_ym':Y[first] if first is not None else None,
   'signal_vs_trough_months':lead,'entry_premium_to_trough_pct':round(entry_vs_bottom,2) if entry_vs_bottom is not None else None,
   'max_drawdown_after_signal_12m_pct':round(maxdd,2) if maxdd is not None else None,
   'signal_before_or_at_trough': bool(first is not None and first<=trough)})
  peak=rec; i=rec+1
 hit=[x for x in cycles if x['signal_ym']]
 def av(key):
  v=[x[key] for x in hit if x[key] is not None]; return round(sum(v)/len(v),2) if v else None
 summary={'completed_cycles':len(cycles),'cycles_with_signal':len(hit),'coverage_pct':round(100*len(hit)/len(cycles),1) if cycles else None,
  'signals_before_or_at_trough':sum(x['signal_before_or_at_trough'] for x in hit),
  'avg_signal_vs_trough_months':av('signal_vs_trough_months'),
  'avg_entry_premium_to_trough_pct':av('entry_premium_to_trough_pct'),
  'avg_max_drawdown_after_signal_12m_pct':av('max_drawdown_after_signal_12m_pct')}
 OUT.write_text(json.dumps({'status':'research_only','no_future_leakage':True,
  'cycle_definition':'completed running-peak drawdown >=2%, ending when prior peak is recovered',
  'signal_rule':'price m3<=0 and m1>=0; uses t and earlier only','summary':summary,'cycles':cycles},ensure_ascii=False,indent=2))
 print(json.dumps({'summary':summary,'cycles':cycles},ensure_ascii=False))
if __name__=='__main__': main()
