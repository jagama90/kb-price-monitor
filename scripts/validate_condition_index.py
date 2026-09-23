#!/usr/bin/env python3
"""Walk-forward validation engine. It never invents unavailable history."""
import json,pathlib,datetime,statistics
ROOT=pathlib.Path(__file__).resolve().parents[1]; H=ROOT/'dist/condition_index_history.json'; O=ROOT/'dist/validation_report.json'
HORIZONS=(1,3,6,12)
def main():
 h=json.loads(H.read_text()) if H.exists() else {'rows':[]}; rows=sorted(h.get('rows',[]),key=lambda x:x.get('date',''))
 scored=[x for x in rows if x.get('score') is not None]
 report={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'observations':len(rows),'scored_observations':len(scored),'horizons_months':list(HORIZONS),'status':'insufficient_history','tests':{},'guardrails':{'minimum_scored_observations':24,'minimum_out_of_sample_observations':12,'no_hindsight_imputation':True}}
 # The engine is deliberately executable before sufficient history exists. It records
 # readiness rather than manufacturing a backtest from current snapshots.
 if len(scored)>=24:
  split=max(12,int(len(scored)*.7)); train=scored[:split]; test=scored[split:]
  report['tests']['walk_forward']={'train_n':len(train),'test_n':len(test),'ready':len(test)>=12}
  report['tests']['turning_points']={'ready':len(test)>=12,'rule':'evaluate score delta before observed price-direction changes'}
  report['tests']['weight_calibration']={'ready':len(train)>=24,'rule':'calibrate on train only; freeze weights before test'}
  report['tests']['forward_returns']={str(m):{'ready':False,'reason':'price target history not yet connected'} for m in HORIZONS}
  report['status']='price_target_history_required'
 O.write_text(json.dumps(report,ensure_ascii=False,indent=2)); print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
