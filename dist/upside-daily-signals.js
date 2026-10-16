/* Research-only daily multi-signal probability. Certified KNN remains primary. */
(()=>{'use strict';
const root=document.getElementById('probabilityResearch');
if(!root)return;
const host=document.querySelector('.probability-track-v222')||document.getElementById('upProbHistory')||root;
const make=(name,cls,label,parent)=>{const el=document.createElement(name);if(cls)el.className=cls;if(label!=null)el.textContent=label;(parent||host).appendChild(el);return el;};
const section=make('section','daily-signal-v1',null);
section.setAttribute('aria-label','일별 금융 심리 거래 연동 연구 후보');
host.insertAdjacentElement('afterend',section);
const head=make('div','daily-signal-head-v1',null,section);
make('b','', '금융 · 심리 · 거래를 반영한 일별 신호',head);
make('span','daily-signal-mark-v1','검증 전 연구 후보',head);
const summary=make('p','daily-signal-summary-v1','연구용 확률 후보를 확인 중입니다.',section);
const note=make('p','daily-signal-note-v1','기존 인증 상승 확률은 위에 유지됩니다. 연구 후보는 아직 실제 상승 발생확률로 검증되지 않았습니다.',section);
const indicators=make('div','daily-signal-features-v1',null,section);
const sourceLabel=make('p','daily-signal-source-v1','원천 발표일 확인 중',section);
const chart=document.createElementNS('http://www.w3.org/2000/svg','svg');
chart.setAttribute('viewBox','0 0 440 156');
chart.setAttribute('role','img');
chart.setAttribute('aria-label','매일 확인한 기존 상승확률과 실험용 종합 상승확률의 변화');
chart.classList.add('daily-signal-chart-v1');
section.appendChild(chart);
const selected=make('p','daily-signal-selected-v1','일별 기록이 누적되면 차트에 표시됩니다.',section);
const extra=make('details','daily-signal-method-v1',null,section);
make('summary','', '모델 검증 및 출처 보기',extra);
const detail=make('p','', '실제 발표일 기준으로 입력을 기록하며, 미래정보 누수와 과거 원천 수정 가능성을 별도 관리합니다.',extra);
const num=v=>v===null||v===undefined||v===''||typeof v==='boolean'?null:(Number.isFinite(Number(v))?Number(v):null);
const pct=v=>num(v)===null?'—':num(v).toFixed(1)+'%';
const stamp=s=>{const a=String(s||'').replace(/[^0-9]/g,'');return a.length===8?a.slice(0,4)+'.'+a.slice(4,6)+'.'+a.slice(6,8):a.length===6?a.slice(0,4)+'.'+a.slice(4,6):'미확인'};
const svg=(tag,props,label)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(props))el.setAttribute(k,String(v));if(label!=null)el.textContent=label;chart.appendChild(el);return el;};
function draw(items){
 while(chart.firstChild)chart.removeChild(chart.firstChild);
 for(const v of [0,25,50,75,100]){
   const y=12+(100-v)*1.12;
   svg('line',{x1:38,y1:y,x2:430,y2:y,stroke:'#e1e9ed','stroke-dasharray':'3 3'});
   svg('text',{x:31,y:y+4,'text-anchor':'end','font-size':10,fill:'#8999a3'},v);
 }
 const valid=items.filter(x=>num(x.certified)!==null||num(x.candidate)!==null);
 if(!valid.length){svg('text',{x:235,y:71,'text-anchor':'middle',fill:'#8996a2','font-size':13},'일별 검증 기록 누적 대기');return;}
 const x=i=>valid.length===1?230:44+i*376/(valid.length-1);
 const y=n=>12+(100-n)*1.12;
 for(const [key,color] of [['certified','#587b8d'],['candidate','#ba7741']]){
   let segment=[];
   const finish=()=>{if(segment.length>1)svg('polyline',{points:segment.join(' '),fill:'none',stroke:color,'stroke-width':2.5,'stroke-linecap':'round','stroke-linejoin':'round'});segment=[];};
   valid.forEach((r,i)=>{const v=num(r[key]);if(v===null){finish();return;}segment.push(x(i)+','+y(v));});
   finish();
 }
 valid.forEach((r,i)=>{
   for(const [key,color] of [['certified','#587b8d'],['candidate','#ba7741']]){
     const v=num(r[key]);if(v===null)continue;
     const point=svg('circle',{cx:x(i),cy:y(v),r:4.2,fill:color,stroke:'white','stroke-width':1.5,tabindex:0,role:'button','aria-label':r.date+' '+key+' '+pct(v)});
     const choose=()=>{selected.textContent=r.date+' · 인증 '+pct(r.certified)+' / 연구 후보 '+pct(r.candidate);};
     point.addEventListener('click',choose);
     point.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}});
   }
 });
 const short=s=>String(s||'').slice(5);
 svg('text',{x:44,y:151,'font-size':11,fill:'#8c9ba4'},short(valid[0].date));
 if(valid.length>1)svg('text',{x:425,y:151,'text-anchor':'end','font-size':11,fill:'#8c9ba4'},short(valid.at(-1).date));
 const latest=valid.at(-1);selected.textContent=latest.date+' · 인증 '+pct(latest.certified)+' / 연구 후보 '+pct(latest.candidate);
}
async function init(){
 try{
  const [response,historyResponse,certifiedResponse]=await Promise.all([
   fetch('upside_daily_candidate.json?v='+Date.now(),{cache:'no-store'}),
   fetch('upside_probability_history.json?v='+Date.now(),{cache:'no-store'}),
   fetch('upside_probability_engine.json?v='+Date.now(),{cache:'no-store'})
  ]);
  if(!response.ok||!historyResponse.ok||!certifiedResponse.ok)throw Error('source not available');
  const d=await response.json(),history=await historyResponse.json(),cert=await certifiedResponse.json();
  const scope=d.scope?.market_scope_id;
  if(!scope||scope!==history.scope||scope!==cert.scope?.market_scope_id)throw Error('market scope mismatch');
  if(d.production_applied!==false||d.certification?.eligible!==false)throw Error('not a shadow');
  const c=d.current||{},ok=c.status==='ok',cp=ok?num(c.probabilities?.up):null;
  const official=num(cert.current?.probabilities?.up);
  summary.textContent=cp===null?'연구용 신호: 데이터 확인 중':'기존 인증 '+pct(official)+' → 일별 연구 후보 '+pct(cp)+' (차이 '+((cp-official)>=0?'+':'')+(cp-official).toFixed(1)+'%p)';
  note.textContent='연구 후보는 과거 수정자료로 학습한 미인증 확률입니다. 위쪽 '+pct(official)+' 인증 확률을 대체하지 않으며 실제 발생확률로 해석하지 마세요.';
  const labels={finance:'금융',sentiment:'심리',demand:'거래'};
  const vintages={finance:'대출 '+stamp(c.vintages?.finance_mortgage_month)+' · 기준금리 '+stamp(c.vintages?.finance_base_rate_day),
                  sentiment:'KB '+stamp(c.vintages?.sentiment_week),
                  demand:'완성 월 '+stamp(c.vintages?.trade_completed_month)};
  for(const key of ['finance','sentiment','demand']){
    const card=make('div','daily-signal-feature-v1',null,indicators);
    make('span','',labels[key],card);
    make('b','',ok&&num(c.components?.[key])!==null?Number(c.components[key]).toFixed(1)+'점':'—',card);
    let state=key==='demand'&&c.source_status?.trade==='fallback_last_good'?' · 마지막 정상값':'';
    make('small','',ok?vintages[key]+state:'원천 확인 중',card);
  }
  sourceLabel.textContent=ok?'입력 기준 '+String(c.as_of||'미확인')+' · 금융·심리·거래의 서로 다른 발표 주기를 유지':'일별 후보에 필요한 원천을 확인 중입니다.';
  const jd=Array.isArray(history.daily)?history.daily:[];
  const rd=Array.isArray(history.research_daily)?history.research_daily:[];
  const certMap=new Map(jd.map(x=>[x.date,num(x.probabilities?.up)]));
  const dates=[...new Set([...jd.map(x=>x.date),...rd.map(x=>x.date)])].sort();
  const shadowMap=new Map(rd.map(x=>[x.date,num(x.probabilities?.up)]));
  let items=dates.map(date=>({date,certified:certMap.get(date)??null,candidate:shadowMap.get(date)??null}));
  if(ok&&cp!==null&&!rd.some(x=>x.date===String(c.as_of||''))&&dates.length){
    // Do not invent a historical series: one current display point is
    // allowed only for the explicitly dated, actually computed live snapshot.
    const today=String(c.as_of||'');
    if(/^\d{4}-\d{2}-\d{2}$/.test(today)){
       items=items.filter(x=>x.date!==today);
       items.push({date:today,certified:official,candidate:cp});
       items.sort((a,b)=>a.date.localeCompare(b.date));
    }
  }
  draw(items);
  const train=d.training||{},val=d.metrics||{},selection=val.selection||{},holdout=val.holdout||{};
  const format=x=>x===null||x===undefined?'미확인':String(x);
  detail.textContent='인증 적용: 아니오. 검증 표본: 학습 '+format(train.selection_n)+'개월 / 별도 과거 검증 '+format(train.holdout_n)+'개월. Brier(과거 검증): 기존 '+format(holdout.baseline?.multiclass_brier)+' / 후보 '+format(holdout.candidate?.multiclass_brier)+'. 당시 수집된 원본 vintage가 없어 미래 누수 완전 배제를 주장하지 않으며, 독립 미래 검증이 끝나기 전에는 주 확률로 승격하지 않습니다.';
 }catch(err){
   console.warn('daily multisignal shadow unavailable',err);
   summary.textContent='일별 연구 후보: 데이터 확인 중';
   sourceLabel.textContent='공식 인증 확률은 위쪽에서 계속 확인할 수 있습니다.';
   draw([]);
 }
}
init();
})();