#!/usr/bin/env python3
"""Build a plain-language market interpretation layer from existing validated signals.

This layer does not create a new market score and does not alter the production
judgment/forecast formulas. It translates already-existing current-state,
confirmation, 3-month component changes and forecast context into easier labels.
"""
from __future__ import annotations
import json, pathlib, datetime

R=pathlib.Path(__file__).resolve().parents[1]
J=R/'dist/market_judgment.json'
T=R/'dist/turning_signal_research.json'
O=R/'dist/market_interpretation.json'

def safe_num(v):
    return float(v) if isinstance(v,(int,float)) else None

def mean(xs):
    return round(sum(xs)/len(xs),2) if xs else None

def pct_pos(xs):
    return round(100*sum(v>0 for v in xs)/len(xs),1) if xs else None

def current_payload(j):
    fl=j.get('feature_layer') or {}
    state=(j.get('heads') or {}).get('current_state') or {}
    forecast=(j.get('heads') or {}).get('forward_scenario') or {}
    ev=state.get('evidence') or {}
    confirmation=state.get('confirmation') or {}
    live=((fl.get('signal_policy') or {}).get('live_recomputed_candidate') or {})
    deltas=live.get('deltas') or {}
    f3={k:safe_num(deltas.get(k+'_3m')) for k in ('finance','sentiment','demand')}
    available=[v for v in f3.values() if v is not None]
    if len(available)<2:
        data_voice='확인 중'
    elif all(v<0 for v in available):
        data_voice='약화 쪽으로 모임'
    elif all(v>0 for v in available):
        data_voice='개선 쪽으로 모임'
    else:
        data_voice='서로 엇갈림'

    m1=safe_num(ev.get('m1_pct')); m3=safe_num(ev.get('m3_pct'))
    label=str(state.get('label') or '')
    if m1 is not None and m3 is not None and m1>0 and m3>0:
        flow='상승 유지'
    elif m1 is not None and m3 is not None and m1<0 and m3<0:
        flow='하락 흐름'
    elif '바닥' in label:
        flow='바닥 확인 중'
    elif '둔화' in label:
        flow='둔화 진행'
    else:
        flow=label or '확인 중'

    cstatus=str(confirmation.get('status') or '')
    if cstatus=='strong':
        strength='강함'
    elif cstatus=='weak':
        strength='약함'
    else:
        bp=confirmation.get('breadth_pass'); rp=confirmation.get('reaccel_pass')
        strength='보통' if bp is not None or rp is not None else '확인 중'

    horizons=forecast.get('horizons') or []
    h0=horizons[0] if horizons else {}
    headline=((h0.get('display') or {}).get('headline') or '')
    if flow=='상승 유지':
        if strength=='약함' and ('하방' in headline or '혼조' in headline or data_voice=='약화 쪽으로 모임'):
            turn='둔화 쪽 조짐 있음'
        elif strength=='강함' and data_voice!='약화 쪽으로 모임':
            turn='아직 뚜렷하지 않음'
        else:
            turn='조금 더 확인 필요'
    elif flow=='하락 흐름':
        if strength=='약함' and data_voice=='개선 쪽으로 모임':
            turn='반등 쪽 조짐 있음'
        else:
            turn='아직 뚜렷하지 않음'
    else:
        turn='조금 더 확인 필요'

    if flow=='상승 유지' and strength=='약함':
        if data_voice=='약화 쪽으로 모임':
            summary='가격은 오르고 있지만 시장 전체로 퍼지는 힘은 약합니다. 금융·심리·거래가 3개월 전보다 함께 약해져, 지금은 추가 상승보다 상승 둔화 여부를 먼저 확인할 구간입니다.'
        else:
            summary='가격 상승은 이어지고 있지만 확산과 재가속 확인은 약합니다. 상승이 더 넓게 퍼지는지 확인이 필요한 구간입니다.'
    elif flow=='상승 유지' and strength=='강함':
        summary='가격 상승과 시장 확산·재가속이 함께 확인됩니다. 현재 상승 흐름의 힘은 비교적 탄탄합니다.'
    elif flow=='하락 흐름':
        summary='가격 흐름이 약한 상태입니다. 금융·심리·거래가 함께 개선되는지 확인해야 방향 전환 가능성을 높게 볼 수 있습니다.'
    else:
        summary='현재 가격 흐름과 주변 신호를 함께 확인하는 구간입니다. 한 가지 원자료보다 여러 신호의 방향을 같이 보는 것이 중요합니다.'

    reasons=[
      {'label':'가격','value':('상승' if (m1 is not None and m1>0) else '하락' if (m1 is not None and m1<0) else '보합'), 'detail':f"1개월 {m1:+.2f}% · 3개월 {m3:+.2f}%" if m1 is not None and m3 is not None else '확인 중'},
      {'label':'시장 확산','value':('충분' if confirmation.get('breadth_pass') is True else '부족' if confirmation.get('breadth_pass') is False else '확인 중'), 'detail':f"breadth {safe_num(ev.get('breadth')):.1f}" if safe_num(ev.get('breadth')) is not None else '확인 중'},
      {'label':'재가속','value':('확인' if confirmation.get('reaccel_pass') is True else '미확인' if confirmation.get('reaccel_pass') is False else '확인 중'), 'detail':f"reaccel {safe_num(ev.get('reaccel')):.1f}" if safe_num(ev.get('reaccel')) is not None else '확인 중'},
      {'label':'금융·심리·거래','value':data_voice, 'detail':' / '.join(f"{k} {v:+.1f}" for k,v in [('금융',f3['finance']),('심리',f3['sentiment']),('거래',f3['demand'])] if v is not None) or '확인 중'}
    ]
    return {
      'as_of':j.get('as_of'),
      'snapshot_id':fl.get('snapshot_id'),
      'flow':flow,
      'strength':strength,
      'turn_sign':turn,
      'data_voice':data_voice,
      'summary':summary,
      'reasons':reasons,
      'source_labels':{
        'strength':'기존 현재국면 확인 기준(breadth ≥ 45, reaccel ≥ 50)을 쉬운 말로 표시',
        'turn_sign':'현재 흐름의 힘·3개월 금융/심리/거래 변화·전망 문구를 함께 해석',
        'data_voice':'금융·심리·거래의 3개월 변화 방향을 비교'
      }
    }

def validate_strength(t):
    rows=[x for x in (t.get('rows') or []) if not x.get('source_provisional')]
    strong=[]; weak=[]
    for x in rows:
        m3=safe_num(x.get('momentum_3m_pct')); b=safe_num(x.get('breadth')); r=safe_num(x.get('reaccel'))
        if m3 is None or b is None or r is None or m3<=0: continue
        (strong if b>=45 and r>=50 else weak).append(x)
    def stats(pool,h):
        vals=[safe_num(x.get(f'fwd_{h}m_pct')) for x in pool]
        vals=[v for v in vals if v is not None]
        return {'n':len(vals),'mean_pct':mean(vals),'positive_pct':pct_pos(vals)}
    return {
      'status':'historically_supported' if strong and weak and (mean([safe_num(x.get('fwd_3m_pct')) for x in strong if safe_num(x.get('fwd_3m_pct')) is not None]) or -999) > (mean([safe_num(x.get('fwd_3m_pct')) for x in weak if safe_num(x.get('fwd_3m_pct')) is not None]) or 999) else 'insufficient',
      'rule':'상승 중 breadth>=45 AND reaccel>=50이면 힘 강함; 상승 중 두 조건을 모두 확인하지 못하면 힘 약함',
      'strong_uptrend':{'fwd_3m':stats(strong,3),'fwd_6m':stats(strong,6)},
      'weak_uptrend':{'fwd_3m':stats(weak,3),'fwd_6m':stats(weak,6)},
      'certified_through':t.get('certified_through'),
      'note':'과거검증 참고값이며 실제 발생확률이 아님'
    }

def main():
    j=json.loads(J.read_text(encoding='utf-8'))
    t=json.loads(T.read_text(encoding='utf-8'))
    out={
      'status':'research_interpretation',
      'version':'plain_market_interpretation_v1',
      'production_formula_changed':False,
      'new_score_created':False,
      'current':current_payload(j),
      'validation':validate_strength(t),
      'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    O.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'current':out['current'],'validation':out['validation']},ensure_ascii=False))

if __name__=='__main__':
    main()
