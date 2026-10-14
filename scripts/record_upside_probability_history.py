#!/usr/bin/env python3
"""Append an auditable, server-persisted daily probability series.

Never infer historical daily readings from a weekly source and never coerce
missing probabilities to zero. Backfilled GitHub archive events have explicit
provenance; future entries come only from actual recomputations.
"""
from __future__ import annotations
import datetime as dt
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENGINE=ROOT/'dist/upside_probability_engine.json'
HISTORY=ROOT/'dist/upside_probability_history.json'
CLASSES=('up','flat','down')

def valid_probability(current):
    values=(current or {}).get('probabilities')
    if (current or {}).get('status')!='ok' or not isinstance(values,dict):
        return None
    try:
        result={k:float(values[k]) for k in CLASSES}
    except (KeyError,TypeError,ValueError):
        return None
    if any(not math.isfinite(x) or not 0<=x<=100 for x in result.values()):
        return None
    if abs(sum(result.values())-100)>.25:
        return None
    return {k:round(v,1) for k,v in result.items()}

def update(history, engine, now):
    if now.tzinfo is None:
        raise ValueError('UTC-aware time required')
    local=now.astimezone(dt.timezone(dt.timedelta(hours=9)))
    stamp=now.astimezone(dt.timezone.utc).isoformat()
    date=local.date().isoformat()
    result=json.loads(json.dumps(history))
    result.setdefault('version',1)
    result.setdefault('events',[])
    result.setdefault('daily',[])
    assert result['version']==1
    assert all(result['events'][i].get('source_as_of','')<=result['events'][i+1].get('source_as_of','')
               for i in range(len(result['events'])-1)), 'source-event chronology regressed'
    cur=engine.get('current') or {}
    scope=((engine.get('scope') or {}).get('market_scope_id') or '')
    if result.get('scope') not in (None,scope):
        raise ValueError('cross-market history merge refused')
    if not scope:
        raise ValueError('market scope unavailable')
    result['scope']=scope
    probs=valid_probability(cur)
    source_date=str(cur.get('as_of') or '')
    if len(source_date)!=8 or not source_date.isdigit():
        source_date=None
    if probs is None or source_date is None:
        # Preserve last-good event history, but don't invent a normal 0% sample.
        daily={'date':date,'checked_at':stamp,'status':'data_check','source_as_of':source_date,
               'probabilities':None}
    else:
        events=result['events']
        newest=events[-1] if events else None
        if newest and source_date<newest['source_as_of']:
            raise ValueError('weekly source date regressed; preserve last-good event')
        changed=not newest or newest.get('source_as_of')!=source_date or newest.get('probabilities')!=probs
        if changed:
            events.append({'source_as_of':source_date,'recorded_at':stamp,
                           'generated_at':engine.get('generated_at'),
                           'probabilities':probs,'source':cur.get('source'),
                           'model_version':engine.get('version'),'origin':'live_computation'})
        daily={'date':date,'checked_at':stamp,
               'status':'new_source_or_signal' if changed else 'source_unchanged',
               'source_as_of':source_date,'probabilities':probs}
    daily_items=result['daily']
    if daily_items and date<daily_items[-1]['date']:
        raise ValueError('daily checkpoint date regressed')
    if daily_items and daily_items[-1]['date']==date:
        daily_items[-1]=daily
    else:
        daily_items.append(daily)
    return result

def main():
    now=dt.datetime.now(dt.timezone.utc)
    old=json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else {'version':1,'events':[],'daily':[]}
    engine=json.loads(ENGINE.read_text(encoding='utf-8'))
    new=update(old,engine,now)
    if new!=old:
        HISTORY.write_text(json.dumps(new,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'recorded','daily_checkpoints':len(new['daily']),
                      'source_events':len(new['events']),
                      'date':new['daily'][-1]['date'],
                      'source_status':new['daily'][-1]['status'],
                      'source_as_of':new['daily'][-1]['source_as_of']},ensure_ascii=False))

if __name__=='__main__':
    main()
