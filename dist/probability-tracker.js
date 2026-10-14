/* Probability tracking UI: server history, never browser-only memory. */
(()=>{'use strict';
const host=document.getElementById('probabilityResearch');
const anchor=document.getElementById('upProbHistory');
if(!host||!anchor)return;
const make=(tag,cls,text,parent)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined&&text!==null)n.textContent=text;if(parent)parent.appendChild(n);return n};
const safe=n=>{if(n===null||n===undefined||n==='')return null;const v=Number(n);return Number.isFinite(v)&&v>=0&&v<=100?v:null};
const labelDate=s=>{const z=String(s||'').replace(/[^0-9]/g,'');return z.length>=8?z.slice(0,4)+'.'+z.slice(4,6)+'.'+z.slice(6,8):'날짜 미확인'};
const signed=n=>{if(n===null)return '비교 기준 없음';return(n>0?'+':'')+n.toFixed(1)+'%p'};
const track=make('section','probability-track-v222',null);
track.setAttribute('aria-label','상승 확률 변화 기록');
anchor.insertAdjacentElement('afterend',track);
const comparison=make('div','probability-month-v222',null,track);
const monthTitle=make('span','', '1개월 전 · 동일 모델 재계산',comparison);
const monthValue=make('b','', '—',comparison);
const monthSource=make('small','', '비교 기준 확인 중',comparison);
const changes=make('div','probability-latest-v222','직전 기록 확인 중',track);
const head=make('div','probability-track-head-v222',null,track);
const title=make('b','', '상승 확률 추이',head);
const controls=make('div','probability-track-buttons-v222',null,head);
const buttonSource=make('button','is-active','관측일별',controls);
const buttonDaily=make('button','','매일 확인',controls);
for(const b of [buttonSource,buttonDaily])b.type='button';
const status=make('p','probability-track-status-v222','기록을 확인하고 있습니다.',track);
const chart=document.createElementNS('http://www.w3.org/2000/svg','svg');
chart.setAttribute('viewBox','0 0 440 188');
chart.setAttribute('role','img');
chart.setAttribute('aria-label','기간별 상승 확률 추이');
chart.classList.add('probability-track-svg-v222');
track.appendChild(chart);
const picked=make('p','probability-track-picked-v222','기록을 선택하면 날짜와 확률이 표시됩니다.',track);
const note=make('p','probability-track-note-v222','매일 점검해도 REB 주간 원천이 같으면 확률은 변하지 않을 수 있습니다.',track);
let events=[],daily=[],mode='source';
const ns='http://www.w3.org/2000/svg';
const svg=(tag,attributes,text)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attributes||{}))n.setAttribute(k,String(v));if(text!=null)n.textContent=text;chart.appendChild(n);return n};
const upOf=o=>safe(o&&o.probabilities&&o.probabilities.up);
function draw(){
  while(chart.firstChild)chart.removeChild(chart.firstChild);
  buttonSource.classList.toggle('is-active',mode==='source');
  buttonDaily.classList.toggle('is-active',mode==='daily');
  buttonSource.setAttribute('aria-pressed',String(mode==='source'));
  buttonDaily.setAttribute('aria-pressed',String(mode==='daily'));
  const items=(mode==='source'?events:daily).filter(x=>upOf(x)!==null);
  const fmt=x=>mode==='source'?labelDate(x.source_as_of):String(x.date||'날짜 미확인');
  for(const val of [0,25,50,75,100]){
    const y=14+(100-val)*1.27;
    svg('line',{x1:43,y1:y,x2:428,y2:y,stroke:'#dfe8ed','stroke-dasharray':'3 4'});
    svg('text',{x:35,y:y+4,'text-anchor':'end',fill:'#8294a1','font-size':11},String(val));
  }
  if(!items.length){svg('text',{x:232,y:90,'text-anchor':'middle',fill:'#8496a1','font-size':15},'기록 누적 대기');picked.textContent='저장된 비교 기록이 없습니다.';return;}
  const n=items.length;
  const xs=items.map((_,i)=>n===1?236:50+i*(369/(n-1)));
  const ys=items.map(x=>14+(100-upOf(x))*1.27);
  if(n>1)svg('polyline',{points:xs.map((x,i)=>x+','+ys[i]).join(' '),fill:'none',stroke:'#19758c','strokeWidth':3,'stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round'});
  const select=i=>{const p=items[i],v=upOf(p);const origin=p.origin==='archived_git_commit'?' · 기존 GitHub 기록':mode==='daily'&&p.status==='source_unchanged'?' · 원천 변화 없음':'';picked.textContent=fmt(p)+' · 상승 '+v.toFixed(1)+'%'+origin};
  items.forEach((o,i)=>{
    const v=upOf(o);
    const circle=svg('circle',{cx:xs[i],cy:ys[i],r:5,fill:'#176b86',stroke:'#fff','stroke-width':1.8,tabindex:0,role:'button','aria-label':fmt(o)+' 상승 '+v.toFixed(1)+'%'});
    circle.style.cursor='pointer';
    circle.addEventListener('click',()=>select(i));
    circle.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(i)}});
  });
  svg('text',{x:50,y:176,fill:'#758998','font-size':11},fmt(items[0]));
  if(n>1)svg('text',{x:420,y:176,fill:'#758998','font-size':11,'text-anchor':'end'},fmt(items[n-1]));
  select(n-1);
}
buttonSource.addEventListener('click',()=>{mode='source';draw()});
buttonDaily.addEventListener('click',()=>{mode='daily';draw()});
async function load(){
  try{
    const [engineRes,journalRes]=await Promise.all([
      fetch('upside_probability_engine.json?v='+Date.now(),{cache:'no-store'}),
      fetch('upside_probability_history.json?v='+Date.now(),{cache:'no-store'})
    ]);
    if(!engineRes.ok||!journalRes.ok)throw Error('history response');
    const engine=await engineRes.json(),journal=await journalRes.json();
    if(journal.scope!==(engine.scope||{}).market_scope_id)throw Error('market scope mismatch');
    const current=engine.current||{},now=safe(current.probabilities?.up);
    const one=engine.comparison_1m;
    if(one?.status==='reconstructed_from_weekly_history'){
      const old=safe(one.probabilities?.up);
      if(old!==null&&now!==null){
        monthValue.textContent=old.toFixed(1)+'% → '+now.toFixed(1)+'% ('+signed(now-old)+')';
        monthSource.textContent='기준 '+labelDate(one.as_of)+' · 과거 주간지수 재계산';
      }
    }else monthSource.textContent='동일 기준의 한 달 전 자료를 확인할 수 없습니다.';
    events=Array.isArray(journal.events)?journal.events.filter(x=>x.source_as_of&&upOf(x)!==null):[];
    daily=Array.isArray(journal.daily)?journal.daily.filter(x=>x.date):[];
    const last=events[events.length-1],prev=events[events.length-2];
    if(last&&now!==null){
      const lastUp=upOf(last);
      if(lastUp!==null&&lastUp===now&&prev&&upOf(prev)!==null){
        changes.textContent='직전 관측 '+upOf(prev).toFixed(1)+'% → '+now.toFixed(1)+'%  ('+signed(now-upOf(prev))+')';
      }else if(lastUp!==null&&lastUp!==now){
        changes.textContent='직전 저장값 '+lastUp.toFixed(1)+'% → 현재 '+now.toFixed(1)+'%  ('+signed(now-lastUp)+')';
        if(current.as_of)events.push({source_as_of:current.as_of,probabilities:current.probabilities,origin:'pending_server_record'});
      }else changes.textContent='직전 값과 변화 없음 · '+now.toFixed(1)+'%';
    }else changes.textContent='직전 관측값 비교 기준 없음';
    if(now!==null&&last&&upOf(last)!==null){
      const prior=upOf(last)===now?upOf(prev):upOf(last);
      changes.classList.toggle('is-down',prior!==null&&now<prior);
    }
    status.textContent='관측일 변화 '+events.length+'건 · 일별 확인 '+daily.length+'일';
    note.textContent='원천 관측일과 수집 확인일을 구분합니다. 과거 재계산은 발표 당시 저장값이 아닙니다. 주간 발표 전에는 같은 확률이 반복될 수 있습니다.';
    draw();
  }catch(e){
    console.warn('probability tracking unavailable',e);
    changes.textContent='최근 변화 기록 확인 중';
    status.textContent='저장된 상승 확률 이력을 불러오지 못했습니다.';
    monthSource.textContent='1개월 전 비교 데이터 확인 중';
    draw();
  }
}
load();
})();