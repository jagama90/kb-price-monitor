'use strict';const eok=n=>n==null?'—':(Number(n)/10000).toLocaleString('ko-KR',{maximumFractionDigits:2})+'억';const KB_HISTORY=[{d:'2026-09-05',avg:198849,n:43},{d:'2026-09-11',avg:190818,n:11}];function renderKbHistory(){const a=KB_HISTORY;if(!a.length)return;const vals=a.map(x=>x.avg),lo=Math.floor((Math.min(...vals)-10000)/10000)*10000,hi=Math.ceil((Math.max(...vals)+10000)/10000)*10000,range=Math.max(1,hi-lo);document.querySelector('#kbYAxis').innerHTML=[hi,hi-(range/3),hi-(range*2/3),lo].map(v=>'<b>'+eok(v)+'</b>').join('');const pts=a.map((x,i)=>{const px=a.length===1?210:i*420/(a.length-1),py=160-((x.avg-lo)/range)*150;return px.toFixed(1)+','+py.toFixed(1)}).join(' ');document.querySelector('#kbSvg').innerHTML='<line x1="0" y1="10" x2="420" y2="10"/><line x1="0" y1="60" x2="420" y2="60"/><line x1="0" y1="110" x2="420" y2="110"/><line x1="0" y1="160" x2="420" y2="160"/><polyline class="mainline" points="'+pts+'"/>'+a.map((x,i)=>{const px=a.length===1?210:i*420/(a.length-1),py=160-((x.avg-lo)/range)*150;return '<circle cx="'+px+'" cy="'+py+'" r="4" fill="#1677ff"/>'}).join('');document.querySelector('#kbXAxis').innerHTML=a.map(x=>'<span>'+x.d.slice(5).replace('-','/')+'</span>').join('');document.querySelector('#kbHistoryNote').textContent='DB 실데이터 '+a.length+'회 · '+a[0].d+' ~ '+a[a.length-1].d+' · 표본 '+a.map(x=>x.n+'건').join(' / ')};renderKbHistory();const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const signal=x=>{const d=Number(x.sale_listing_week_delta||0),t=x.recent_trade_manwon&&x.avg_ask_manwon?Number(x.recent_trade_manwon)-Number(x.avg_ask_manwon):0;if(d>0&&t<0)return['하락','down'];if(d<0&&t>=0)return['상승','up'];return['관찰','watch']};async function load(){const [m,k,tg]=await Promise.all([fetch('buy_watchlist_market.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),fetch('buy_watchlist_master.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),fetch('buy_watchlist_targets.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json())]);const market=m.items||[],master=k.items||[],targets=tg.items||[];const masterById=new Map(master.map(x=>[Number(x.complex_id),x]));
const hubWatch=document.getElementById('hubWatchMeta');if(hubWatch){const traded=market.filter(x=>x.recent_trade_manwon!=null).length;hubWatch.textContent=market.length+'개 연결 · 실거래 '+traded+'개'}
const kbKey=x=>Number(x.complex_id)+':'+Number(x.area_id);const kb=new Map(market.map(x=>{const z=masterById.get(Number(x.complex_id)),t=(z?.types||[]).find(a=>Number(a.area_id)===Number(x.area_id)),p=t?.general_price_manwon;return [kbKey(x),p==null?null:Number(p)]}));document.querySelector('#updated').textContent='KB '+new Date(k.kb_collected_at||Date.now()).toLocaleDateString('ko-KR')+' · MARKET '+new Date(m.collected_at||Date.now()).toLocaleDateString('ko-KR');const collected=new Date(m.collected_at||Date.now()), collectedText=collected.toLocaleString('ko-KR',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});document.querySelector('#marketDate').textContent=collected.toLocaleDateString('ko-KR');const norm=s=>String(s||'').replace(/\s|아파트|\(|\)|마천역/g,'');const targetMap=new Map(targets.map(t=>[norm(t.name),t]));const preferred=x=>{const t=targetMap.get(norm(x.user_name||x.kb_name)),types=x.types||[];if(!t||t.min_pyeong==null)return types;return types.filter(a=>{const m=String(a.type_label||'').match(/\d+(?:\.\d+)?/);return m&&Number(m[0])>=Number(t.min_pyeong)&&Number(m[0])<=Number(t.max_pyeong)})};let boundary=[...master].map(x=>{const a=preferred(x).filter(t=>Number(t.general_price_manwon));if(!a.length)return null;const z=a.reduce((p,c)=>Math.abs(Number(c.general_price_manwon)-150000)<Math.abs(Number(p.general_price_manwon)-150000)?c:p);return{name:x.user_name||x.kb_name,p:Number(z.general_price_manwon),type:z.type_label}}).filter(Boolean).filter(x=>x.p>=130000&&x.p<=170000).sort((a,b)=>Math.abs(a.p-150000)-Math.abs(b.p-150000)).slice(0,7);const boundaryEl=document.querySelector('#boundary');let boundaryMode='near';const renderBoundary=()=>{const a=[...boundary].sort((x,y)=>boundaryMode==='asc'?x.p-y.p:boundaryMode==='desc'?y.p-x.p:Math.abs(x.p-150000)-Math.abs(y.p-150000));boundaryEl.innerHTML='<div class="mini-sort"><button data-b="near" class="'+(boundaryMode==='near'?'active':'')+'">15억 근접</button><button data-b="asc" class="'+(boundaryMode==='asc'?'active':'')+'">낮은순</button><button data-b="desc" class="'+(boundaryMode==='desc'?'active':'')+'">높은순</button></div>'+ (a.map(x=>'<div class="row"><span>'+esc(x.name)+' <small>'+esc(x.type)+'평</small></span><b class="'+(x.p<=150000?'up':'')+'">'+eok(x.p)+'</b></div>').join('')||'<small>13~17억 구간 데이터 없음</small>');boundaryEl.querySelectorAll('[data-b]').forEach(b=>b.onclick=()=>{boundaryMode=b.dataset.b;renderBoundary()})};renderBoundary();const radarBase=[...market].filter(x=>x.sale_listing_week_delta!=null&&Number(x.sale_listing_week_delta)!==0);let radarMode='abs';const radarEl=document.querySelector('#radar');const renderRadar=()=>{const radar=[...radarBase].sort((a,b)=>radarMode==='up'?Number(b.sale_listing_week_delta)-Number(a.sale_listing_week_delta):radarMode==='down'?Number(a.sale_listing_week_delta)-Number(b.sale_listing_week_delta):Math.abs(Number(b.sale_listing_week_delta))-Math.abs(Number(a.sale_listing_week_delta))).slice(0,7);radarEl.innerHTML='<small class="radar-period">최근 수집 '+collectedText+' · 직전 주간 스냅샷 대비</small><div class="mini-sort"><button data-r="abs" class="'+(radarMode==='abs'?'active':'')+'">변동폭</button><button data-r="up" class="'+(radarMode==='up'?'active':'')+'">증가순</button><button data-r="down" class="'+(radarMode==='down'?'active':'')+'">감소순</button></div>'+(radar.length?radar.map(x=>'<div class="radar-row"><span>'+esc(x.name)+'</span><b class="'+(x.sale_listing_week_delta>0?'down':'up')+'">'+(x.sale_listing_week_delta>0?'+':'')+Number(x.sale_listing_week_delta)+'건</b></div>').join(''):'<small class="no-change">변동이 있는 단지가 없습니다.</small>');radarEl.querySelectorAll('[data-r]').forEach(b=>b.onclick=()=>{radarMode=b.dataset.r;renderRadar()})};renderRadar();const priceOf=x=>Number(kb.get(kbKey(x)))||Number(x.avg_ask_manwon)||Number(x.recent_trade_manwon)||Infinity;const rows=[...market].sort((a,b)=>{const da=Math.abs(priceOf(a)-150000),db=Math.abs(priceOf(b)-150000);return da-db||priceOf(b)-priceOf(a)});const unavailableCount=(m.known_unavailable_targets||[]).length;document.querySelector('#summary').textContent=market.length+'개 연결'+(unavailableCount?' · '+unavailableCount+'개 입주 전':'')+' · KB · 실거래 · 매물';document.querySelector('#body').innerHTML=rows.map(x=>{const s=signal(x),lc=x.sale_listing_count==null?'—':Number(x.sale_listing_count).toLocaleString()+'건',wd=x.sale_listing_week_delta==null?'—':(x.sale_listing_week_delta>0?'+':'')+Number(x.sale_listing_week_delta)+'건';return'<tr><td><b>'+esc(x.name)+'</b><small> '+esc(x.type_label||'')+'평</small></td><td>'+eok(kb.get(kbKey(x)))+'</td><td>'+eok(x.recent_trade_manwon)+'<small> '+esc(x.recent_trade_date||'')+'</small></td><td>'+eok(x.avg_ask_manwon)+'</td><td>'+lc+'</td><td class="'+(x.sale_listing_week_delta>0?'down':x.sale_listing_week_delta<0?'up':'')+'">'+wd+'</td><td><span class="pill '+s[1]+'">'+s[0]+'</span></td></tr>'}).join('');document.querySelector('#mobileCards').innerHTML=rows.map(x=>{const s=signal(x),lc=x.sale_listing_count==null?'—':Number(x.sale_listing_count)+'건',wd=x.sale_listing_week_delta==null?'—':(x.sale_listing_week_delta>0?'+':'')+Number(x.sale_listing_week_delta)+'건';return'<article class="complex"><div class="complex-head"><b>'+esc(x.name)+' <small>'+esc(x.type_label||'')+'평</small></b><span class="pill '+s[1]+'">'+s[0]+'</span></div><div class="complex-grid"><div><span>KB시세</span><b>'+eok(kb.get(kbKey(x)))+'</b></div><div><span>최근 실거래</span><b>'+(x.recent_trade_manwon==null?'확인 대기':eok(x.recent_trade_manwon))+'</b></div><div><span>매물 평균</span><b>'+(x.avg_ask_manwon==null?'원천 미연결':eok(x.avg_ask_manwon))+'</b></div><div><span>매매 매물</span><b>'+lc+'</b></div><div><span>주간 증감</span><b class="'+(x.sale_listing_week_delta>0?'down':x.sale_listing_week_delta<0?'up':'')+'">'+wd+'</b></div><div><span>최근 거래일</span><b>'+esc(x.recent_trade_date||'—')+'</b></div></div></article>'}).join('')+'<button id="moreComplexes" class="more-btn">↓ 더보기 ('+Math.max(0,rows.length-5)+'개)</button>';const mc=document.querySelector('#mobileCards'),mb=document.querySelector('#moreComplexes');if(rows.length<=5)mb.style.display='none';mb.addEventListener('click',()=>{const open=mc.classList.toggle('expanded');mb.textContent=open?'↑ 접기':'↓ 더보기 ('+Math.max(0,rows.length-5)+'개)'})}load().catch(e=>{document.querySelector('#updated').textContent='관심단지 일부 데이터 확인 필요';console.error(e)});
async function loadMarketIndicators(){
 try{
  const d=await fetch('market_indicators.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json());
  const vols=d.seoul_apt_trade_count||[];
  if(vols.length){const z=vols[vols.length-1];setText('snapVolume',Number(z[1]).toLocaleString('ko-KR')+'건');setText('snapVolumePeriod',z[0]+(z[2]?' · 신고 진행':' · 집계'))}
  const bands=d.price_bands?.months||[],latest=bands[bands.length-1];
  if(latest){setText('snapUnder15',latest.under15_share+'%');const ids={'b9':'<=9eok','b15':'9-15eok','b25':'15-25eok','b25p':'25eok+'};Object.entries(ids).forEach(([id,k])=>setText(id,Number(latest.counts?.[k]||0).toLocaleString('ko-KR')+'건'))}
  const m=d.m2_official||d.m2;if(m){setText('snapM2',m.yoy_pct==null?'—':m.yoy_pct+'%');setText('snapM2Period',m.period+' · 한국은행 ECOS');setText('m2Detail','ECOS 동일 M2 수준계열 기준 · 전월비 '+(m.mom_pct??'—')+'% · 전년비 '+(m.yoy_pct??'—')+'%')}
  if(d.matched_period){const x=d.matched_period,c=x.current,p=x.previous,fmt=v=>v==null?'—':Number(v).toLocaleString('ko-KR');setText('matchedRange',p.period+' '+p.range+' ↔ '+c.period+' '+c.range+' · 계약일 기준');setText('matchedVolume',fmt(p.total)+' → '+fmt(c.total)+'건');setText('matchedVolumeDelta',x.changes?.trade_count_pct==null?'증감 계산 대기':signed(x.changes.trade_count_pct,'%')+' · 당월 신고 진행');setText('matchedUnder15',(p.under15_share??'—')+' → '+(c.under15_share??'—')+'%');setText('matchedUnder15Delta',x.changes?.under15_share_pp==null?'증감 계산 대기':signed(x.changes.under15_share_pp,'%p'));const hv=document.getElementById('hubValidationMeta');if(hv)hv.textContent='거래 '+(x.changes?.trade_count_pct==null?'—':signed(x.changes.trade_count_pct,'%'))+' · ≤15억 '+(c.under15_share??'—')+'%'}
  window.__marketIndicators=d;
  renderKbOfficial(d);
  renderConditionIndex(d);
  setupScoreDetails(d,window.__conditionComponents||{});
  renderLeadChanges();
  setupSnapshotEvidence(d);
  const updated=document.querySelector('#updated');if(updated&&/LOADING|DATA ERROR|관심단지 일부/.test(updated.textContent))updated.textContent='MARKET '+(d.updated_at||new Date().toLocaleDateString('ko-KR'));
 }catch(e){console.error(e)}
}
const setText=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v};
function setupScoreDetails(d,components){
 window.__marketIndicators=d;
 window.__conditionComponents=components||{};
 document.querySelectorAll('.score-component[data-score-key]').forEach(card=>{
  card.setAttribute('role','button');
  card.setAttribute('tabindex','0');
  card.setAttribute('aria-expanded','false');
  card.setAttribute('aria-controls','scoreExplanation');
 });
}
function setupSnapshotEvidence(d){
 const x=d.matched_period;
 const open=(title,source,current,previous,delta,note,formula)=>{setText('snapshotExplainTitle',title);setText('snapshotExplainSource',source);document.getElementById('snapshotExplainBody').innerHTML='<div class="evidence-compare"><div><small>현재 동일기간</small><b>'+esc(current[0])+'</b><span>'+esc(current[1])+'</span></div><div><small>직전월 동일기간</small><b>'+esc(previous[0])+'</b><span>'+esc(previous[1])+'</span></div></div><div class="evidence-change"><div><span>변화</span><b>'+esc(delta)+'</b></div><p>'+esc(note)+'</p></div><div class="evidence-method"><b>산출 기준</b><p>'+esc(formula)+'</p></div>';const el=document.getElementById('snapshotExplanation');el.hidden=false};
 const bind=(id,fn)=>{const el=document.getElementById(id);if(!el)return;el.onclick=fn;el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fn()}}};
 if(x){bind('volumeCard',()=>open('서울 거래량','국토교통부 실거래가 · 계약일 기준',[Number(x.current.total).toLocaleString('ko-KR')+'건',x.current.period+' '+x.current.range],[Number(x.previous.total).toLocaleString('ko-KR')+'건',x.previous.period+' '+x.previous.range],signed(x.changes.trade_count_pct,'%'),x.warning||'당월 신고 진행 중','현재월과 직전월을 같은 달력일 구간으로 맞춰 계약 건수를 비교합니다.'));bind('under15Card',()=>open('15억 이하 비중','국토교통부 실거래가 · 서울 아파트',[x.current.under15_share+'%',x.current.period+' '+x.current.range],[x.previous.under15_share+'%',x.previous.period+' '+x.previous.range],signed(x.changes.under15_share_pp,'%p'),'중저가 거래 비중의 월간 이동','15억원 이하 거래건수 ÷ 해당 동일기간 서울 아파트 전체 거래건수 × 100'))}
 const m=d.m2_official||d.m2;
 bind('rateCard',()=>open('기준금리','한국은행 기준금리',['3.00%','2026.08.27'],['3.00%','직전 결정'], '0.0%p','현재 기준금리 수준','한국은행 금융통화위원회 기준금리 결정값을 표시합니다.'));
 if(m)bind('m2Card',()=>open('M2 통화량','한국은행 ECOS 101Y003',[Number(m.yoy_pct).toFixed(1)+'%','전년동월비 · '+m.period],[Number(m.mom_pct).toFixed(1)+'%','전월비'],signed(m.yoy_pct,'%'),'광의통화 증가율','M2 원계열의 전년동월비와 전월비를 함께 확인합니다.'));
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
 Object.entries(labels).forEach(([k,id])=>{
  setText(id,components[k]==null?'미연결':Math.round(components[k])+'/100');
  const card=document.querySelector('[data-score="'+k+'"]');
  if(card)card.style.setProperty('--score',components[k]==null?0:Math.round(components[k]));
 });
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
 const hubDrivers=document.getElementById('hubDriversMeta');
 if(hubDrivers)hubDrivers.textContent='금융 '+(finance==null?'—':Math.round(finance))+' · 심리 '+(sent==null?'—':Math.round(sent));
 const stateLabel=s=>s[0]==='우호적'?'개선 신호':s[0]==='제약'?'제약 신호':s[0]==='중립'?'중립 구간':'미연결';
 [['Finance',fs],['Sentiment',ss],['Demand',ds],['Value',vs],['Supply',sup]].forEach(([id,s])=>{setText('state'+id,stateLabel(s));const el=document.getElementById('state'+id);if(el)el.className='component-state '+s[1]});
 const connected=[finance,sent,demand,value,components.supply].filter(v=>v!=null);
 const weak=connected.filter(v=>v<45).length,strong=connected.filter(v=>v>=55).length;
 setText('heroVerdict',weak>=3?'아직은 제약 신호가 우세합니다. 반전 확인이 필요한 구간입니다.':strong>=3?'개선 신호가 여러 단계에서 확인되고 있습니다. 지속성을 확인할 구간입니다.':'개선과 제약 신호가 엇갈립니다. 다음 단계로의 전달을 확인할 구간입니다.');
 [['Finance',fs],['Sentiment',ss],['Demand',ds],['Value',vs]].forEach(([id,state])=>{setText('path'+id,state[0]);const el=document.getElementById('node'+id);if(el)el.className='flow-step-v4 '+state[1]});
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
function renderLeadChanges(){
 const lc=window.__conditionComponents||{},hist=window.__conditionHistoryRows||[],prev=hist.length?hist[hist.length-1]:null;
 const delta=(k,now)=>prev&&Number.isFinite(+prev.components?.[k])?now-(+prev.components[k]):null,fmt=v=>v==null?'이력 연결 중':(v>0?'↑ +':v<0?'↓ ':'→ ')+v.toFixed(1);
 const lead=(id,val)=>{const e=document.getElementById(id);if(e)e.textContent=val;const n=document.getElementById(id+'Note');if(n)n.textContent='최근 완료월 대비 현재 진행월'};
 if(!['finance','sentiment','supply','demand'].every(k=>Number.isFinite(lc[k])))return;
 const ds={finance:delta('finance',lc.finance),sentiment:delta('sentiment',lc.sentiment),supply:delta('supply',lc.supply),demand:delta('demand',lc.demand)};
 lead('leadFinance',fmt(ds.finance));lead('leadSentiment',fmt(ds.sentiment));lead('leadJeonse',fmt(ds.supply));lead('leadDemand',fmt(ds.demand));
 const vv=Object.values(ds).filter(Number.isFinite),up=vv.filter(x=>x>0).length,down=vv.filter(x=>x<0).length,lv=document.getElementById('leadVerdict'),ln=document.getElementById('leadVerdictNote');
 if(lv)lv.textContent=vv.length<3?'변화 이력을 연결하는 중':up>=3?'개선 신호가 여러 단계로 확산':down>=3?'여러 선행신호가 함께 약화':'개선과 약화가 엇갈리는 변곡 구간';
 if(ln)ln.textContent=vv.length?('최근 완료월 대비 현재 진행월: '+up+'개 개선 · '+down+'개 약화'):'현재 수준을 반복하지 않고 변화만 표시합니다.';
}
async function renderConditionHistory(){
 const host=document.getElementById('conditionHistoryChart'),latestEl=document.getElementById('conditionHistoryLatest'),note=document.getElementById('conditionHistoryNote'),summary=document.getElementById('conditionHistorySummary'),controls=document.getElementById('conditionPeriods');if(!host)return;
 try{
  const r=await fetch('final_backtest.json?v='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error(r.status);
  const d=await r.json(),all=(d.rows||d.checkpoint_rows||[]).filter(x=>x.score!=null);window.__conditionHistoryRows=all;if(!d.certified_final||!all.length)throw Error('not certified');
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
  controls?.querySelectorAll('button').forEach(b=>b.onclick=()=>{controls.querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');months=+b.dataset.months;draw()});draw();renderLeadChanges();
 }catch(e){latestEl.textContent='인증 데이터 대기';host.innerHTML='<div class="chart-error">최종 인증 파일이 배포되면 자동으로 표시됩니다.</div>'}
}
renderConditionHistory();

async function renderCycleStage(){ // direction-aware market phase UI
 const badge=document.getElementById('cycleStageBadge');if(!badge)return;
 try{const d=await fetch('turning_signal_research.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),rows=d.rows||[],x=rows.at(-1),prev=rows.at(-2);if(!x)throw Error('no rows');
  const m1=Number(x.price_mom_pct),m3=Number(x.momentum_3m_pct),prev3=Number(prev?.momentum_3m_pct),recent=rows.slice(-4,-1),wasRising=recent.some(r=>Number(r.momentum_3m_pct)>0);
  let stage=0,label='하락 중',text='가격 하락 흐름이 이어지고 있습니다. 아직 하락이 멈췄다고 보기 어렵습니다.';
  if(x.bottom_zone){stage=1;label='하락 둔화';text='하락 압력이 약해지고 있습니다. 다만 아직 가격이 멈췄거나 상승세로 바뀌었다고 보기는 이릅니다.'}
  if(m1>=0&&m3<=0&&!wasRising){stage=2;label='바닥 확인 중';text='하락 뒤 가격이 더 내려가지 않고 있습니다. 과거 검증상 매수 타이밍을 살펴볼 가치가 높아지는 구간이지만 아직 상승 확인 전입니다.'}
  if(m3>0){stage=3;label='상승 확인';text='최근 3개월 가격 흐름이 상승입니다. 상승 흐름이 이어지는지 확인하는 단계입니다.'}
  if(wasRising&&m3<=0&&m1>=0){stage=3;label='상승 후 보합';text='앞선 상승세가 멈추고 최근 가격이 보합권에 들어왔습니다. 하락 뒤 바닥 신호가 아니라 상승 모멘텀이 식은 상태입니다.'}
  if(x.momentum_zone){stage=4;label='상승 가속';text='가격 상승과 시장 수요가 함께 강해지는 구간입니다.'}
  badge.textContent=label;document.getElementById('cycleStageText').textContent=text;
  const flow=m3>0?'상승 '+m3.toFixed(1)+'%':m3<0?'하락 '+Math.abs(m3).toFixed(1)+'%':'보합';
  document.getElementById('cycleStageEvidence').textContent='최근 데이터 '+x.ym.slice(0,4)+'.'+x.ym.slice(4)+' · 최근 3개월 가격 '+flow;
  document.querySelectorAll('#cycleSteps span').forEach((e,i)=>e.classList.toggle('active',i===stage));
 }catch(e){badge.textContent='데이터 확인 중';document.getElementById('cycleStageText').textContent='최신 가격 데이터를 확인하고 있습니다.'}}
renderCycleStage();

window.showScoreDetail=function(k){
 const d=window.__marketIndicators,c=window.__conditionComponents||{};if(!d||c[k]==null)return;
 const w={finance:25,sentiment:20,demand:20,value:20,supply:15},t={finance:'금융여건',sentiment:'시장심리',demand:'실수요·거래',value:'가격·밸류',supply:'공급·전세'},m=d.m2_official||d.m2,x=d.matched_period,s=d.kb_sentiment||{},v=d.kb_value||{},val=z=>z==null?'—':Number(z).toFixed(1),body={
  finance:'현재 '+Math.round(c.finance)+'/100 · M2 전월비 '+val(m?.mom_pct)+'% · 전년비 '+val(m?.yoy_pct)+'%<br><b>산식</b> 50 + M2 전월비×8 + M2 전년비×1.5',
  sentiment:'현재 '+Math.round(c.sentiment)+'/100 · 매수우위 '+val(s.latest?.매수우위?.value)+' · 거래활발 '+val(s.latest?.매매거래활발?.value),
  demand:'현재 '+Math.round(c.demand)+'/100 · 동일기간 거래 '+(x?.changes?.trade_count_pct==null?'—':signed(x.changes.trade_count_pct,'%'))+' · ≤15억 비중 '+(x?.changes?.under15_share_pp==null?'—':signed(x.changes.under15_share_pp,'%p')),
  value:'현재 '+Math.round(c.value)+'/100 · 현재 KB '+eok(v.current_manwon)+' · 36개월 저점 '+eok(v.window_low_manwon)+' · 고점 '+eok(v.window_high_manwon),
  supply:'현재 '+Math.round(c.supply)+'/100 · 전세수급 '+val(s.latest?.전세수급?.value)+' · 전세거래활발 '+val(s.latest?.전세거래활발?.value)
 };
 setText('scoreExplainTitle',t[k]+' 산출근거');setText('scoreExplainWeight','전체 점수 가중치 '+w[k]+'%');
 const bodyEl=document.getElementById('scoreExplainBody'),p=document.getElementById('scoreExplanation');if(!bodyEl||!p)return;
 bodyEl.innerHTML='<p>'+body[k]+'</p>';p.hidden=false;p.style.display='block';
 document.querySelectorAll('.score-component[data-score-key]').forEach(card=>{const on=card.dataset.scoreKey===k;card.setAttribute('aria-expanded',on?'true':'false');card.classList.toggle('active',on)});
 p.scrollIntoView({behavior:'smooth',block:'center'});
};
window.hideScoreDetail=function(){
 const p=document.getElementById('scoreExplanation');if(p){p.hidden=true;p.style.display='none'}
 document.querySelectorAll('.score-component[data-score-key]').forEach(card=>{card.setAttribute('aria-expanded','false');card.classList.remove('active')});
};

async function renderRegimeForecast(){
 const host=document.getElementById('forecastGrid'),meta=document.getElementById('forecastMeta'),headline=document.getElementById('forecastHeadline'),trend=document.getElementById('forecastTrend');if(!host)return;
 const labels={consolidation:'보합·조정',reacceleration:'상승 재가속',downturn:'하락 전환'};
 const short={consolidation:'보합',reacceleration:'재가속',downturn:'하락'};
 const fmtMonth=v=>{const z=String(v||'');return z.length===6?z.slice(0,4)+'.'+z.slice(4):z};
 try{
  const d=await fetch('regime_forecast.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('forecast '+r.status);return r.json()});
  const hs=d.horizons||[];
  const dominant=h=>Object.entries(h.weights||{}).sort((a,b)=>Number(b[1])-Number(a[1]))[0]?.[0]||h.base_case||'consolidation';
  const phrase=(h,i)=>{
   const w=h.weights||{},vals=Object.values(w).map(Number),spread=vals.length?Math.max(...vals)-Math.min(...vals):99,top=dominant(h);
   if(i===1&&spread<10)return '혼조·분기점';
   if(i===2&&hs[0]&&Number(w.reacceleration||0)>Number(hs[0].weights?.reacceleration||0)&&Number(w.downturn||0)<Number(hs[0].weights?.downturn||0))return '재상승 가능성 확대';
   if(i===0&&top==='consolidation'&&Number(w.downturn||0)>=Number(w.consolidation||0)-8)return '쉬어가기·하방 경계';
   return labels[top]||top;
  };
  host.innerHTML=hs.map((h,i)=>{
   const w=h.weights||{},top=dominant(h),topv=Number(w[top]||0);
   return '<div class="forecast-stop state-'+top+'"><div class="forecast-stop-head"><small>'+esc(h.label||h.period)+'</small><span>'+topv.toFixed(1)+'</span></div><b>'+esc(phrase(h,i))+'</b><div class="scenario-rail" aria-label="시나리오 가중치"><i class="scenario-flat" style="width:'+Number(w.consolidation||0)+'%"></i><i class="scenario-up" style="width:'+Number(w.reacceleration||0)+'%"></i><i class="scenario-down" style="width:'+Number(w.downturn||0)+'%"></i></div><div class="forecast-mini-values"><span>보합 '+Number(w.consolidation||0).toFixed(0)+'</span><span>재가속 '+Number(w.reacceleration||0).toFixed(0)+'</span><span>하락 '+Number(w.downturn||0).toFixed(0)+'</span></div></div>'
  }).join('');
  if(headline&&hs.length)headline.textContent=hs.map((h,i)=>phrase(h,i)).join(' → ');
  if(trend&&hs.length>=2){const a=hs[0].weights||{},z=hs[hs.length-1].weights||{},du=Number(z.reacceleration||0)-Number(a.reacceleration||0),dd=Number(z.downturn||0)-Number(a.downturn||0);trend.innerHTML='<span class="trend-chip trend-up">재가속 '+(du>=0?'＋':'')+du.toFixed(1)+'%p</span><span class="trend-chip trend-down">하락 '+(dd>=0?'＋':'')+dd.toFixed(1)+'%p</span>'}
  meta.textContent='연구 '+fmtMonth(d.latest_research_month)+(d.latest_research_provisional?' 잠정':'')+' · 인증 '+fmtMonth(d.latest_certified_backtest_month)+'까지';
  const hb=document.getElementById('hubBacktestMeta');if(hb)hb.textContent='인증 '+fmtMonth(d.latest_certified_backtest_month)+' · 연구 '+fmtMonth(d.latest_research_month);
 }catch(e){host.innerHTML='<div class="forecast-stop"><small>전망엔진</small><b>데이터 확인 중</b></div>';if(headline)headline.textContent='최신 전망 데이터를 확인하고 있습니다.';meta.textContent='전망 파일 배포 후 자동 표시됩니다.'}
}
renderRegimeForecast();

// Score cards themselves are the controls; no separate "점수 근거 보기" button.
document.addEventListener('click',e=>{
 if(e.target.closest?.('.score-detail-close')){e.preventDefault();window.hideScoreDetail?.();return}
 const card=e.target.closest?.('.score-component[data-score-key]');
 if(card){e.preventDefault();window.showScoreDetail?.(card.dataset.scoreKey)}
});
document.addEventListener('keydown',e=>{
 const card=e.target.closest?.('.score-component[data-score-key]');
 if(card&&(e.key==='Enter'||e.key===' ')){e.preventDefault();window.showScoreDetail?.(card.dataset.scoreKey)}
});

async function loadGarakHistory(){
 const host=document.getElementById('garakHistoryChart'),latest=document.getElementById('garakHistoryLatest');if(!host)return;
 try{
  const d=await fetch('garak_geumho_24a_history.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('history '+r.status);return r.json()});
  const rows=(d.series||[]).filter(x=>x.ym&&(x.sale!=null||x.rent!=null));
  if(rows.length<2)throw Error('history rows missing');
  const W=760,H=220,L=58,R=16,T=14,B=30,vals=rows.flatMap(x=>[x.sale,x.rent]).filter(v=>v!=null).map(Number);
  let lo=Math.min(...vals),hi=Math.max(...vals),pad=Math.max(5000,(hi-lo)*.08);lo=Math.max(0,lo-pad);hi+=pad;const range=Math.max(1,hi-lo);
  const x=i=>L+(W-L-R)*(i/(rows.length-1)),y=v=>T+(H-T-B)*(1-(Number(v)-lo)/range);
  const pts=key=>rows.map((r,i)=>r[key]==null?null:[x(i),y(r[key])]).filter(Boolean).map(p=>p.map(n=>n.toFixed(1)).join(',')).join(' ');
  const ticks=[0,.25,.5,.75,1].map(q=>hi-(hi-lo)*q);
  const grids=ticks.map((v,i)=>{const yy=T+(H-T-B)*(i/4);return '<line class="garak-grid" x1="'+L+'" y1="'+yy+'" x2="'+(W-R)+'" y2="'+yy+'"/><text class="garak-axis" x="4" y="'+(yy+4)+'">'+(v/10000).toFixed(v>=100000?1:2)+'억</text>'}).join('');
  const years=[];let last='';
  rows.forEach((r,i)=>{const yr=String(r.ym).slice(0,4);if(yr!==last&&(i===0||Number(yr)%4===0||i===rows.length-1)){years.push('<text class="garak-axis" text-anchor="middle" x="'+x(i).toFixed(1)+'" y="'+(H-6)+'">'+yr+'</text>');last=yr}});
  host.innerHTML='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none">'+grids+'<polyline class="garak-sale" points="'+pts('sale')+'"/><polyline class="garak-rent" points="'+pts('rent')+'"/>'+years.join('')+'</svg>';
  const z=rows[rows.length-1];latest.textContent=z.ym.slice(0,4)+'.'+z.ym.slice(4)+' · 매매 '+eok(z.sale)+' · 전세 '+eok(z.rent)+(d.refresh_status==='fallback_last_good'?' · LAST GOOD':'');
  latest.title='KB 월별 원자료 '+rows.length+'개월 · '+rows[0].ym+'~'+z.ym;
 }catch(e){host.innerHTML='<div class="chart-error">장기 추이 데이터를 불러오지 못했습니다.</div>';latest.textContent='데이터 확인 필요';console.error(e)}
}
loadGarakHistory();

async function loadMarketExtensions(){
 const host=document.getElementById('marketContext');if(!host)return;
 const set=(id,v)=>{const el=document.getElementById(id);if(el)el.textContent=v};
 const pct=v=>v==null?'—':(Number(v)>0?'+':'')+Number(v).toFixed(2)+'%';
 const pp=v=>v==null?'—':(Number(v)>0?'+':'')+Number(v).toFixed(2)+'%p';
 try{
  const d=await fetch('market_extensions.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('extensions '+r.status);return r.json()});
  const b=d.current?.breadth||{},s25=b.seoul_25||{},g3=b.gangnam3||{},ng=b.non_gangnam3||{},songpa=b.songpa||{};
  const up=Number(s25.up_share_pct||0);
  set('breadthHeadline',(s25.up??'—')+'/'+(s25.count??25)+'개구 상승');
  set('breadthGangnam','강남3구 '+(g3.up??'—')+'/'+(g3.count??3)+'↑');
  set('breadthNonGangnam','비강남 '+(ng.up??'—')+'/'+(ng.count??22)+'↑');
  set('breadthSongpa','송파 '+pct(songpa.change_pct));
  const fill=document.getElementById('breadthFill');if(fill)fill.style.width=Math.max(0,Math.min(100,up))+'%';
  set('contextBreadthBadge',up>=75?'확산 강함':up>=45?'확산 혼조':'확산 약함');

  const t=d.current?.temperature||{},sg=Number(t.songpa_vs_seoul_gap_pp);
  set('tempSeoul',pct(t.seoul_m3_pct));
  set('tempSongpa',pct(t.songpa_m3_median_pct));
  set('temperatureHeadline',sg<=-1?'송파가 서울보다 느림':sg>=1?'송파가 서울보다 강함':'서울과 비슷한 흐름');
  set('tempGap',sg<0?'서울 대비 '+Math.abs(sg).toFixed(2)+'%p 뒤처짐 · '+String(t.ym||'').slice(0,4)+'.'+String(t.ym||'').slice(4):'서울 대비 '+pp(sg)+' · '+String(t.ym||'').slice(0,4)+'.'+String(t.ym||'').slice(4));

  const a=d.current?.affordability||{},ac=Number(a.affordability_change_3m_pct);
  set('affordHeadline',ac<0?'구매력 약화':'구매력 개선');
  set('affordRate',a.mortgage_rate_pct==null?'—':Number(a.mortgage_rate_pct).toFixed(2)+'%');
  set('affordPayment',a.payment_5eok_won==null?'—':Math.round(Number(a.payment_5eok_won)/10000).toLocaleString('ko-KR')+'만원');
  set('affordChange',a.affordability_change_3m_pct==null?'—':(ac>0?'+':'')+ac.toFixed(1)+'%');
  const loan=a.max_loan_income100m_dsr40_won==null?null:Number(a.max_loan_income100m_dsr40_won)/100000000;
  set('affordBenchmark','비교기준: 연소득 1억 · DSR 40% · 30년'+(loan==null?'':' → '+loan.toFixed(2)+'억')+' · 개인 한도 아님');

  const v=d.validation||{};
  set('contextValidation',v.breadth_role==='confidence_context'?'Breadth 백테스트 통과 · 국면 신뢰도 보강에 사용':'Breadth 연구 검증 중');
  host.dataset.breadth=up>=75?'strong':up>=45?'mixed':'weak';
  host.dataset.afford=ac<0?'worse':'better';
  const hd=document.getElementById('hubDriversMeta');if(hd)hd.textContent='확산 '+(s25.up??'—')+'/'+(s25.count??25)+' · 구매력 '+(ac>0?'+':'')+ac.toFixed(1)+'%';
 }catch(e){
  set('contextBreadthBadge','데이터 확인');
  set('breadthHeadline','확장지표 확인 중');
  set('temperatureHeadline','확장지표 확인 중');
  set('affordHeadline','확장지표 확인 중');
  console.error(e);
 }
}
loadMarketExtensions();
