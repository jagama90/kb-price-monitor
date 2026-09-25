'use strict';let SEOUL_VOLUME=[{m:'3월',v:5515},{m:'4월',v:8661},{m:'5월',v:8972},{m:'6월',v:5303},{m:'7월',v:5838},{m:'8월',v:3143,p:true}];function renderVolume(){const el=document.querySelector('#volumeChart');if(!el)return;const max=Math.max(...SEOUL_VOLUME.map(x=>x.v));el.innerHTML=SEOUL_VOLUME.map(x=>'<div class="vbar '+(x.p?'provisional':'')+'" style="height:'+Math.max(4,x.v/max*88)+'%"><strong>'+x.v.toLocaleString()+'</strong><label>'+x.m+(x.p?'*':'')+'</label></div>').join('')}renderVolume();const eok=n=>n==null?'—':(Number(n)/10000).toLocaleString('ko-KR',{maximumFractionDigits:2})+'억';const KB_HISTORY=[{d:'2026-09-05',avg:198849,n:43},{d:'2026-09-11',avg:190818,n:11}];function renderKbHistory(){const a=KB_HISTORY;if(!a.length)return;const vals=a.map(x=>x.avg),lo=Math.floor((Math.min(...vals)-10000)/10000)*10000,hi=Math.ceil((Math.max(...vals)+10000)/10000)*10000,range=Math.max(1,hi-lo);document.querySelector('#kbYAxis').innerHTML=[hi,hi-(range/3),hi-(range*2/3),lo].map(v=>'<b>'+eok(v)+'</b>').join('');const pts=a.map((x,i)=>{const px=a.length===1?210:i*420/(a.length-1),py=160-((x.avg-lo)/range)*150;return px.toFixed(1)+','+py.toFixed(1)}).join(' ');document.querySelector('#kbSvg').innerHTML='<line x1="0" y1="10" x2="420" y2="10"/><line x1="0" y1="60" x2="420" y2="60"/><line x1="0" y1="110" x2="420" y2="110"/><line x1="0" y1="160" x2="420" y2="160"/><polyline class="mainline" points="'+pts+'"/>'+a.map((x,i)=>{const px=a.length===1?210:i*420/(a.length-1),py=160-((x.avg-lo)/range)*150;return '<circle cx="'+px+'" cy="'+py+'" r="4" fill="#1677ff"/>'}).join('');document.querySelector('#kbXAxis').innerHTML=a.map(x=>'<span>'+x.d.slice(5).replace('-','/')+'</span>').join('');document.querySelector('#kbHistoryNote').textContent='DB 실데이터 '+a.length+'회 · '+a[0].d+' ~ '+a[a.length-1].d+' · 표본 '+a.map(x=>x.n+'건').join(' / ')};renderKbHistory();const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const signal=x=>{const d=Number(x.sale_listing_week_delta||0),t=x.recent_trade_manwon&&x.avg_ask_manwon?Number(x.recent_trade_manwon)-Number(x.avg_ask_manwon):0;if(d>0&&t<0)return['하락','down'];if(d<0&&t>=0)return['상승','up'];return['관찰','watch']};async function load(){const [m,k,tg]=await Promise.all([fetch('buy_watchlist_market.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),fetch('buy_watchlist_master.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),fetch('buy_watchlist_targets.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json())]);const market=m.items||[],master=k.items||[],targets=tg.items||[];const kb=new Map(master.map(x=>{const vals=(x.types||[]).map(t=>Number(t.general_price_manwon)).filter(Number.isFinite);return [Number(x.complex_id),vals.length?Math.round(vals.reduce((a,b)=>a+b,0)/vals.length):null]}));document.querySelector('#updated').textContent='KB '+new Date(k.kb_collected_at||Date.now()).toLocaleDateString('ko-KR')+' · MARKET '+new Date(m.collected_at||Date.now()).toLocaleDateString('ko-KR');const collected=new Date(m.collected_at||Date.now()), collectedText=collected.toLocaleString('ko-KR',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});document.querySelector('#marketDate').textContent=collected.toLocaleDateString('ko-KR');const norm=s=>String(s||'').replace(/\s|아파트|\(|\)|마천역/g,'');const targetMap=new Map(targets.map(t=>[norm(t.name),t]));const preferred=x=>{const t=targetMap.get(norm(x.user_name||x.kb_name)),types=x.types||[];if(!t||t.min_pyeong==null)return types;return types.filter(a=>{const m=String(a.type_label||'').match(/\d+(?:\.\d+)?/);return m&&Number(m[0])>=Number(t.min_pyeong)&&Number(m[0])<=Number(t.max_pyeong)})};let boundary=[...master].map(x=>{const a=preferred(x).filter(t=>Number(t.general_price_manwon));if(!a.length)return null;const z=a.reduce((p,c)=>Math.abs(Number(c.general_price_manwon)-150000)<Math.abs(Number(p.general_price_manwon)-150000)?c:p);return{name:x.user_name||x.kb_name,p:Number(z.general_price_manwon),type:z.type_label}}).filter(Boolean).filter(x=>x.p>=130000&&x.p<=170000).sort((a,b)=>Math.abs(a.p-150000)-Math.abs(b.p-150000)).slice(0,7);const boundaryEl=document.querySelector('#boundary');let boundaryMode='near';const renderBoundary=()=>{const a=[...boundary].sort((x,y)=>boundaryMode==='asc'?x.p-y.p:boundaryMode==='desc'?y.p-x.p:Math.abs(x.p-150000)-Math.abs(y.p-150000));boundaryEl.innerHTML='<div class="mini-sort"><button data-b="near" class="'+(boundaryMode==='near'?'active':'')+'">15억 근접</button><button data-b="asc" class="'+(boundaryMode==='asc'?'active':'')+'">낮은순</button><button data-b="desc" class="'+(boundaryMode==='desc'?'active':'')+'">높은순</button></div>'+ (a.map(x=>'<div class="row"><span>'+esc(x.name)+' <small>'+esc(x.type)+'평</small></span><b class="'+(x.p<=150000?'up':'')+'">'+eok(x.p)+'</b></div>').join('')||'<small>13~17억 구간 데이터 없음</small>');boundaryEl.querySelectorAll('[data-b]').forEach(b=>b.onclick=()=>{boundaryMode=b.dataset.b;renderBoundary()})};renderBoundary();const radarBase=[...market].filter(x=>x.sale_listing_week_delta!=null&&Number(x.sale_listing_week_delta)!==0);let radarMode='abs';const radarEl=document.querySelector('#radar');const renderRadar=()=>{const radar=[...radarBase].sort((a,b)=>radarMode==='up'?Number(b.sale_listing_week_delta)-Number(a.sale_listing_week_delta):radarMode==='down'?Number(a.sale_listing_week_delta)-Number(b.sale_listing_week_delta):Math.abs(Number(b.sale_listing_week_delta))-Math.abs(Number(a.sale_listing_week_delta))).slice(0,7);radarEl.innerHTML='<small class="radar-period">최근 수집 '+collectedText+' · 직전 주간 스냅샷 대비</small><div class="mini-sort"><button data-r="abs" class="'+(radarMode==='abs'?'active':'')+'">변동폭</button><button data-r="up" class="'+(radarMode==='up'?'active':'')+'">증가순</button><button data-r="down" class="'+(radarMode==='down'?'active':'')+'">감소순</button></div>'+(radar.length?radar.map(x=>'<div class="radar-row"><span>'+esc(x.name)+'</span><b class="'+(x.sale_listing_week_delta>0?'down':'up')+'">'+(x.sale_listing_week_delta>0?'+':'')+Number(x.sale_listing_week_delta)+'건</b></div>').join(''):'<small class="no-change">변동이 있는 단지가 없습니다.</small>');radarEl.querySelectorAll('[data-r]').forEach(b=>b.onclick=()=>{radarMode=b.dataset.r;renderRadar()})};renderRadar();const rows=[...market].sort((a,b)=>Math.abs(Number(b.sale_listing_week_delta||0))-Math.abs(Number(a.sale_listing_week_delta||0)));document.querySelector('#summary').textContent='총 '+master.length+'개 관심단지 · KB · 호가 · 실거래 · 매물';document.querySelector('#body').innerHTML=rows.map(x=>{const s=signal(x);return'<tr><td><b>'+esc(x.name)+'</b></td><td>'+eok(kb.get(Number(x.complex_id)))+'</td><td>'+eok(x.recent_trade_manwon)+'<small> '+esc(x.recent_trade_date||'')+'</small></td><td>'+eok(x.avg_ask_manwon)+'</td><td>'+Number(x.sale_listing_count||0).toLocaleString()+'건</td><td class="'+(x.sale_listing_week_delta>0?'down':x.sale_listing_week_delta<0?'up':'')+'">'+(x.sale_listing_week_delta>0?'+':'')+Number(x.sale_listing_week_delta||0)+'건</td><td><span class="pill '+s[1]+'">'+s[0]+'</span></td></tr>'}).join('');document.querySelector('#mobileCards').innerHTML=rows.map(x=>{const s=signal(x);return'<article class="complex"><div class="complex-head"><b>'+esc(x.name)+'</b><span class="pill '+s[1]+'">'+s[0]+'</span></div><div class="complex-grid"><div><span>KB시세</span><b>'+eok(kb.get(Number(x.complex_id)))+'</b></div><div><span>최근 실거래</span><b>'+eok(x.recent_trade_manwon)+'</b></div><div><span>매물 평균</span><b>'+eok(x.avg_ask_manwon)+'</b></div><div><span>매매 매물</span><b>'+Number(x.sale_listing_count||0)+'건</b></div><div><span>주간 증감</span><b class="'+(x.sale_listing_week_delta>0?'down':x.sale_listing_week_delta<0?'up':'')+'">'+(x.sale_listing_week_delta>0?'+':'')+Number(x.sale_listing_week_delta||0)+'건</b></div><div><span>최근 거래일</span><b>'+esc(x.recent_trade_date||'—')+'</b></div></div></article>'}).join('')+'<button id="moreComplexes" class="more-btn">↓ 더보기 ('+Math.max(0,rows.length-5)+'개)</button>';const mc=document.querySelector('#mobileCards'),mb=document.querySelector('#moreComplexes');if(rows.length<=5)mb.style.display='none';mb.addEventListener('click',()=>{const open=mc.classList.toggle('expanded');mb.textContent=open?'↑ 접기':'↓ 더보기 ('+Math.max(0,rows.length-5)+'개)'})}load().catch(e=>{document.querySelector('#updated').textContent='관심단지 일부 데이터 확인 필요';console.error(e)});
async function loadMarketIndicators(){
 try{
  const d=await fetch('market_indicators.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json());
  const vols=d.seoul_apt_trade_count||[];
  if(vols.length){SEOUL_VOLUME=vols.map(x=>({m:Number(x[0].slice(5))+'월',v:x[1],p:x[2]}));renderVolume();const z=vols[vols.length-1];setText('snapVolume',Number(z[1]).toLocaleString('ko-KR')+'건');setText('snapVolumePeriod',z[0]+(z[2]?' · 신고 진행':' · 집계'))}
  const bands=d.price_bands?.months||[],latest=bands[bands.length-1];
  if(latest){setText('snapUnder15',latest.under15_share+'%');const ids={'b9':'<=9eok','b15':'9-15eok','b25':'15-25eok','b25p':'25eok+'};Object.entries(ids).forEach(([id,k])=>setText(id,Number(latest.counts?.[k]||0).toLocaleString('ko-KR')+'건'))}
  const m=d.m2_official||d.m2;if(m){setText('snapM2',m.yoy_pct==null?'—':m.yoy_pct+'%');setText('snapM2Period',m.period+' · 한국은행 ECOS');setText('m2Detail','ECOS 동일 M2 수준계열 기준 · 전월비 '+(m.mom_pct??'—')+'% · 전년비 '+(m.yoy_pct??'—')+'%')}
  if(d.matched_period){const x=d.matched_period,c=x.current,p=x.previous,fmt=v=>v==null?'—':Number(v).toLocaleString('ko-KR');setText('matchedRange',p.period+' '+p.range+' ↔ '+c.period+' '+c.range+' · 계약일 기준');setText('matchedVolume',fmt(p.total)+' → '+fmt(c.total)+'건');setText('matchedVolumeDelta',x.changes?.trade_count_pct==null?'증감 계산 대기':signed(x.changes.trade_count_pct,'%')+' · 당월 신고 진행');setText('matchedUnder15',(p.under15_share??'—')+' → '+(c.under15_share??'—')+'%');setText('matchedUnder15Delta',x.changes?.under15_share_pp==null?'증감 계산 대기':signed(x.changes.under15_share_pp,'%p'))}
  renderKbOfficial(d);
  renderConditionIndex(d);
  setupScoreDetails(d,window.__conditionComponents||{});
  setupSnapshotEvidence(d);
  window.__marketIndicators=d;
  const updated=document.querySelector('#updated');if(updated&&/LOADING|DATA ERROR|관심단지 일부/.test(updated.textContent))updated.textContent='MARKET '+(d.updated_at||new Date().toLocaleDateString('ko-KR'));
 }catch(e){console.error(e)}
}
const setText=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v};
function setupSnapshotEvidence(d){
 const x=d.matched_period;
 const open=(title,source,current,previous,delta,note,formula)=>{document.getElementById('rateDetail').hidden=true;document.getElementById('macroDetail').hidden=true;setText('snapshotExplainTitle',title);setText('snapshotExplainSource',source);document.getElementById('snapshotExplainBody').innerHTML='<div class="evidence-compare"><div><small>현재 동일기간</small><b>'+esc(current[0])+'</b><span>'+esc(current[1])+'</span></div><div><small>직전월 동일기간</small><b>'+esc(previous[0])+'</b><span>'+esc(previous[1])+'</span></div></div><div class="evidence-change"><div><span>변화</span><b>'+esc(delta)+'</b></div><p>'+esc(note)+'</p></div><div class="evidence-method"><b>산출 기준</b><p>'+esc(formula)+'</p></div>';const el=document.getElementById('snapshotExplanation');el.hidden=false};
 const bind=(id,fn)=>{const el=document.getElementById(id);if(!el)return;el.onclick=fn;el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fn()}}};
 if(x){bind('volumeCard',()=>open('서울 거래량','국토교통부 실거래가 · 계약일 기준',[Number(x.current.total).toLocaleString('ko-KR')+'건',x.current.period+' '+x.current.range],[Number(x.previous.total).toLocaleString('ko-KR')+'건',x.previous.period+' '+x.previous.range],signed(x.changes.trade_count_pct,'%'),x.warning||'당월 신고 진행 중','현재월과 직전월을 같은 달력일 구간으로 맞춰 계약 건수를 비교합니다.'));bind('under15Card',()=>open('15억 이하 비중','국토교통부 실거래가 · 서울 아파트',[x.current.under15_share+'%',x.current.period+' '+x.current.range],[x.previous.under15_share+'%',x.previous.period+' '+x.previous.range],signed(x.changes.under15_share_pp,'%p'),'중저가 거래 비중의 월간 이동','15억원 이하 거래건수 ÷ 해당 동일기간 서울 아파트 전체 거래건수 × 100'))}
 document.getElementById('closeSnapshotExplain')?.addEventListener('click',()=>document.getElementById('snapshotExplanation').hidden=true);
}
const signed=(v,s='')=>(Number(v)>0?'+':'')+Number(v).toFixed(1)+s;
const clamp=v=>Math.max(0,Math.min(100,v));
function renderKbOfficial(d){const s=d.kb_weekly_sale_index,r=d.kb_weekly_rent_index,m=d.mortgage_rate_official,v=d.kb_value;const box=document.getElementById('kbOfficialData');if(!box)return;const f=x=>x?.latest?Number(x.latest.value).toFixed(2)+' <small>'+esc(x.latest.date)+'</small>':'수집 대기';box.innerHTML='<div><span>KB 주간 매매가격지수</span><b>'+f(s)+'</b></div><div><span>KB 주간 전세가격지수</span><b>'+f(r)+'</b></div><div><span>ECOS 주담대금리</span><b>'+(m?.rate_pct!=null?m.rate_pct+'% <small>'+esc(m.period)+'</small>':'수집 대기')+'</b></div><div><span>가격·Value</span><b>'+(v?.score_0_100!=null?v.score_0_100+'/100':'52주 검증 대기')+'</b></div>'}
function renderConditionIndex(d){
 const bands=d.price_bands?.months||[],latest=bands[bands.length-1],prev=bands[bands.length-2],m=d.m2_official||d.m2,matched=d.matched_period;
 const components={finance:null,sentiment:null,demand:null,value:null,supply:null};
 if(d.kb_sentiment?.score_0_100!=null)components.sentiment=Number(d.kb_sentiment.score_0_100);
 if(m?.mom_pct!=null&&m?.yoy_pct!=null)components.finance=clamp(50+Number(m.mom_pct)*8+Number(m.yoy_pct)*1.5);
 if(matched?.changes?.trade_count_pct!=null&&matched?.changes?.under15_share_pp!=null)components.demand=clamp(50+Number(matched.changes.trade_count_pct)*.35+Number(matched.changes.under15_share_pp)*1.5);
 if(d.kb_value?.score_0_100!=null)components.value=Number(d.kb_value.score_0_100);
 if(d.kb_sentiment?.jeonse_score_0_100!=null)components.supply=Number(d.kb_sentiment.jeonse_score_0_100);
 window.__conditionComponents=components;
 const weights={finance:25,sentiment:20,demand:20,value:20,supply:15},labels={finance:'scoreFinance',sentiment:'scoreSentiment',demand:'scoreDemand',value:'scoreValue',supply:'scoreSupply'};
 Object.entries(labels).forEach(([k,id])=>setText(id,components[k]==null?'미연결':Math.round(components[k])+'/100'));
 const historyKey='marketConditionPreviousComponents', previous=(()=>{try{return JSON.parse(localStorage.getItem(historyKey)||'{}')}catch(e){return {}}})();
 Object.entries(labels).forEach(([k,id])=>{const card=document.querySelector('[data-score="'+k+'"]'),old=previous[k],now=components[k];card?.querySelector('.score-change-badge')?.remove();if(old!=null&&now!=null&&Math.round(Number(old))!==Math.round(Number(now))){const delta=Math.round(Number(now))-Math.round(Number(old)),badge=document.createElement('span');badge.className='score-change-badge '+(delta>0?'score-up':'score-down');badge.textContent=(delta>0?'↑ +':'↓ ')+delta;badge.title='이전 확인값 '+Math.round(Number(old))+' → 현재 '+Math.round(Number(now));card?.appendChild(badge)}});
 try{localStorage.setItem(historyKey,JSON.stringify(components))}catch(e){}
 const available=Object.keys(components).filter(k=>components[k]!=null),covered=available.reduce((a,k)=>a+weights[k],0);
 setText('confidenceScore',covered+'% 가중치 연결');
 if(covered<60){setText('conditionScore','산출 보류');setText('heroMeterValue','—');const meter=document.getElementById('heroMeterFill');if(meter)meter.style.width='0%'}
 else {const score=Math.round(available.reduce((a,k)=>a+components[k]*weights[k],0)/covered);setText('conditionScore',score+'/100');setText('heroMeterValue',score+'/100');const meter=document.getElementById('heroMeterFill');if(meter)meter.style.width=score+'%'}
 const finance=components.finance,sent=components.sentiment,demand=components.demand,value=components.value;
 const trade=matched?.changes?.trade_count_pct,under=matched?.changes?.under15_share_pp,mom=m?.mom_pct;
 const state=(v)=>v==null?['미연결','neutral']:v>=55?['우호적','good']:v<45?['제약','bad']:['중립','neutral'];
 const fs=state(finance),ss=state(sent),ds=state(demand),vs=state(value),sup=state(components.supply);
 const stateLabel=s=>s[0]==='우호적'?'개선 신호':s[0]==='제약'?'제약 신호':s[0]==='중립'?'중립 구간':'미연결';
 [['Finance',fs],['Sentiment',ss],['Demand',ds],['Value',vs],['Supply',sup]].forEach(([id,s])=>{setText('state'+id,stateLabel(s));const el=document.getElementById('state'+id);if(el)el.className='component-state '+s[1]});
 const connected=[finance,sent,demand,value,components.supply].filter(v=>v!=null);
 const weak=connected.filter(v=>v<45).length,strong=connected.filter(v=>v>=55).length;
 setText('heroVerdict',weak>=3?'아직은 제약 신호가 우세합니다. 반전 확인이 필요한 구간입니다.':strong>=3?'개선 신호가 여러 단계에서 확인되고 있습니다. 지속성을 확인할 구간입니다.':'개선과 제약 신호가 엇갈립니다. 다음 단계로의 전달을 확인할 구간입니다.');
 [['Finance',fs],['Sentiment',ss],['Demand',ds],['Value',vs]].forEach(([id,s])=>{setText('path'+id,s[0]);const el=document.getElementById('node'+id);if(el)el.className='signal-node '+s[1]});
 setText('pathFinanceNote',mom==null?'금리·유동성':('M2 전월비 '+signed(mom,'%')));
 setText('pathDemandNote',trade==null?'거래량·자금 이동':('동일기간 거래 '+signed(trade,'%')));
 const positives=[],negatives=[];
 if(mom>0)positives.push(['유동성 확대','M2 전월비 '+signed(mom,'%')]);if(mom<0)negatives.push(['유동성 축소','M2 전월비 '+signed(mom,'%')]);
 if(under>0)positives.push(['중저가 거래비중 확대','15억 이하 '+signed(under,'%p')]);if(under<0)negatives.push(['중저가 거래비중 축소','15억 이하 '+signed(under,'%p')]);
 if(trade>0)positives.push(['거래량 증가','동일기간 '+signed(trade,'%')]);if(trade<0)negatives.push(['거래량 둔화','동일기간 '+signed(trade,'%')]);
 const p=positives[0]||['뚜렷한 개선 신호 없음','연결 지표를 계속 확인'],n=negatives[0]||['뚜렷한 제약 신호 없음','연결 지표를 계속 확인'];
 setText('positiveLead',p[0]);setText('positiveSub',p[1]);setText('negativeLead',n[0]);setText('negativeSub',n[1]);
 let headline='신호가 아직 한 방향으로 연결되지 않았습니다',summary='금융·심리·거래·가격을 각각 확인하며 다음 단계로의 전달 여부를 봅니다.';
 if(finance>=50&&sent<45){headline='금융여건과 시장심리 사이에 간극이 있습니다';summary='자금 여건이 상대적으로 나아져도 심리가 약하면 거래와 가격으로의 전달을 확인해야 합니다.'}
 if(trade<0){headline='선행 여건보다 거래 둔화가 더 강하게 나타납니다';summary='유동성·가격대 변화만으로 반전을 판단하지 않고 실제 거래량이 회복되는지를 다음 확인 신호로 봅니다.'}
 if(trade>0&&sent>=45){headline='심리와 거래가 함께 회복되는지 확인할 구간입니다';summary='거래 회복이 가격과 관심단지까지 이어지는지 확인하는 단계입니다.'}
 setText('storyHeadline',headline);setText('storySummary',summary);
 const next=[];if(trade<0)next.push('거래량 반등');if(sent<45)next.push('KB 심리 회복');next.push('15억 이하 비중 지속성');next.push('관심단지 실거래 전이');
 document.getElementById('nextSignals').innerHTML=next.slice(0,4).map((x,i)=>'<span><b>'+(i+1)+'</b>'+esc(x)+'</span>').join('');
 setTimeout(renderConditionHistory,0);
}
loadMarketIndicators();
const BASE_RATES=[{d:'2016-06-09',v:1.25},{d:'2017-11-30',v:1.50},{d:'2018-11-30',v:1.75},{d:'2019-07-18',v:1.50},{d:'2019-10-16',v:1.25},{d:'2020-03-17',v:.75},{d:'2020-05-28',v:.50},{d:'2021-08-26',v:.75},{d:'2021-11-25',v:1.00},{d:'2022-01-14',v:1.25},{d:'2022-04-14',v:1.50},{d:'2022-05-26',v:1.75},{d:'2022-07-13',v:2.25},{d:'2022-08-25',v:2.50},{d:'2022-10-12',v:3.00},{d:'2022-11-24',v:3.25},{d:'2023-01-13',v:3.50},{d:'2024-10-11',v:3.25},{d:'2024-11-28',v:3.00},{d:'2025-02-25',v:2.75},{d:'2025-05-29',v:2.50},{d:'2026-07-16',v:2.75},{d:'2026-08-27',v:3.00}];
let RATE_PAGE=0,MACRO_PAGE=0;
function renderPagedSeries(svgId,xId,yId,rows,page=0,pageSize=7,fixedScale=null){
 const end=Math.max(1,rows.length-page*pageSize),start=Math.max(0,end-pageSize),view=rows.slice(start,end);
 const W=620,H=250,L=54,R=18,T=30,B=48,allVals=rows.map(x=>Number(x.v)),rawMin=fixedScale?fixedScale[0]:Math.min(...allVals),rawMax=fixedScale?fixedScale[1]:Math.max(...allVals),pad=fixedScale?0:Math.max(.25,(rawMax-rawMin)*.18),lo=Math.max(0,rawMin-pad),hi=rawMax+pad,range=Math.max(.5,hi-lo);
 const X=i=>L+i*(W-L-R)/Math.max(1,view.length-1),Y=v=>T+(hi-v)/range*(H-T-B);
 const ticks=5,grid=Array.from({length:ticks},(_,i)=>{const val=hi-i*range/(ticks-1),y=T+i*(H-T-B)/(ticks-1);return '<line x1="'+L+'" y1="'+y+'" x2="'+(W-R)+'" y2="'+y+'" class="gridline"/><text x="'+(L-8)+'" y="'+(y+4)+'" text-anchor="end" class="ylabel">'+val.toFixed(2)+'%</text>'}).join('');
 const line=view.map((x,i)=>X(i)+','+Y(Number(x.v))).join(' ');
 const marks=view.map((x,i)=>'<circle cx="'+X(i)+'" cy="'+Y(Number(x.v))+'" r="5"/><text x="'+X(i)+'" y="'+(Y(Number(x.v))-12)+'" text-anchor="middle" class="pointlabel">'+Number(x.v).toFixed(2)+'</text><text x="'+X(i)+'" y="'+(H-18)+'" text-anchor="middle" class="xlabel">'+esc(String(x.d).slice(2,7).replace('-','.'))+'</text>').join('');
 const svg=document.getElementById(svgId);svg.setAttribute('viewBox','0 0 '+W+' '+H);svg.removeAttribute('width');svg.removeAttribute('height');svg.innerHTML=grid+'<polyline points="'+line+'" class="seriesline"/>'+marks;
 const axis=document.getElementById(xId);if(axis)axis.innerHTML='';const yy=document.getElementById(yId);if(yy)yy.innerHTML='';
 return {start,end,total:rows.length};
}
function renderRateDetail(){
 const pg=renderPagedSeries('rateSvg','rateX','rateY',BASE_RATES,RATE_PAGE,7,[0.50,3.75]);setText('rateRange',BASE_RATES[pg.start].d+' ~ '+BASE_RATES[pg.end-1].d);
 document.getElementById('rateHistory').innerHTML='<div class="head"><span>변경일</span><b>기준금리</b><em>직전 대비</em></div>'+BASE_RATES.slice(-8).reverse().map(x=>{const n=BASE_RATES.indexOf(x),p=n?BASE_RATES[n-1].v:null,delta=p==null?'—':((x.v-p)>0?'+':'')+(x.v-p).toFixed(2)+'%p';return '<div><span>'+x.d+'</span><b>'+x.v.toFixed(2)+'%</b><em>'+delta+'</em></div>'}).join('');
 document.getElementById('ratePrev').disabled=pg.start===0;document.getElementById('rateNext').disabled=pg.end===pg.total;
}
const rc=document.querySelector('#rateCard'),rd=document.querySelector('#rateDetail');
function openRate(){RATE_PAGE=0;rd.hidden=false;document.querySelector('#macroDetail').hidden=true;document.querySelector('#snapshotExplanation').hidden=true;rc.setAttribute('aria-expanded','true');renderRateDetail()}
rc?.addEventListener('click',openRate);rc?.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openRate()}});
document.querySelector('#closeRate')?.addEventListener('click',()=>{rd.hidden=true;rc.setAttribute('aria-expanded','false')});
document.querySelector('#ratePrev')?.addEventListener('click',()=>{RATE_PAGE++;renderRateDetail()});document.querySelector('#rateNext')?.addEventListener('click',()=>{RATE_PAGE=Math.max(0,RATE_PAGE-1);renderRateDetail()});
const MACRO={m2:{title:'한국 M2 통화공급 증가율',source:'한국은행 ECOS',series:[{d:'2026-03',v:7.3},{d:'2026-04',v:8.2},{d:'2026-05',v:7.0},{d:'2026-06',v:8.2}]}};
function showMacro(k){
 const z=MACRO[k],live=window.__marketIndicators?.m2_official||window.__marketIndicators?.m2,rows=z.series.slice();
 if(live?.period&&live?.yoy_pct!=null){const pd=String(live.period).slice(0,4)+'-'+String(live.period).slice(4,6),i=rows.findIndex(x=>x.d===pd);if(i>=0)rows[i]={d:pd,v:Number(live.yoy_pct)};else rows.push({d:pd,v:Number(live.yoy_pct)})}
 setText('macroTitle',z.title);setText('macroSource',z.source);document.getElementById('macroCurrent').innerHTML='<div><span>현재</span><b>'+(live?.yoy_pct!=null?Number(live.yoy_pct).toFixed(1)+'%':'—')+'</b></div><small>'+(live?.period||'최신')+' · 한국은행 ECOS</small>';
 MACRO_PAGE=0;const pg=renderPagedSeries('macroSvg','macroX','macroY',rows,MACRO_PAGE,7);setText('macroRange',rows[pg.start].d+' ~ '+rows[pg.end-1].d);
 document.getElementById('macroHistory').innerHTML='<div class="head"><span>기간</span><b>전년비</b><em>출처</em></div>'+rows.slice().reverse().map(x=>'<div><span>'+x.d+'</span><b>'+x.v.toFixed(1)+'%</b><em>ECOS</em></div>').join('');
 const el=document.getElementById('macroDetail');document.querySelector('#rateDetail').hidden=true;document.querySelector('#snapshotExplanation').hidden=true;el.hidden=false;
 document.getElementById('macroPrev').disabled=true;document.getElementById('macroNext').disabled=true;
}
document.querySelector('#m2Card')?.addEventListener('click',()=>showMacro('m2'));document.querySelector('#closeMacro')?.addEventListener('click',()=>document.querySelector('#macroDetail').hidden=true);

async function loadEcosFinanceSamples(){
 try{
  const d=await fetch('ecos_finance_sample.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),r=d.results||{};
  const pick=(x,match)=>{const a=x?.sample?.rows||[];return a.find(z=>String(z.item||'').includes(match))||a[a.length-1]};
  const rate=pick(r.loan_rate,'주택담보대출'),credit=pick(r.household_credit,''),mort=pick(r.mortgage,'');
  if(rate){setText('sampleMortgageRate',rate.value+'%');setText('sampleMortgageRateMeta',(rate.time||'')+' · '+(rate.item||'')+' · 샘플')}
  if(credit){setText('sampleHouseholdCredit',Number(credit.value).toLocaleString('ko-KR'));setText('sampleHouseholdCreditMeta',(credit.time||'')+' · '+(credit.item||'')+' · 샘플')}
  if(mort){setText('sampleMortgage',Number(mort.value).toLocaleString('ko-KR'));setText('sampleMortgageMeta',(mort.time||'')+' · '+(mort.item||'')+' · 샘플')}
 }catch(e){console.warn('ECOS finance sample not published yet',e)}
}
loadEcosFinanceSamples();

let SCORE_DETAIL_DATA={};
function scoreDetailRows(k,d,c){
 const m=d.m2_official||d.m2, x=d.matched_period, ks=d.kb_sentiment||{}, v=d.kb_value||{};
 const guide={
  finance:'해석 · 0~39 긴축/제약 · 40~59 중립 · 60~100 완화/개선. M2 증가율이 높을수록 점수가 올라갑니다.',
  sentiment:'해석 · KB 원지표는 0~200, 100이 매수·매도 균형입니다. 이 상황판 점수는 0~100으로 환산하며 0~39 매도우위 · 40~59 중립 · 60~100 매수우위입니다.',
  demand:'해석 · 0~39 수요 위축 · 40~59 중립 · 60~100 수요 개선. 전월 같은 신고구간보다 거래량과 15억 이하 비중이 늘수록 올라갑니다.',
  value:'해석 · 25~75 범위. 최근 36개월 가격대에서 저점에 가까울수록 75, 고점에 가까울수록 25입니다. 50은 36개월 중간 위치입니다.',
  supply:'해석 · KB 원지표는 0~200, 100이 수요·공급 균형입니다. 상황판 점수는 0~100 환산값으로 0~39 공급우위 · 40~59 중립 · 60~100 수요우위입니다.'
 };
 let rows;
 if(k==='finance')rows=[['M2 전월비',m?.mom_pct==null?'미연결':signed(m.mom_pct,'%'),'전월보다 시중 유동성이 얼마나 늘거나 줄었는지'],['M2 전년비',m?.yoy_pct==null?'미연결':signed(m.yoy_pct,'%'),'1년 전보다 유동성이 얼마나 늘었는지'],['현재 산출값',c.finance==null?'미연결':Math.round(c.finance)+'/100','50 + 전월비×8 + 전년비×1.5']];
 else if(k==='sentiment')rows=[['KB 매수우위',ks.latest?.['매수우위']?.value==null?'미연결':Number(ks.latest['매수우위'].value).toFixed(1),'0~200 · 100=매수자와 매도자 균형 · 높을수록 매수자 우위'],['KB 거래활발',ks.latest?.['매매거래활발']?.value==null?'미연결':Number(ks.latest['매매거래활발'].value).toFixed(1),'0~200 · 높을수록 거래가 활발하다는 응답이 강함'],['현재 산출값',c.sentiment==null?'미연결':Math.round(c.sentiment)+'/100','두 KB 심리지표를 상황판 0~100 척도로 환산']];
 else if(k==='demand')rows=[['동일기간 거래량 변화',x?.changes?.trade_count_pct==null?'미연결':signed(x.changes.trade_count_pct,'%'),'전월과 같은 계약일 구간 대비 · 0%=거래량 동일'],['15억 이하 비중 변화',x?.changes?.under15_share_pp==null?'미연결':signed(x.changes.under15_share_pp,'%p'),'0%p=비중 동일 · +면 15억 이하 거래비중 확대'],['현재 산출값',c.demand==null?'산출 보류':Math.round(c.demand)+'/100',c.demand==null?'두 입력값 연결 후 산출':'50 + 거래량 변화×0.35 + 비중 변화×1.5']];
 else if(k==='value')rows=[['KB 현재가격',v.current_manwon==null?'미연결':(v.current_manwon/10000).toFixed(2)+'억','가락금호 24A KB 월별 일반거래가'],['36개월 범위',(v.window_low_manwon==null||v.window_high_manwon==null)?'미연결':(v.window_low_manwon/10000).toFixed(2)+'억 ~ '+(v.window_high_manwon/10000).toFixed(2)+'억','이 범위에서 현재가격의 위치를 계산'],['가격 위치',v.current_position_0_1==null?'미연결':Math.round(v.current_position_0_1*100)+'%','0%=36개월 저점 · 100%=36개월 고점'],['현재 산출값',c.value==null?'미연결':Math.round(c.value)+'/100',v.status==='connected'?'저점 75점 ↔ 중간 50점 ↔ 고점 25점':'과거 이력 검증 대기']];
 else rows=[['KB 전세수급',ks.latest?.['전세수급']?.value==null?'미연결':Number(ks.latest['전세수급'].value).toFixed(1),'0~200 · 100=수요·공급 균형 · 높을수록 전세 수요우위'],['전세거래활발',ks.latest?.['전세거래활발']?.value==null?'미연결':Number(ks.latest['전세거래활발'].value).toFixed(1),'0~200 · 높을수록 전세 거래가 활발하다는 응답이 강함'],['현재 산출값',c.supply==null?'미연결':Math.round(c.supply)+'/100','KB 전세 신호를 상황판 0~100 척도로 환산']];
 return {guide:guide[k],rows};
}
function setupScoreDetails(d,c){
 SCORE_DETAIL_DATA={d,c};
 const meta={finance:['금융여건','25%','금리·유동성·신용이 실제 자금조달 여건을 얼마나 개선했는지 봅니다.'],sentiment:['시장심리','20%','KB 매수우위와 거래활발 지수로 매수·매도 압력을 봅니다.'],demand:['실수요·거래','20%','동일기간 거래량과 15억 이하 거래비중으로 실제 수요 확인 여부를 봅니다.'],value:['가격·밸류','20%','현재 가격의 장기 위치를 보되 가격 하락 자체를 매수 호재로 간주하지 않습니다.'],supply:['공급·전세','15%','전세수급·거래와 향후 입주·미분양을 통해 공급 부담을 검증합니다.']};
 const open=k=>{const [title,w,desc]=meta[k], detail=scoreDetailRows(k,d,c), rows=detail.rows, el=document.getElementById('scoreExplanation'),grid=document.querySelector('.score-grid'),cards=[...grid.querySelectorAll('.score-component')],clicked=grid.querySelector('[data-score="'+k+'"]'),idx=cards.indexOf(clicked);setText('scoreExplainTitle',title+' 점수 산정 근거');setText('scoreExplainWeight','매수여건 지수 가중치 '+w);document.getElementById('scoreExplainBody').innerHTML='<p class="score-rule">'+esc(desc)+'</p><div class="score-scale-guide">'+esc(detail.guide)+'</div><div class="score-detail-rows">'+rows.map(r=>'<div><span>'+esc(r[0])+'</span><b>'+esc(r[1])+'</b><small>'+esc(r[2])+'</small></div>').join('')+'</div><p class="score-note">미연결 데이터는 50점으로 임의 대체하지 않고 전체 신뢰도에서 제외합니다.</p>';if(grid&&clicked){let anchor=clicked;if(window.matchMedia('(max-width:800px)').matches&&idx>=0){const rowEnd=Math.min(cards.length-1,idx%2===0?idx+1:idx);anchor=cards[rowEnd]}grid.insertBefore(el,anchor.nextSibling)}el.hidden=false};
 document.querySelectorAll('.score-component').forEach(el=>{el.onclick=()=>open(el.dataset.score);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open(el.dataset.score)}}});
 document.getElementById('closeScoreExplain')?.addEventListener('click',()=>document.getElementById('scoreExplanation').hidden=true);
}

async function renderGarakGeumho24A(){
 const label=document.getElementById('garakHistoryLatest'),host=document.getElementById('garakHistoryChart'); if(!host)return;
 try{const r=await fetch('garak_geumho_24a_history.json?v=95',{cache:'no-store'});if(!r.ok)throw Error(r.status);const d=await r.json(),rows=(d.series||[]).filter(x=>Number(x.sale)).slice(-96);if(!rows.length)throw Error('empty');
 const latest=rows.at(-1);label.textContent=latest.ym.slice(0,4)+'.'+latest.ym.slice(4)+' · '+(latest.sale/10000).toFixed(2)+'억';
 const W=420,H=230,p={l:38,r:8,t:12,b:26},vals=rows.flatMap(x=>[+x.sale,+x.rent]).filter(v=>v>0),lo=Math.min(...vals)*.94,hi=Math.max(...vals)*1.04,X=i=>p.l+i*(W-p.l-p.r)/(rows.length-1),Y=v=>p.t+(hi-v)/(hi-lo)*(H-p.t-p.b);
 const poly=k=>rows.map((q,i)=>q[k]?X(i).toFixed(1)+','+Y(+q[k]).toFixed(1):'').filter(Boolean).join(' ');let g='',ticks='';
 for(let k=0;k<4;k++){const v=lo+(hi-lo)*k/3,y=Y(v);g+='<line class="garak-grid" x1="'+p.l+'" y1="'+y+'" x2="'+(W-p.r)+'" y2="'+y+'"/><text class="garak-axis" x="2" y="'+(y+3)+'">'+(v/10000).toFixed(1)+'</text>'}
 rows.forEach((q,i)=>{if(i%24===0||i===rows.length-1)ticks+='<text class="garak-axis" text-anchor="middle" x="'+X(i)+'" y="'+(H-7)+'">'+q.ym.slice(2,4)+'.'+q.ym.slice(4)+'</text>'});
 host.innerHTML='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none" role="img" aria-label="가락금호 24A KB 월별 매매 전세 시세">'+g+'<polyline class="garak-sale" points="'+poly('sale')+'"/><polyline class="garak-rent" points="'+poly('rent')+'"/>'+ticks+'</svg>';
 }catch(e){label.textContent='데이터 연결 실패';host.innerHTML='<div class="chart-error">차트 데이터를 불러오지 못했습니다.</div>'}
}
renderGarakGeumho24A();

async function renderConditionHistory(){
 const host=document.getElementById('conditionHistoryChart'),latestEl=document.getElementById('conditionHistoryLatest'),note=document.getElementById('conditionHistoryNote'),summary=document.getElementById('conditionHistorySummary'),controls=document.getElementById('conditionPeriods');if(!host)return;
 try{
  const r=await fetch('final_backtest.json?v='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error(r.status);
  const d=await r.json(),all=(d.rows||d.checkpoint_rows||[]).filter(x=>x.score!=null);if(!d.certified_final||!all.length)throw Error('not certified');
  let months=60;
  const currentScore=()=>{const n=parseFloat(document.getElementById('conditionScore')?.textContent||'');return Number.isFinite(n)?n:null};
  const draw=()=>{
   const rows=months?all.slice(-months):all,W=620,H=250,p={l:34,r:14,t:22,b:32},X=i=>p.l+i*(W-p.l-p.r)/Math.max(1,rows.length-1),Y=v=>p.t+(100-v)/100*(H-p.t-p.b);
   let grid='';[0,25,50,75,100].forEach(v=>{const y=Y(v);grid+='<line class="condition-grid" x1="'+p.l+'" y1="'+y+'" x2="'+(W-p.r)+'" y2="'+y+'"/><text class="condition-axis" x="2" y="'+(y+3)+'">'+v+'</text>'});
   const pts=rows.map((x,i)=>X(i).toFixed(1)+','+Y(+x.score).toFixed(1)).join(' ');
   let ticks='',turns='';rows.forEach((q,i)=>{if(i%Math.max(1,Math.floor(rows.length/4))===0||i===rows.length-1)ticks+='<text class="condition-axis" text-anchor="middle" x="'+X(i)+'" y="'+(H-7)+'">'+q.ym.slice(2,4)+'.'+q.ym.slice(4)+'</text>';if(i>1&&i<rows.length-2){const s=+q.score,prev=+rows[i-1].score,next=+rows[i+1].score;if((s<=prev&&s<next&&prev-s>=1)||(s>=prev&&s>next&&s-prev>=1))turns+='<circle class="condition-turn-dot" cx="'+X(i)+'" cy="'+Y(s)+'" r="4"/>'}});
   const cs=currentScore();let cur='';if(cs!=null){const x=W-p.r,y=Y(cs);cur='<line class="condition-current-guide" x1="'+x+'" y1="'+p.t+'" x2="'+x+'" y2="'+(H-p.b)+'"/><circle class="condition-current-dot" cx="'+x+'" cy="'+y+'" r="5"/><text class="condition-current-label" text-anchor="end" x="'+(x-7)+'" y="'+(y-8)+'">현재 '+Math.round(cs)+'</text>'}
   host.innerHTML='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="월별 매수여건 점수">'+grid+'<polyline class="condition-line" points="'+pts+'"/>'+turns+ticks+cur+'<line id="conditionTouchLine" class="condition-touch-line" visibility="hidden"/><circle id="conditionTouchDot" class="condition-touch-dot" r="6" visibility="hidden"/></svg><div id="conditionTooltip" class="condition-tooltip" hidden></div>';
   const svg=host.querySelector('svg'),tip=host.querySelector('#conditionTooltip'),line=host.querySelector('#conditionTouchLine'),dot=host.querySelector('#conditionTouchDot');
   const inspect=e=>{const rect=svg.getBoundingClientRect(),cx=(e.touches?.[0]?.clientX??e.clientX)-rect.left,xView=cx/rect.width*W,idx=Math.max(0,Math.min(rows.length-1,Math.round((xView-p.l)/(W-p.l-p.r)*(rows.length-1)))),q=rows[idx],x=X(idx),y=Y(+q.score);line.setAttribute('x1',x);line.setAttribute('x2',x);line.setAttribute('y1',p.t);line.setAttribute('y2',H-p.b);line.setAttribute('visibility','visible');dot.setAttribute('cx',x);dot.setAttribute('cy',y);dot.setAttribute('visibility','visible');tip.hidden=false;tip.innerHTML='<b>'+q.ym.slice(0,4)+'.'+q.ym.slice(4)+'</b><strong>'+q.score+'/100</strong>';tip.style.left=Math.min(78,Math.max(6,x/W*100))+'%';tip.style.top=Math.max(8,y/H*100-4)+'%'};
   svg.addEventListener('pointerdown',inspect);svg.addEventListener('pointermove',e=>{if(e.buttons)inspect(e)});svg.addEventListener('touchstart',inspect,{passive:true});svg.addEventListener('touchmove',inspect,{passive:true});
   const last=rows.at(-1),first=rows[0],delta=(+last.score-+first.score).toFixed(1),peak=rows.reduce((a,b)=>+a.score>+b.score?a:b),low=rows.reduce((a,b)=>+a.score<+b.score?a:b);
   latestEl.textContent=last.ym.slice(0,4)+'.'+last.ym.slice(4)+' · '+last.score+'/100';
   summary.innerHTML='<b>현재 '+last.score+'점</b><span>'+rows.length+'개월 전 대비 '+(+delta>=0?'+':'')+delta+'점 · 기간 저점 '+low.score+' ('+low.ym.slice(2,4)+'.'+low.ym.slice(4)+') · 고점 '+peak.score+' ('+peak.ym.slice(2,4)+'.'+peak.ym.slice(4)+')</span>';
   note.textContent=rows.length+'개월 표시 · 점/선을 누르면 해당 월 수치 확인 · 주요 국지 고점·저점 표시';
  };
  controls?.querySelectorAll('button').forEach(b=>b.onclick=()=>{controls.querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');months=+b.dataset.months;draw()});draw();
 }catch(e){latestEl.textContent='인증 데이터 대기';host.innerHTML='<div class="chart-error">최종 인증 파일이 배포되면 자동으로 표시됩니다.</div>'}
}
renderConditionHistory();
