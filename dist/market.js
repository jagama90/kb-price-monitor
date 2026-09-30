'use strict';const eok=n=>n==null?'—':(Number(n)/10000).toLocaleString('ko-KR',{maximumFractionDigits:2})+'억';async function renderKbHistory(){
 const note=document.querySelector('#kbHistoryNote'),svg=document.querySelector('#kbSvg'),axis=document.querySelector('#kbXAxis'),yaxis=document.querySelector('#kbYAxis');
 if(!svg||!axis||!yaxis)return;
 try{
  const d=await fetch('kb_watchlist_history.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('KB history '+r.status);return r.json()});
  const monthly={};
  for(const item of d.items||[])for(const x of item.series||[]){
   if(!x.ym||x.sale==null)continue;
   (monthly[x.ym]||(monthly[x.ym]=[])).push(Number(x.sale));
  }
  const med=a=>{const z=[...a].sort((a,b)=>a-b),n=z.length;return n%2?z[(n-1)/2]:(z[n/2-1]+z[n/2])/2};
  const a=Object.entries(monthly).filter(([,v])=>v.length>=8).sort((a,b)=>a[0].localeCompare(b[0])).slice(-12).map(([d,v])=>({d,avg:med(v),n:v.length}));
  if(!a.length)throw Error('no comparable watchlist history');
  const vals=a.map(x=>x.avg),lo=Math.floor((Math.min(...vals)-10000)/10000)*10000,hi=Math.ceil((Math.max(...vals)+10000)/10000)*10000,range=Math.max(1,hi-lo);
  yaxis.innerHTML=[hi,hi-(range/3),hi-(range*2/3),lo].map(v=>'<b>'+eok(v)+'</b>').join('');
  const pts=a.map((x,i)=>{const px=a.length===1?210:i*420/(a.length-1),py=160-((x.avg-lo)/range)*150;return px.toFixed(1)+','+py.toFixed(1)}).join(' ');
  svg.innerHTML='<line x1="0" y1="10" x2="420" y2="10"/><line x1="0" y1="60" x2="420" y2="60"/><line x1="0" y1="110" x2="420" y2="110"/><line x1="0" y1="160" x2="420" y2="160"/><polyline class="mainline" points="'+pts+'"/>'+a.map((x,i)=>{const px=a.length===1?210:i*420/(a.length-1),py=160-((x.avg-lo)/range)*150;return '<circle cx="'+px+'" cy="'+py+'" r="4" fill="#1677ff"/>'}).join('');
  const tickIdx=a.length<=6?a.map((_,i)=>i):Array.from(new Set([0,2,4,6,8,a.length-1])).filter(i=>i<a.length);
  axis.innerHTML=tickIdx.map(i=>'<span>'+a[i].d.slice(2,4)+'.'+a[i].d.slice(4,6)+'</span>').join('');
  const yfmt=v=>String(v||'').length===6?String(v).slice(0,4)+'.'+String(v).slice(4):String(v||'');
  if(note)note.textContent='KB 관심단지 월별 중앙값 · '+yfmt(a[0].d)+' ~ '+yfmt(a[a.length-1].d)+' · 최신 표본 '+a[a.length-1].n+'개';
 }catch(e){
  if(note)note.textContent='KB 관심단지 이력 확인 필요';
  console.error(e);
 }
}
renderKbHistory();let sourceRefreshNote='';const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const signal=x=>{const hasDelta=x.sale_listing_week_delta!=null,hasTrade=x.recent_trade_manwon!=null,hasAsk=x.avg_ask_manwon!=null,d=Number(x.sale_listing_week_delta),trade=Number(x.recent_trade_manwon),ask=Number(x.avg_ask_manwon);if(!hasDelta||!hasTrade||!hasAsk||!Number.isFinite(d)||!Number.isFinite(trade)||!Number.isFinite(ask)||trade<=0||ask<=0)return['관찰','watch'];const t=trade-ask;if(d>0&&t<0)return['하락','down'];if(d<0&&t>=0)return['상승','up'];return['관찰','watch']};async function load(){const [m,k,tg,wc]=await Promise.all([fetch('buy_watchlist_market.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),fetch('buy_watchlist_master.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),fetch('buy_watchlist_targets.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),fetch('kb_watchlist_weekly_change.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()).catch(()=>({items:[]}))]);const market=m.items||[],master=k.items||[],targets=tg.items||[];window.__watchMarket=m;const masterById=new Map(master.map(x=>[Number(x.complex_id),x]));
const listingCollected=new Date(m.listing_collected_at||m.collected_at||0),listingAgeDays=isNaN(listingCollected)?999:(Date.now()-listingCollected.getTime())/86400000,rowListingFresh=x=>{const d=new Date(x.listing_collected_at||m.listing_collected_at||m.collected_at||0),age=isNaN(d)?999:(Date.now()-d.getTime())/86400000,status=String(x.listing_refresh_status||m.listing_refresh_status||'legacy');return age<=10&&(status==='connected'||status==='legacy')},rowTradeFresh=x=>{const s=String(x.trade_refresh_status||'legacy');return x.recent_trade_manwon!=null&&(s==='connected'||s==='connected_no_newer_trade'||s==='legacy')},freshListingRows=market.filter(rowListingFresh).length,listingFresh=freshListingRows>0;
const hubWatch=document.getElementById('hubWatchMeta');if(hubWatch){const traded=market.filter(rowTradeFresh).length,liveListings=market.filter(rowListingFresh).length;hubWatch.textContent=market.length+'개 연결 · 실거래 '+traded+'개 · 매물 '+liveListings+'개'}
const kbKey=x=>Number(x.complex_id)+':'+Number(x.area_id);const kb=new Map(market.map(x=>{const z=masterById.get(Number(x.complex_id)),t=(z?.types||[]).find(a=>Number(a.area_id)===Number(x.area_id)),p=t?.general_price_manwon;return [kbKey(x),p==null?null:Number(p)]}));const validDate=v=>{const d=new Date(v||0);return Number.isFinite(d.getTime())?d:null},marketDates=[m.molit_trade_collected_at,m.kb_detail_collected_at,m.collected_at].map(validDate).filter(Boolean),marketUpdated=marketDates.length?new Date(Math.max(...marketDates.map(d=>d.getTime()))):new Date(),kbUpdated=validDate(k.kb_collected_at)||new Date();document.querySelector('#updated').textContent='시장 '+marketUpdated.toLocaleDateString('ko-KR',{month:'numeric',day:'numeric'})+' · KB '+kbUpdated.toLocaleDateString('ko-KR',{month:'numeric',day:'numeric'})+sourceRefreshNote;const collected=new Date(m.listing_collected_at||m.collected_at||Date.now()), collectedText=collected.toLocaleString('ko-KR',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'});const watchNotice=document.getElementById('watchSourceNotice'),listingStatus=String(m.listing_refresh_status||'');if(watchNotice){const liveRows=market.filter(rowListingFresh).length,partial=listingStatus==='partial_last_good';watchNotice.hidden=listingStatus==='connected';watchNotice.textContent=listingStatus==='connected'?'':partial?'KB 매물 일부 복구 · '+liveRows+'/'+market.length+'개 최신 연결 · 나머지는 마지막 정상값 또는 미연결':'KB 매물 원천 지연 · 마지막 정상 수집 '+collectedText+' · 매물 관련 값은 마지막 정상값과 구분 표시'}document.querySelector('#marketDate').textContent=kbUpdated.toLocaleDateString('ko-KR');const rowSignal=x=>rowListingFresh(x)&&rowTradeFresh(x)?signal(x):['관찰','watch'];const norm=s=>String(s||'').replace(/\s|아파트|\(|\)|마천역/g,'');const targetMap=new Map(targets.map(t=>[norm(t.name),t]));const preferred=x=>{const t=targetMap.get(norm(x.user_name||x.kb_name)),types=x.types||[];if(!t)return types;const aids=new Set((t.area_ids||[]).map(Number));if(aids.size)return types.filter(a=>aids.has(Number(a.area_id)));if(t.min_pyeong==null)return types;return types.filter(a=>{const m=String(a.type_label||'').match(/\d+(?:\.\d+)?/);return m&&Number(m[0])>=Number(t.min_pyeong)&&Number(m[0])<=Number(t.max_pyeong)})};const weekByKey=new Map((wc.items||[]).map(x=>[Number(x.complex_id)+':'+Number(x.area_id),x]));let boundary=(wc.items||[]).map(w=>({name:w.name,p:Number(w.current_manwon),type:w.type_label,delta:w.delta_manwon==null?null:Number(w.delta_manwon),deltaPct:w.delta_pct==null?null:Number(w.delta_pct),prev:w.previous_friday_manwon==null?null:Number(w.previous_friday_manwon)})).filter(x=>Number.isFinite(x.p)&&x.p>=130000&&x.p<=170000).sort((a,b)=>Math.abs(a.p-150000)-Math.abs(b.p-150000)).slice(0,7);const boundaryEl=document.querySelector('#boundary'),latestFriday=wc.latest_friday_as_of?sourcePeriodFmt(wc.latest_friday_as_of):'최근 금요일',prevFriday=wc.previous_friday_as_of?sourcePeriodFmt(wc.previous_friday_as_of):'직전 금요일';const md=document.querySelector('#marketDate');if(md)md.textContent=latestFriday+' vs '+prevFriday;let boundaryMode='near';const renderBoundary=()=>{const a=[...boundary].sort((x,y)=>boundaryMode==='asc'?x.p-y.p:boundaryMode==='desc'?y.p-x.p:Math.abs(x.p-150000)-Math.abs(y.p-150000));boundaryEl.innerHTML='<small class="boundary-period-v136">KB 일반가 · 완료 주간 '+latestFriday+' vs '+prevFriday+'</small><div class="mini-sort"><button data-b="near" class="'+(boundaryMode==='near'?'active':'')+'">15억 근접</button><button data-b="asc" class="'+(boundaryMode==='asc'?'active':'')+'">낮은순</button><button data-b="desc" class="'+(boundaryMode==='desc'?'active':'')+'">높은순</button></div>'+(a.map(x=>{const cls=x.delta>0?'rise':x.delta<0?'fall':'flat',move=x.delta==null?'비교 기준 없음':x.delta===0?'변동 없음':(x.delta>0?'+':'')+eok(x.delta)+' · '+(x.deltaPct>0?'+':'')+x.deltaPct.toFixed(1)+'%';return'<div class="row boundary-row-v136"><span>'+esc(x.name)+' <small>'+esc(x.type)+'평</small></span><b>'+eok(x.p)+'<small class="boundary-move-v136 '+cls+'">'+move+'</small></b></div>'}).join('')||'<small>13~17억 구간 데이터 없음</small>');boundaryEl.querySelectorAll('[data-b]').forEach(b=>b.onclick=()=>{boundaryMode=b.dataset.b;renderBoundary()})};renderBoundary();const freshRadar=[...market].filter(x=>rowListingFresh(x)&&x.sale_listing_week_delta!=null&&Number(x.sale_listing_week_delta)!==0),fallbackRadar=[...market].filter(x=>x.sale_listing_week_delta!=null&&Number(x.sale_listing_week_delta)!==0),radarUsesFallback=!freshRadar.length&&fallbackRadar.length>0,radarBase=radarUsesFallback?fallbackRadar:freshRadar;let radarMode='abs';const radarEl=document.querySelector('#radar');const renderRadar=()=>{const radar=[...radarBase].sort((a,b)=>radarMode==='up'?Number(b.sale_listing_week_delta)-Number(a.sale_listing_week_delta):radarMode==='down'?Number(a.sale_listing_week_delta)-Number(b.sale_listing_week_delta):Math.abs(Number(b.sale_listing_week_delta))-Math.abs(Number(a.sale_listing_week_delta))).slice(0,7),period=radarUsesFallback?'매물 원천 지연 · '+collectedText+' 마지막 정상값':'최근 수집 '+collectedText+' · 직전 주간 스냅샷 대비';radarEl.innerHTML='<small class="radar-period">'+period+'</small><div class="mini-sort"><button data-r="abs" class="'+(radarMode==='abs'?'active':'')+'">변동폭</button><button data-r="up" class="'+(radarMode==='up'?'active':'')+'">증가순</button><button data-r="down" class="'+(radarMode==='down'?'active':'')+'">감소순</button></div>'+(radar.length?radar.map(x=>'<div class="radar-row"><span>'+esc(x.name)+'</span><b class="'+(x.sale_listing_week_delta>0?'down':'up')+'">'+(x.sale_listing_week_delta>0?'+':'')+Number(x.sale_listing_week_delta)+'건</b></div>').join(''):'<small class="no-change">'+(listingStatus==='connected'?'변동이 있는 단지가 없습니다.':'현재 매물 원천이 일부 지연되어 증감 계산 가능한 최신 단지가 없습니다.')+'</small>');radarEl.querySelectorAll('[data-r]').forEach(b=>b.onclick=()=>{radarMode=b.dataset.r;renderRadar()})};renderRadar();const priceOf=x=>Number(kb.get(kbKey(x)))||(rowListingFresh(x)?Number(x.avg_ask_manwon):0)||Number(x.recent_trade_manwon)||Infinity;const rows=[...market].sort((a,b)=>{const da=Math.abs(priceOf(a)-150000),db=Math.abs(priceOf(b)-150000);return da-db||priceOf(b)-priceOf(a)});const unavailableCount=(m.known_unavailable_targets||[]).length;renderDataStatusPanel();document.querySelector('#summary').textContent=market.length+'개 단지'+(unavailableCount?' · '+unavailableCount+'개 입주 전':'')+' · KB시세 · 실거래 · 매물';document.querySelector('#body').innerHTML=rows.map(x=>{const s=rowSignal(x),lf=rowListingFresh(x),tf=rowTradeFresh(x),lc=lf&&x.sale_listing_count!=null?Number(x.sale_listing_count).toLocaleString()+'건':'—',wd=lf&&x.sale_listing_week_delta!=null?(x.sale_listing_week_delta>0?'+':'')+Number(x.sale_listing_week_delta)+'건':'—',ask=lf&&x.avg_ask_manwon!=null?eok(x.avg_ask_manwon):'—',trade=tf?eok(x.recent_trade_manwon):'<span class="data-missing">실거래 미확인</span>',tradeDate=tf?'<small> '+esc(x.recent_trade_date||'')+'</small>':'';return'<tr><td><b>'+esc(x.name)+'</b><small> '+esc(x.type_label||'')+'평</small></td><td>'+eok(kb.get(kbKey(x)))+'</td><td>'+trade+tradeDate+'</td><td class="'+(!lf||x.avg_ask_manwon==null?'data-missing':'')+'">'+ask+'</td><td class="'+(!lf||x.sale_listing_count==null?'data-missing':'')+'">'+lc+'</td><td class="'+(!lf||x.sale_listing_week_delta==null?'data-missing':x.sale_listing_week_delta>0?'down':x.sale_listing_week_delta<0?'up':'')+'">'+wd+'</td><td><span class="pill '+s[1]+'">'+s[0]+'</span></td></tr>'}).join('');document.querySelector('#mobileCards').innerHTML=rows.map(x=>{const s=rowSignal(x),lf=rowListingFresh(x),tf=rowTradeFresh(x),stale=String(x.listing_refresh_status||'').includes('last_good'),lc=x.sale_listing_count!=null?Number(x.sale_listing_count).toLocaleString()+'건':'—',wd=x.sale_listing_week_delta!=null?(x.sale_listing_week_delta>0?'+':'')+Number(x.sale_listing_week_delta)+'건':'—',ask=x.avg_ask_manwon!=null?eok(x.avg_ask_manwon):'—',tradeDate=tf?sourcePeriodFmt(x.recent_trade_date||''):'—',listMeta=stale?'마지막 정상값':lf?'KB 최신':'KB 원천 미연결';return'<article class="complex"><div class="complex-head"><b>'+esc(x.name)+' <small>'+esc(x.type_label||'')+'평</small></b><span class="pill '+s[1]+'">'+s[0]+'</span></div><div class="complex-grid compact-watch-v136"><div><span>KB시세</span><b>'+eok(kb.get(kbKey(x)))+'</b><small>KB 일반가</small></div><div><span>최근 실거래</span><b class="'+(tf?'':'data-missing')+'">'+(tf?eok(x.recent_trade_manwon):'미확인')+'</b><small>'+tradeDate+'</small></div><div><span>매물 평균</span><b class="'+(x.avg_ask_manwon!=null?'':'data-missing')+'">'+ask+'</b><small>'+listMeta+'</small></div><div><span>매물 수</span><b class="'+(x.sale_listing_count!=null?'':'data-missing')+'">'+lc+(x.sale_listing_week_delta!=null?' <i class="watch-delta-v136 '+(x.sale_listing_week_delta>0?'rise':x.sale_listing_week_delta<0?'fall':'flat')+'">'+wd+'</i>':'')+'</b><small>'+listMeta+'</small></div></div></article>'}).join('')+'<button id="moreComplexes" class="more-btn">↓ 더보기 ('+Math.max(0,rows.length-5)+'개)</button>';const mc=document.querySelector('#mobileCards'),mb=document.querySelector('#moreComplexes');if(rows.length<=5)mb.style.display='none';mb.addEventListener('click',()=>{const open=mc.classList.toggle('expanded');mb.textContent=open?'↑ 접기':'↓ 더보기 ('+Math.max(0,rows.length-5)+'개)'})}load().catch(e=>{document.querySelector('#updated').textContent='관심단지 일부 데이터 확인 필요';console.error(e)});
async function loadMarketIndicators(){
 try{
  const [d,jg]=await Promise.all([
   fetch('market_indicators.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),
   fetch('market_judgment.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('judgment '+r.status);return r.json()})
  ]);
  window.__marketJudgment=jg;
  renderCycleStage(jg);
  const vols=d.seoul_apt_trade_count||[];
  if(vols.length){const z=vols[vols.length-1];setText('snapVolume',Number(z[1]).toLocaleString('ko-KR')+'건');setText('snapVolumePeriod',sourcePeriodFmt(z[0])+(z[2]?' · 신고 진행':' · 집계'))}
  const bands=d.price_bands?.months||[],latest=bands[bands.length-1];
  if(latest){setText('snapUnder15',latest.under15_share+'%');const b3=latest.buckets3||{'<=15eok':Number(latest.counts?.['<=9eok']||0)+Number(latest.counts?.['9-15eok']||0),'15-25eok':latest.counts?.['15-25eok'],'25eok+':latest.counts?.['25eok+']};setText('b15all',Number(b3['<=15eok']||0).toLocaleString('ko-KR')+'건');setText('b15to25',Number(b3['15-25eok']||0).toLocaleString('ko-KR')+'건');setText('b25p',Number(b3['25eok+']||0).toLocaleString('ko-KR')+'건')}
  const m=d.m2_official||d.m2;if(m){setText('snapM2',m.yoy_pct==null?'—':m.yoy_pct+'%');setText('snapM2Period',sourcePeriodFmt(m.period)+(m.yoy_change_pp==null?'':' · 전월보다 '+signed(m.yoy_change_pp,'%p')));setText('m2Detail','ECOS M2 · 전월비 '+(m.mom_pct??'—')+'% ('+(m.mom_change_pp==null?'변화 대기':signed(m.mom_change_pp,'%p'))+') · 전년비 '+(m.yoy_pct??'—')+'% ('+(m.yoy_change_pp==null?'변화 대기':signed(m.yoy_change_pp,'%p'))+')')}
  if(d.matched_period){const x=d.matched_period,c=x.current,p=x.previous,fmt=v=>v==null?'—':Number(v).toLocaleString('ko-KR');setText('matchedRange',sourcePeriodFmt(p.period)+' '+p.range+' ↔ '+sourcePeriodFmt(c.period)+' '+c.range+' · 계약일 기준');setText('matchedVolume',fmt(p.total)+' → '+fmt(c.total)+'건');setText('matchedVolumeDelta',x.changes?.trade_count_pct==null?'증감 계산 대기':signed(x.changes.trade_count_pct,'%')+' · 당월 신고 진행');setText('matchedUnder15',(p.under15_share??'—')+' → '+(c.under15_share??'—')+'%');setText('matchedUnder15Delta',x.changes?.under15_share_pp==null?'증감 계산 대기':signed(x.changes.under15_share_pp,'%p'));const hv=document.getElementById('hubValidationMeta');if(hv)hv.textContent='거래 '+(x.changes?.trade_count_pct==null?'—':signed(x.changes.trade_count_pct,'%'))+' · ≤15억 '+(c.under15_share??'—')+'%';renderTradeDistribution(x)}
  const u=d.unsold_seoul;if(u){setText('validationUnsold',Number(u.seoul_units).toLocaleString('ko-KR')+'호');setText('validationUnsoldPeriod',sourcePeriodFmt(u.period)+' · 전월 '+(Number(u.change_units)>0?'+':'')+Number(u.change_units).toLocaleString('ko-KR')+'호 ('+(Number(u.change_pct)>0?'+':'')+Number(u.change_pct).toFixed(1)+'%)')}
  window.__marketIndicators=d;renderDataStatusPanel();
  const src=d.refresh_run?.sources||{},srcLabel={molit:'국토부',ecos:'ECOS',kb_sentiment:'KB지수',watchlist_detail:'단지상세'},delayed=Object.entries(src).filter(([,v])=>v!=='connected').map(([k])=>srcLabel[k]||k);
  sourceRefreshNote=delayed.length?' · 일부 지연':' · 정상';
  const updatedNow=document.querySelector('#updated');
  if(updatedNow){const base=updatedNow.textContent.replace(/ · 원천 (?:지연 .+|갱신 확인)$/,'');updatedNow.textContent=base+sourceRefreshNote}
  const br=d.base_rate_official;BASE_RATES=(br?.series||[]).map(x=>({d:String(x.date||''),v:Number(x.rate_pct)})).filter(x=>x.d&&Number.isFinite(x.v));
  RATE_PAGE=0;
  renderKbOfficial(d);
  renderConditionIndex(d,jg);
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
 const br=(d.base_rate_official||{}),rates=br.series||[],cur=rates[rates.length-1],prev=rates[rates.length-2]||cur;
 if(cur)bind('rateCard',()=>open('기준금리','한국은행 ECOS',[Number(cur.rate_pct).toFixed(2)+'%',cur.date||br.latest_observation_date||'최신'],[Number(prev.rate_pct).toFixed(2)+'%',prev.date||'직전 변경'],signed(Number(cur.rate_pct)-Number(prev.rate_pct),'%p'),'현재 기준금리 수준','한국은행 ECOS 기준금리 시계열의 최신 변경값과 직전 변경값을 비교합니다.'));
 if(m)bind('m2Card',()=>open('M2 통화량','한국은행 ECOS 101Y003',[Number(m.yoy_pct).toFixed(1)+'%','전년동월비 · '+m.period],[Number(m.mom_pct).toFixed(1)+'%','전월비'],signed(m.yoy_pct,'%'),'광의통화 증가율','M2 원계열의 전년동월비와 전월비를 함께 확인합니다.'));
 document.getElementById('closeSnapshotExplain')?.addEventListener('click',()=>document.getElementById('snapshotExplanation').hidden=true);
}
const signed=(v,s='')=>(Number(v)>0?'+':'')+Number(v).toFixed(1)+s;
const clamp=v=>Math.max(0,Math.min(100,v));
const sourcePeriodFmt=v=>{
 const s=String(v??'').trim();
 if(!s)return'—';
 let m;
 if((m=s.match(/^(\d{4})[-./]?(\d{2})[-./]?(\d{2})$/)))return m[1]+'.'+m[2]+'.'+m[3];
 if((m=s.match(/^(\d{4})[-./]?(\d{2})$/)))return m[1]+'-'+m[2];
 return s;
};
const scoreBand=v=>{if(v==null||!Number.isFinite(Number(v)))return{label:'미연결',range:'—',cls:'neutral',comment:'입력 데이터 확인 필요'};v=Number(v);if(v<30)return{label:'매우 제약',range:'0~29',cls:'verybad',comment:'매수여건 제약이 큰 구간'};if(v<45)return{label:'제약 구간',range:'30~44',cls:'bad',comment:'부담 요인이 우세한 구간'};if(v<55)return{label:'중립 구간',range:'45~54',cls:'neutral',comment:'개선·제약이 엇갈리는 구간'};if(v<70)return{label:'개선 구간',range:'55~69',cls:'good',comment:'매수여건이 점진적으로 나아지는 구간'};return{label:'우호 구간',range:'70~100',cls:'strong',comment:'여러 매수여건이 우호적인 구간'}};
function renderKbOfficial(d){
 const s=d.kb_weekly_sale_index,r=d.kb_weekly_rent_index,m=d.mortgage_rate_official,v=d.kb_value,box=document.getElementById('kbOfficialData');if(!box)return;
 const dlt=(v,suf)=>v==null?'변화 대기':(Number(v)>0?'+':'')+Number(v).toFixed(2)+suf;
 const idx=x=>x?.latest?'<b>'+Number(x.latest.value).toFixed(2)+'</b><small>전주 '+dlt(x.latest.change_pct,'%')+' · '+esc(sourcePeriodFmt(x.latest.date))+'</small>':'<b>수집 대기</b>';
 const vc=v?.components||{},pir=vc.pir||{},rr=vc.rent_ratio||{},tg=vc.trend_gap||{};
 box.innerHTML='<div><span>KB 주간 매매가격지수</span>'+idx(s)+'</div><div><span>KB 주간 전세가격지수</span>'+idx(r)+'</div><div><span>ECOS 주담대금리</span><b>'+(m?.rate_pct!=null?Number(m.rate_pct).toFixed(2)+'%':'—')+'</b><small>'+(m?.change_pp==null?'전월 변화 대기':'전월 '+dlt(m.change_pp,'%p'))+' · '+esc(sourcePeriodFmt(m?.period))+'</small></div><div><span>가격·밸류</span><b>'+(v?.score_0_100!=null?v.score_0_100+'/100':'—')+'</b><small>'+(pir.value!=null?'PIR '+Number(pir.value).toFixed(2)+'배 · ':'')+(rr.value_pct!=null?'전세가율 '+Number(rr.value_pct).toFixed(1)+'% · ':'')+(tg.value_pct!=null?'추세 '+(Number(tg.value_pct)>0?'+':'')+Number(tg.value_pct).toFixed(1)+'%':'')+'</small></div>';
 setText('validationRentChange',r?.latest?.change_pct==null?'—':signed(r.latest.change_pct,'%'));
 setText('validationRentPeriod',r?.latest?.date?'전주 대비 · '+sourcePeriodFmt(r.latest.date):'KB 공식');
 const jsup=d.kb_sentiment?.latest?.전세수급,chg=d.kb_sentiment?.changes?.전세수급;
 setText('validationJeonseSupply',jsup?.value==null?'—':Number(jsup.value).toFixed(1));
 setText('validationJeonseSupplyPeriod',jsup?.date?('전주 '+(chg==null?'변화 대기':signed(chg,''))+' · 100=균형 · '+(Number(jsup.value)>100?'수요우위':'공급우위')):'KB 공식');
}
function renderConditionIndex(d,jg=window.__marketJudgment){
 const bands=d.price_bands?.months||[],latest=bands[bands.length-1],prev=bands[bands.length-2],m=d.m2_official||d.m2,matched=d.matched_period;
 const buy=jg?.heads?.buy_condition||null,shared=jg?.feature_layer||{},sharedComponents=buy?.components||shared.components||null;
 const components=sharedComponents?Object.fromEntries(Object.entries(sharedComponents).map(([k,v])=>[k,v==null?null:Number(v)])):{finance:null,sentiment:null,demand:null,value:null,supply:null};
 if(!sharedComponents){
  if(d.kb_sentiment?.score_0_100!=null)components.sentiment=Number(d.kb_sentiment.score_0_100);
  if(m?.mom_pct!=null&&m?.yoy_pct!=null)components.finance=clamp(50+Number(m.mom_pct)*8+Number(m.yoy_pct)*1.5);
  if(matched?.changes?.trade_count_pct!=null&&matched?.changes?.under15_share_pp!=null)components.demand=clamp(50+Number(matched.changes.trade_count_pct)*.35+Number(matched.changes.under15_share_pp)*1.5);
  if(d.kb_value?.score_0_100!=null)components.value=Number(d.kb_value.score_0_100);
  if(d.kb_sentiment?.jeonse_score_0_100!=null)components.supply=Number(d.kb_sentiment.jeonse_score_0_100);
 }
 window.__conditionComponents=components;
 const weights={finance:25,sentiment:20,demand:20,value:20,supply:15},labels={finance:'scoreFinance',sentiment:'scoreSentiment',demand:'scoreDemand',value:'scoreValue',supply:'scoreSupply'};
 const deltaMap=shared.component_deltas_vs_research_month||{},factorNames={finance:'금융',sentiment:'심리',demand:'거래',value:'밸류',supply:'전세'};
 const arrow=v=>Number(v)>.5?'↑':Number(v)<-.5?'↓':'→';
 const factorSummary=document.getElementById('judgmentFactorSummary');
 if(factorSummary)factorSummary.innerHTML=Object.keys(labels).map(k=>'<span data-factor="'+k+'"><b>'+factorNames[k]+' '+(components[k]==null?'—':Math.round(components[k]))+'</b><i class="'+(arrow(deltaMap[k])==='↑'?'up':arrow(deltaMap[k])==='↓'?'down':'flat')+'">'+arrow(deltaMap[k])+'</i></span>').join('');
 Object.entries(labels).forEach(([k,id])=>{
  setText(id,components[k]==null?'—':Math.round(components[k]));
  const card=document.querySelector('[data-score="'+k+'"]');
  if(card)card.style.setProperty('--score',components[k]==null?0:Math.round(components[k]));
 });
 const historyKey='marketConditionPreviousComponents', previous=(()=>{try{return JSON.parse(localStorage.getItem(historyKey)||'{}')}catch(e){return {}}})(); window.__previousConditionComponents=previous;
 Object.entries(labels).forEach(([k])=>document.querySelector('[data-score="'+k+'"]')?.querySelector('.score-change-badge')?.remove());
 try{localStorage.setItem(historyKey,JSON.stringify(components))}catch(e){}
 const available=Object.keys(components).filter(k=>components[k]!=null),covered=available.reduce((a,k)=>a+weights[k],0);
 const cov=document.getElementById('confidenceScore');if(cov){cov.textContent=covered+'%';cov.className='coverage-badge-v140 '+(covered>=95?'full':covered>=80?'partial':'low');const health=cov.closest('.condition-health-v181');if(health)health.hidden=covered>=95}
 if(covered<60){setText('conditionScore','산출 보류');setText('conditionTier','연결 부족');setText('heroMeterValue','—');const meter=document.getElementById('heroMeterFill');if(meter)meter.style.width='0%'}
 else {const rawScore=buy?.score_0_100!=null?Number(buy.score_0_100):available.reduce((a,k)=>a+components[k]*weights[k],0)/covered,score=Math.round(rawScore),band=scoreBand(score);setText('conditionScore',score+'/100');setText('conditionTier',buy?.tier||band.label);const tier=document.getElementById('conditionTier');if(tier)tier.className='score-tier-v140 '+band.cls;setText('heroMeterValue',score+'/100');const meter=document.getElementById('heroMeterFill');if(meter)meter.style.width=score+'%'}
 const finance=components.finance,sent=components.sentiment,demand=components.demand,value=components.value;
 const trade=matched?.changes?.trade_count_pct,under=matched?.changes?.under15_share_pp,mom=m?.mom_pct;
 const state=(v)=>{const b=scoreBand(v);return[b.label,b.cls==='good'||b.cls==='strong'?'good':b.cls==='bad'||b.cls==='verybad'?'bad':'neutral']};
 const fs=state(finance),ss=state(sent),ds=state(demand),vs=state(value),sup=state(components.supply);
 const stateLabel=s=>s[0];
 [['Finance',fs],['Sentiment',ss],['Demand',ds],['Value',vs],['Supply',sup]].forEach(([id,s])=>{setText('state'+id,stateLabel(s));const el=document.getElementById('state'+id);if(el)el.className='component-state '+s[1]});
 const impactFor=(k,v)=>{
  if(v==null||!Number.isFinite(Number(v)))return'입력 데이터 확인 필요';
  v=Number(v);
  if(k==='finance')return v>=55?'매수환경을 끌어올리고 하락 위험을 완화':v<45?'자금여건이 매수환경을 제약':'자금여건은 현재 방향성 중립';
  if(k==='sentiment')return v>=55?'상승 확산과 재가속을 지지':v<45?'상승 확산을 막고 재가속 판단을 억제':'심리는 아직 뚜렷한 방향을 만들지 못함';
  if(k==='demand')return v>=55?'실거래 회복이 상승 지속을 지지':v<45?'가속 전환을 막는 핵심 제약':'거래는 방향 확인이 더 필요한 수준';
  if(k==='value')return v>=55?'가격 안전마진이 매수 판단을 지지':v<45?'가격 안전마진 부족으로 매수를 제약':'가격 부담은 중립권';
  if(k==='supply')return v>=55?'전세 수요가 가격 하방을 지지':v<45?'전세 여건이 하방 방어를 약화':'전세 신호는 방향성 중립';
  return'';
 };
 setText('impactFinance',impactFor('finance',components.finance));
 setText('impactSentiment',impactFor('sentiment',components.sentiment));
 setText('impactDemand',impactFor('demand',components.demand));
 setText('impactValue',impactFor('value',components.value));
 setText('impactSupply',impactFor('supply',components.supply));
 const connected=[finance,sent,demand,value,components.supply].filter(v=>v!=null);
 const weak=connected.filter(v=>v<45).length,strong=connected.filter(v=>v>=55).length;
 const lowFactors=Object.entries(components).filter(([,v])=>v!=null).sort((a,b)=>a[1]-b[1]).slice(0,2).map(([k])=>factorNames[k]).join('·');
 const highFactors=Object.entries(components).filter(([,v])=>v!=null).sort((a,b)=>b[1]-a[1]).slice(0,1).map(([k])=>factorNames[k]).join('');
 setText('heroVerdict',buy?(highFactors+'은 상대적으로 양호하지만 '+lowFactors+' 부담이 커 매수여건은 '+buy.tier+'입니다.'):(weak>=3?'아직은 제약 신호가 우세합니다. 반전 확인이 필요한 구간입니다.':strong>=3?'개선 신호가 여러 단계에서 확인되고 있습니다. 지속성을 확인할 구간입니다.':'개선과 제약 신호가 엇갈립니다. 다음 단계로의 전달을 확인할 구간입니다.'));
 const next=[];if(trade<0)next.push('거래량 반등');if(sent<45)next.push('KB 심리 회복');next.push('15억 이하 비중 지속성');next.push('관심단지 실거래 전이');
 document.getElementById('nextSignals').innerHTML=next.slice(0,4).map((x,i)=>'<span><b>'+(i+1)+'</b>'+esc(x)+'</span>').join('');
 setTimeout(renderConditionHistory,0);
}
loadMarketIndicators();
let BASE_RATES=[];
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
 if(!BASE_RATES.length){setText('rateRange','ECOS 데이터 연결 중');const h=document.getElementById('rateHistory');if(h)h.innerHTML='<small>기준금리 시계열을 불러오는 중입니다.</small>';return}
 const pg=renderPagedSeries('rateSvg','rateX','rateY',BASE_RATES,RATE_PAGE,7,null);setText('rateRange',BASE_RATES[pg.start].d+' ~ '+BASE_RATES[pg.end-1].d);
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

window.__regimeReferences=null;window.__currentCycleStage=0;window.__currentRegimeMetrics=null;window.__selectedRegimeRefStage=null;window.__regimeCompare=false;
async function renderCycleStage(jg=window.__marketJudgment){ // unified snapshot first; research fallback only
 try{
  const head=jg?.heads?.current_state||null,feature=jg?.feature_layer||null;
  if(head&&feature){
   const stage=Math.max(0,Math.min(4,Number(head.stage)||0)),pm=feature.price_momentum||{},sig=feature.signals||{},ov=pm.overlay||{};
   const mapped1=Number(pm.m1_pct),mapped3=Number(pm.m3_pct),raw1=ov.kb_4w_pct!=null?Number(ov.kb_4w_pct):mapped1,raw3=ov.kb_13w_pct!=null?Number(ov.kb_13w_pct):mapped3;
   const kbComparable=ov.kb_4w_pct!=null&&ov.kb_13w_pct!=null,stamp=String(ov.kb_as_of||feature.as_of||jg.as_of||''),label=stamp.replace(/^(\d{4})(\d{2})(\d{2})$/,'$1.$2.$3').replace(/-/g,'.');
   const pct=v=>Number.isFinite(Number(v))?(Number(v)>0?'+':'')+Number(v).toFixed(2)+'%':'—',score=v=>Number.isFinite(Number(v))?Number(v).toFixed(1):'—';
   window.__currentCycleStage=stage;
   window.__currentRegimeMetrics={
    ym:feature.research_month||'',label:label||feature.research_month||'현재',
    price_mom_1m_pct:raw1,price_mom_3m_pct:raw3,
    research_price_mom_1m_pct:mapped1,research_price_mom_3m_pct:mapped3,
    price_source:kbComparable?'kb_seoul_weekly':'research',
    breadth_0_100:Number(sig.breadth),reaccel_0_100:Number(sig.reaccel)
   };
   setText('judgmentCurrentLabel',head.label||['하락','둔화','바닥','상승·보합','가속'][stage]);
   setText('cycleStageText',head.summary||'통합 시장 판단 엔진의 현재 국면을 표시합니다.');
   document.querySelectorAll('#cycleSteps span').forEach((el,i)=>{el.classList.toggle('active',i===stage);el.setAttribute('aria-current',i===stage?'step':'false')});
   const refBox=document.getElementById('regimeReference');if(refBox&&!refBox.hidden&&window.__selectedRegimeRefStage===stage&&window.__regimeReferences){window.__regimeCompare=true;renderRegimeReference(stage)}
   return;
  }

  const [d,kb]=await Promise.all([
   fetch('turning_signal_research.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('turning signal '+r.status);return r.json()}),
   fetch('market_indicators.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null)
  ]),rows=d.rows||[],x=rows.at(-1);if(!x)throw Error('no rows');
  const m1=Number(x.price_mom_pct),m3=Number(x.momentum_3m_pct),recent=rows.slice(-4,-1),wasRising=recent.some(r=>Number(r.momentum_3m_pct)>0);
  let stage=0,text='가격 하락 흐름이 이어지고 있습니다. 아직 하락이 멈췄다고 보기 어렵습니다.';
  if(x.bottom_zone){stage=1;text='하락 압력이 약해지고 있습니다. 다만 아직 가격이 멈췄거나 상승세로 바뀌었다고 보기는 이릅니다.'}
  if(m1>=0&&m3<=0&&!wasRising){stage=2;text='하락 뒤 가격이 더 내려가지 않고 있습니다. 바닥 여부를 확인하는 구간입니다.'}
  if(m3>0){stage=3;text='최근 3개월 가격 흐름이 상승입니다. 상승 흐름이 이어지는지 확인하는 단계입니다.'}
  if(wasRising&&m3<=0&&m1>=0){stage=3;text='앞선 상승세가 멈추고 최근 가격이 보합권에 들어왔습니다. 상승 모멘텀이 식은 상태입니다.'}
  if(x.momentum_zone){stage=4;text='가격 상승과 시장 수요가 함께 강해지는 구간입니다.'}
  const km=kb?.kb_weekly_sale_index?.momentum||{},kbComparable=km.mom_4w_pct!=null&&km.mom_13w_pct!=null;
  window.__currentCycleStage=stage;
  window.__currentRegimeMetrics={
   ym:x.ym,label:km.as_of?String(km.as_of).slice(0,4)+'.'+String(km.as_of).slice(4,6)+'.'+String(km.as_of).slice(6,8):x.ym.slice(0,4)+'.'+x.ym.slice(4),
   price_mom_1m_pct:kbComparable?Number(km.mom_4w_pct):m1,
   price_mom_3m_pct:kbComparable?Number(km.mom_13w_pct):m3,
   research_price_mom_1m_pct:m1,research_price_mom_3m_pct:m3,
   price_source:kbComparable?'kb_seoul_weekly':'research',
   breadth_0_100:Number(x.breadth),reaccel_0_100:Number(x.reaccel)
  };
  setText('judgmentCurrentLabel',['하락','둔화','바닥','상승·보합','가속'][stage]);
  setText('cycleStageText',text);
  const flow=m3>0?'상승 '+m3.toFixed(1)+'%':m3<0?'하락 '+Math.abs(m3).toFixed(1)+'%':'보합';
  document.querySelectorAll('#cycleSteps span').forEach((el,i)=>{el.classList.toggle('active',i===stage);el.setAttribute('aria-current',i===stage?'step':'false')});
  const refBox=document.getElementById('regimeReference');if(refBox&&!refBox.hidden&&window.__selectedRegimeRefStage===stage&&window.__regimeReferences){window.__regimeCompare=true;renderRegimeReference(stage)}
 }catch(e){
  console.warn('cycle stage',e);setText('judgmentCurrentLabel','국면 확인 중');setText('cycleStageText','국면 데이터 연결을 확인하고 있습니다.');
 }
}
const regimeYm=v=>{const s=String(v||'');return s.length===6?s.slice(0,4)+'.'+s.slice(4):s};
function renderRegimeReference(stage){
 const refs=window.__regimeReferences||[],x=refs.find(r=>Number(r.stage)===Number(stage));if(!x)return;
 window.__selectedRegimeRefStage=Number(stage);
 document.querySelectorAll('#cycleSteps [data-regime-ref]').forEach(e=>e.setAttribute('aria-pressed',Number(e.dataset.regimeRef)===Number(stage)?'true':'false'));
 const current=window.__currentRegimeMetrics,compare=!!(window.__regimeCompare&&current),period=x.period_start===x.period_end?regimeYm(x.period_start):regimeYm(x.period_start)+' ~ '+regimeYm(x.period_end);
 const hk=x.kb_seoul_momentum||{},sameKb=hk.mom_4w_pct!=null&&hk.mom_13w_pct!=null&&current?.price_source==='kb_seoul_weekly';
 const hist1=hk.mom_4w_pct!=null?Number(hk.mom_4w_pct):Number(x.price_mom_1m_pct),hist3=hk.mom_13w_pct!=null?Number(hk.mom_13w_pct):Number(x.price_mom_3m_pct);
 const cur1=sameKb?Number(current.price_mom_1m_pct):Number(current?.research_price_mom_1m_pct??current?.price_mom_1m_pct),cur3=sameKb?Number(current.price_mom_3m_pct):Number(current?.research_price_mom_3m_pct??current?.price_mom_3m_pct);
 const priceLabel1=sameKb||hk.mom_4w_pct!=null?'1개월 가격':'월간 가격',priceLabel3=sameKb||hk.mom_13w_pct!=null?'3개월 가격':'3개월 가격';
 const currentLabel=current?.label||regimeYm(current?.ym);
 setText('regimeRefTitle',x.label+' 대표 '+(x.months>1?'구간':'시점'));
 setText('regimeRefPeriod',compare?period+' ↔ 현재 '+currentLabel:period);
 setText('regimeRefDesc',x.description+(compare?(sameKb?' 과거와 현재 모두 KB 서울 주간 매매가격지수의 4주·13주 변화율로 비교합니다.':' 현재값과 같은 척도로 대조합니다.'):''));
 const toggle=document.getElementById('regimeCompareToggle');if(toggle){toggle.disabled=!current;toggle.classList.toggle('active',compare);toggle.textContent=compare?'과거만 보기':'현재와 비교';toggle.setAttribute('aria-pressed',compare?'true':'false')}
 const signed2=v=>v==null||!Number.isFinite(Number(v))?'—':(Number(v)>0?'+':'')+Number(v).toFixed(2)+'%';
 const score=v=>v==null?'—':Number(v).toFixed(1)+'/100';
 const metric=(wrapId,bId,label,hv,cv,kind)=>{
  const wrap=document.getElementById(wrapId);if(!wrap)return;
  if(!compare){wrap.innerHTML='<small>'+label+'</small><b id="'+bId+'">'+(kind==='pct'?signed2(hv):score(hv))+'</b>';return}
  const delta=Number(cv)-Number(hv),unit=kind==='pct'?'%p':'p',hist=kind==='pct'?signed2(hv):score(hv),now=kind==='pct'?signed2(cv):score(cv),dd=(delta>0?'+':'')+delta.toFixed(kind==='pct'?2:1)+unit,cls=delta>0?'up':delta<0?'down':'flat';
  wrap.innerHTML='<small>'+label+'</small><b id="'+bId+'" class="regime-metric-pair-v151"><span>과거 '+hist+'</span><i>→</i><span>현재 '+now+'</span></b><em class="regime-metric-delta-v151 '+cls+'">현재 '+dd+'</em>';
 };
 metric('regimeMetricM1','regimeRefM1',priceLabel1,hist1,cur1,'pct');
 metric('regimeMetricM3','regimeRefM3',priceLabel3,hist3,cur3,'pct');
 metric('regimeMetricBreadth','regimeRefBreadth','시장 확산',x.breadth_0_100,current?.breadth_0_100,'score');
 metric('regimeMetricReaccel','regimeRefReaccel','재가속',x.reaccel_0_100,current?.reaccel_0_100,'score');
 const host=document.getElementById('regimeRefSpark');if(host){
  const rawBar=(tag,v)=>{const n=Number(v)||0,mag=Math.min(50,Math.abs(n)/15*50),side=n<0?'neg':n>0?'pos':'flat';return '<div class="compare-bar-line-v151"><span>'+tag+'</span><div class="momentum-track-v147"><i></i><u class="'+side+'" style="width:'+mag+'%;'+(n<0?'right:50%':'left:50%')+'"></u></div><b class="'+side+'">'+(n>0?'+':'')+n.toFixed(2)+'%</b></div>'};
  const single=(label,v)=>{const n=Number(v)||0,mag=Math.min(50,Math.abs(n)/15*50),side=n<0?'neg':n>0?'pos':'flat';return '<div class="momentum-row-v147"><div class="momentum-label-v147"><span>'+label+'</span><b class="'+side+'">'+(n>0?'+':'')+n.toFixed(2)+'%</b></div><div class="momentum-track-v147"><i></i><u class="'+side+'" style="width:'+mag+'%;'+(n<0?'right:50%':'left:50%')+'"></u></div></div>'};
  const src=hk.mom_4w_pct!=null?'KB 서울 매매지수 · '+String(hk.as_of||'').replace(/^(\d{4})(\d{2})(\d{2})$/,'$1.$2.$3'):'대표가격';
  if(compare){
   host.innerHTML='<div class="momentum-title-v147"><b>가격 모멘텀 · 과거 vs 현재</b><span>'+(sameKb?'동일 KB 서울지수':'동일 연구척도')+'</span></div><div class="compare-momentum-group-v151"><strong>'+priceLabel1+'</strong>'+rawBar('과거',hist1)+rawBar('현재',cur1)+'</div><div class="compare-momentum-group-v151"><strong>'+priceLabel3+'</strong>'+rawBar('과거',hist3)+rawBar('현재',cur3)+'</div><div class="momentum-period-v147"><span>'+period+' ↔ 현재 '+currentLabel+'</span><b>'+esc(src)+'</b></div>';
  }else{
   host.innerHTML='<div class="momentum-title-v147"><b>가격 모멘텀</b><span>'+esc(src)+'</span></div>'+single(priceLabel1,hist1)+single(priceLabel3,hist3)+'<div class="momentum-period-v147"><span>'+period+'</span><b>'+esc(src)+'</b></div>';
  }
 }
 const note=document.querySelector('#regimeReference .regime-ref-note-v145');if(note)note.textContent=compare?(sameKb?'가격은 과거·현재 모두 KB 서울지수 기준입니다. 시장 확산·재가속은 연구엔진 점수를 비교합니다.':'과거 대표값과 현재값을 같은 연구척도로 비교합니다.'):'현재와 비교를 누르면 같은 지표를 대조합니다. 대표사례는 현재 판정에 사용하지 않습니다.';
}
async function loadRegimeReferences(){
 try{
  const d=await fetch('regime_reference_examples.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('references '+r.status);return r.json()});
  window.__regimeReferences=d.references||[];
  document.querySelectorAll('#cycleSteps [data-regime-ref]').forEach(el=>{
   const open=()=>{const s=Number(el.dataset.regimeRef),box=document.getElementById('regimeReference');if(box&&!box.hidden&&window.__selectedRegimeRefStage===s){box.hidden=true;window.__selectedRegimeRefStage=null;window.__regimeCompare=false;document.querySelectorAll('#cycleSteps [data-regime-ref]').forEach(x=>x.setAttribute('aria-pressed','false'));return}if(box)box.hidden=false;window.__regimeCompare=!!(window.__currentRegimeMetrics&&s===window.__currentCycleStage);renderRegimeReference(s)};
   el.addEventListener('click',open);el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}});
  });
  const toggle=document.getElementById('regimeCompareToggle');if(toggle)toggle.addEventListener('click',()=>{if(window.__selectedRegimeRefStage==null||!window.__currentRegimeMetrics)return;window.__regimeCompare=!window.__regimeCompare;renderRegimeReference(window.__selectedRegimeRefStage)});
 }catch(e){console.warn('regime references',e)}
}
renderCycleStage();loadRegimeReferences();


window.__legacyScoreDetailUnused=function(k){
 const d=window.__marketIndicators,c=window.__conditionComponents||{};if(!d||c[k]==null)return;
 const w={finance:25,sentiment:20,demand:20,value:20,supply:15},t={finance:'금융여건',sentiment:'시장심리',demand:'실수요·거래',value:'가격·밸류',supply:'공급·전세'},m=d.m2_official||d.m2,x=d.matched_period,s=d.kb_sentiment||{},v=d.kb_value||{},val=z=>z==null?'—':Number(z).toFixed(1),body={
  finance:'현재 '+Math.round(c.finance)+'/100 · M2 전월비 '+val(m?.mom_pct)+'% · 전년비 '+val(m?.yoy_pct)+'%<br><b>산식</b> 50 + M2 전월비×8 + M2 전년비×1.5',
  sentiment:'현재 '+Math.round(c.sentiment)+'/100 · 매수우위 '+val(s.latest?.매수우위?.value)+' · 거래활발 '+val(s.latest?.매매거래활발?.value),
  demand:'현재 '+Math.round(c.demand)+'/100 · 동일기간 거래 '+(x?.changes?.trade_count_pct==null?'—':signed(x.changes.trade_count_pct,'%'))+' · ≤15억 비중 '+(x?.changes?.under15_share_pp==null?'—':signed(x.changes.under15_share_pp,'%p')),
  value:'현재 '+Math.round(c.value)+'/100 · PIR '+(v.components?.pir?.value==null?'—':Number(v.components.pir.value).toFixed(2)+'배')+' · 전세가율 '+(v.components?.rent_ratio?.value_pct==null?'—':Number(v.components.rent_ratio.value_pct).toFixed(1)+'%')+' · 장기추세 '+(v.components?.trend_gap?.value_pct==null?'—':signed(v.components.trend_gap.value_pct,'%')),
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
 const host=document.getElementById('forecastGrid'),meta=document.getElementById('forecastMeta');if(!host)return;
 const fmtMonth=v=>{const z=String(v||'');return z.length===6?z.slice(0,4)+'.'+z.slice(4):z};
 const fallbackDisplay=w=>{
  const d=Number(w?.downturn||0),r=Number(w?.reacceleration||0),v=Math.round(d),band=v<=19?0:v<=29?1:v<=34?2:v<=44?3:v<=54?4:5;
  const labels=['상승 우위','재상승 가능성 확대','혼조·방향 탐색','쉬어가기·하방 경계','조정 위험 확대','하락 우위'];
  const tones=['very_low','low','mixed','watch','high','very_high'];
  let secondary=band===0?(r>=40?'재상승 신호 강함':'하방 위험 낮음'):band===1?(r>=35?'재상승 신호 강화':r>=25?'재상승 여지 확대':'하방 위험 낮아지는 중'):band===2?(r>=35?'재상승 신호와 하방 위험 경합':'방향성 확인 필요'):band===3?(r>=35?'하방 경계 속 재상승 신호 공존':'하방 위험 주의'):band===4?'재상승 신호보다 조정 위험 우세':'하락 시나리오 우세';
  return{risk_band:band,headline:labels[band],tone:tones[band],downturn_weight:d,reacceleration_weight:r,secondary};
 };
 try{
  const d=await fetch('regime_forecast.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('forecast '+r.status);return r.json()});
  const hs=d.horizons||[],displays=hs.map(h=>h.display||fallbackDisplay(h.weights||{}));
  const currentPhase=d.state?.current_phase||window.__marketJudgment?.heads?.current_state?.label||'현재 국면';
  const nodes=[{label:'현재',headline:currentPhase,tone:'current'},...hs.map((h,i)=>({label:h.label||h.period,headline:displays[i]?.headline||'방향 확인 중',tone:displays[i]?.tone||'mixed'}))];
  host.innerHTML=nodes.map((n,i)=>'<div class="forecast-route-node-v181 tone-'+esc(n.tone)+'"><small>'+esc(n.label)+'</small><b>'+esc(n.headline)+'</b></div>'+(i<nodes.length-1?'<i class="forecast-route-arrow-v181">→</i>':'')).join('');
  if(meta){meta.hidden=true;meta.textContent='현재 판단에 사용한 연구 데이터 '+fmtMonth(d.latest_research_month)+(d.latest_research_provisional?' · 잠정':'')+' · 검증 완료 '+fmtMonth(d.latest_certified_backtest_month)+'까지';}
  const hb=document.getElementById('hubBacktestMeta');if(hb)hb.textContent='인증 '+fmtMonth(d.latest_certified_backtest_month)+' · 연구 '+fmtMonth(d.latest_research_month);
 }catch(e){
  console.warn('forecast render',e);host.innerHTML='<div class="forecast-route-node-v181"><small>전망엔진</small><b>데이터 확인 중</b></div>';if(meta){meta.hidden=false;meta.textContent='전망 데이터를 확인하고 있습니다.';}
 }
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

  window.__marketExtensions=d;
  const v=d.validation||{};
  set('contextValidation',v.breadth_role==='confidence_context'?'상승 확산도 검증 통과 · 국면 신뢰도 보강에 사용':'상승 확산도 연구 검증 중');
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



/* evidence-first detail panels v136 */
function renderTradeDistribution(x){
 const host=document.getElementById('volumeChart');if(!host||!x?.current||!x?.previous)return;
 const get=z=>z.buckets3||{'<=15eok':Number(z.counts?.['<=9eok']||0)+Number(z.counts?.['9-15eok']||0),'15-25eok':Number(z.counts?.['15-25eok']||0),'25eok+':Number(z.counts?.['25eok+']||0)};
 const keys=[['<=15eok','≤15억'],['15-25eok','15~25억'],['25eok+','25억+']],cb=get(x.current),pb=get(x.previous),ct=Number(x.current.total||0)||1,pt=Number(x.previous.total||0)||1;
 const rows=keys.map(([k,label])=>{const prev=Number(pb[k]||0)/pt*100,cur=Number(cb[k]||0)/ct*100,delta=cur-prev,max=5,pos=Math.min(100,Math.abs(delta)/max*50),dir=delta>0?'up':delta<0?'down':'flat';return '<div class="share-shift-row-v143"><div class="share-shift-head-v143"><b>'+label+'</b><span>'+prev.toFixed(1)+'% <i>→</i> '+cur.toFixed(1)+'%</span><em class="'+dir+'">'+(delta>0?'+':'')+delta.toFixed(1)+'%p</em></div><div class="share-shift-rail-v143"><i class="zero"></i><u class="'+dir+'" style="width:'+pos+'%;'+(delta>=0?'left:50%':'right:50%')+'"></u></div><small>'+Number(pb[k]||0).toLocaleString('ko-KR')+'건 → '+Number(cb[k]||0).toLocaleString('ko-KR')+'건</small></div>'}).join('');
 host.innerHTML='<div class="share-shift-chart-v143"><div class="share-shift-title-v143"><b>가격대 구성비 변화</b><span>0%p 기준 · ±5%p 확대</span></div>'+rows+'<div class="share-shift-period-v143"><span>'+sourcePeriodFmt(x.previous.period)+' '+x.previous.range+'</span><i>vs</i><span>'+sourcePeriodFmt(x.current.period)+' '+x.current.range+'*</span></div></div><small class="dist-note-v136">* 당월은 신고 진행 중이라 건수보다 가격대 구성비 변화에 초점을 둡니다.</small>';
}
async function renderBacktestSummary(){
 try{
  const d=await fetch('final_backtest.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()),rows=d.rows||[],first=rows[0]?.ym,last=rows[rows.length-1]?.ym,corr=d.metrics?.score_vs_fwd_6m_corr;
  const ym=v=>String(v||'').length===6?String(v).slice(0,4)+'.'+String(v).slice(4):String(v||'—');
  const set=(id,v)=>{const x=document.getElementById(id);if(x)x.textContent=v};
  set('backtestScope',rows.length+'개월 · '+ym(first)+'~'+ym(last));set('backtestCertified',ym(d.certified_through)+' · 미래정보 차단');set('backtestCorr',corr==null?'—':(Number(corr)>=0?'+':'')+Number(corr).toFixed(2));
  const low=d.metrics?.low_score_mean_fwd_6m_pct,high=d.metrics?.high_score_mean_fwd_6m_pct;
  set('backtestCaution',low==null||high==null?'현재 점수공식을 과거 시점 데이터에만 적용해 검증합니다.':'과거 '+rows.length+'개월에서 점수와 이후 6개월 가격의 관계를 확인합니다. 낮은 점수 구간 평균 '+(low>=0?'+':'')+Number(low).toFixed(2)+'%, 높은 점수 구간 '+(high>=0?'+':'')+Number(high).toFixed(2)+'%. 예측값이 아니라 검증 참고치입니다.');
  const hb=document.getElementById('hubBacktestMeta');if(hb)hb.textContent=rows.length+'개월 검증 · 인증 '+ym(d.certified_through);
 }catch(e){console.warn('backtest summary',e)}
}
function renderDataStatusPanel(){
 const d=window.__marketIndicators,m=window.__watchMarket;if(!d&&!m)return;
 const set=(id,v)=>{const x=document.getElementById(id);if(x)x.textContent=v};
 if(d){
  const src=d.refresh_run?.sources||{},matched=d.matched_period||{},sent=d.kb_sentiment||{},m2=d.m2_official||d.m2||{},mort=d.mortgage_rate_official||{},base=d.base_rate_official?.latest||{},sale=d.kb_weekly_sale_index?.latest||{},rent=d.kb_weekly_rent_index?.latest||{};
  const uns=d.unsold_seoul||{};set('sourceMolitStatus',(src.molit==='connected'?'정상':'지연')+(matched.current?.total!=null?' · 실거래 '+Number(matched.current.total).toLocaleString('ko-KR')+'건':''));set('sourceMolitMeta','미분양 '+(uns.seoul_units==null?'—':Number(uns.seoul_units).toLocaleString('ko-KR')+'호')+' · '+(matched.current?.period?sourcePeriodFmt(matched.current.period)+' 계약일 기준':''));
  set('sourceKbStatus',(src.kb_sentiment==='connected'?'정상':'지연')+(sale.value!=null?' · 매매 '+Number(sale.value).toFixed(2):''));set('sourceKbMeta',(sale.date?sourcePeriodFmt(sale.date)+' · ':'')+'전세 '+(rent.value==null?'—':Number(rent.value).toFixed(2))+' · 심리 포함');
  set('sourceEcosStatus',(src.ecos==='connected'?'정상':'지연')+(mort.rate_pct!=null?' · 주담대 '+Number(mort.rate_pct).toFixed(2)+'%':''));set('sourceEcosMeta','M2 '+(m2.yoy_pct==null?'—':(Number(m2.yoy_pct)>0?'+':'')+Number(m2.yoy_pct).toFixed(1)+'% YoY')+' · 기준금리 '+(base.rate_pct==null?'—':Number(base.rate_pct).toFixed(2)+'%'));
 }
 if(m){
  const exact=Number(m.exact_kb_rows||0),trade=Number(m.molit_trade_matched_rows||0),list=Number(m.listing_refresh_matched_rows||0),total=(m.items||[]).length,status=String(m.listing_refresh_status||'');
  set('sourceWatchStatus','KB '+exact+'/'+total+' · 실거래 '+trade+'/'+total);set('sourceWatchMeta',(status==='connected'?'매물 '+list+'/'+total+' 최신 연결':status==='partial_last_good'?'매물 '+list+'/'+total+' 최신 · 나머지 마지막 정상/미연결':'매물 원천 지연')+' · '+(m.listing_collected_at?refreshCalendarStamp(refreshStamp(m.listing_collected_at)):'시각 확인 대기'));

 }
}
renderBacktestSummary();

/* refresh calendar + semantic change history v135 */
const REFRESH_SNAPSHOT_KEY='kbpm.refresh.snapshot.v3';
const REFRESH_CHANGE_TTL=24*60*60*1000;
const refreshJson=async path=>{try{const r=await fetch(path+'?v='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error(path+' '+r.status);return await r.json()}catch(e){console.warn('refresh-meta',e);return null}};
const refreshStamp=v=>{const d=new Date(v||0);return Number.isFinite(d.getTime())?d:null};
const refreshMax=(...vals)=>{const ds=vals.flat().map(refreshStamp).filter(Boolean);return ds.length?new Date(Math.max(...ds.map(d=>d.getTime()))):null};
const refreshFmt=d=>d?new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(d):'확인 대기';
const refreshShortFmt=d=>{if(!d)return'확인 대기';const now=new Date(),parts=z=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(z),same=parts(d)===parts(now);return (same?'오늘 ':new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric'}).format(d)+' ')+new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(d)};
const refreshScheduleFmt=d=>d?new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(d):'—';
const refreshDayKey=d=>d?new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(d):'';
const refreshClock=d=>d?new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(d):'—';
const refreshDateLabel=d=>d?new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',weekday:'short'}).formatToParts(d).reduce((a,p)=>{a[p.type]=p.value;return a},{}):null;
const refreshDateText=d=>{const p=refreshDateLabel(d);return p?p.month+'/'+p.day+'('+p.weekday+')':'—'};
const refreshRelativeDay=d=>{
 if(!d)return'';
 const now=new Date(),today=refreshDayKey(now),target=refreshDayKey(d);
 const tomorrow=refreshDayKey(new Date(now.getTime()+86400000));
 const yesterday=refreshDayKey(new Date(now.getTime()-86400000));
 if(target===today)return'오늘';
 if(target===tomorrow)return'내일';
 if(target===yesterday)return'어제';
 return'';
};
const refreshCalendarStamp=d=>{if(!d)return'확인 대기';const rel=refreshRelativeDay(d),clock=refreshClock(d),date=refreshDateText(d);return rel?(rel+' '+clock+(rel==='오늘'?'':' · '+date)):(date+' '+clock)};
const refreshCalendarSchedule=d=>{if(!d)return'—';const rel=refreshRelativeDay(d),clock=refreshClock(d),date=refreshDateText(d);if(rel)return rel+' '+clock+' · '+date;const wd=new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',weekday:'long'}).format(d);return wd+' '+clock+' · '+date};
const refreshKstParts=()=>{const p=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));return{y:+p.year,m:+p.month,d:+p.day,w:{Sun:0,Mon:1,Tue:2,Wed:3,Thu:4,Fri:5,Sat:6}[p.weekday],hh:+p.hour,mm:+p.minute}};
const refreshKstDate=(y,m,d,h,min)=>new Date(Date.UTC(y,m-1,d,h-9,min));
const refreshTodayDaily=()=>{const n=refreshKstParts();return refreshKstDate(n.y,n.m,n.d,7,5)};
const refreshNextDaily=()=>{const n=refreshKstParts(),after=n.hh>7||(n.hh===7&&n.mm>=5),base=refreshTodayDaily();return after?new Date(base.getTime()+86400000):base};
const refreshDailyDueState=last=>{const n=refreshKstParts(),due=refreshTodayDaily(),after=n.hh>7||(n.hh===7&&n.mm>=5),lastDate=refreshStamp(last);return{due,after,overdue:Boolean(after&&(!lastDate||lastDate.getTime()<due.getTime()))}};
const refreshNextWeekly=()=>{const n=refreshKstParts();let delta=(5-n.w+7)%7;if(delta===0&&(n.hh>21||(n.hh===21&&n.mm>=5)))delta=7;return new Date(refreshKstDate(n.y,n.m,n.d,21,5).getTime()+delta*86400000)};
const refreshNextMonthly=()=>{const n=refreshKstParts();let y=n.y,m=n.m;let d=refreshKstDate(y,m,3,7,20);if(Date.now()>=d.getTime()){m+=1;if(m===13){m=1;y+=1}d=refreshKstDate(y,m,3,7,20)}return d};
const refreshReadState=()=>{try{const x=JSON.parse(localStorage.getItem(REFRESH_SNAPSHOT_KEY)||'{}');return{xVersion:3,items:x.items||{}}}catch{return{xVersion:3,items:{}}}};
const refreshWriteState=s=>{try{localStorage.setItem(REFRESH_SNAPSHOT_KEY,JSON.stringify(s))}catch{}};
const refreshSig=v=>JSON.stringify(v);
const refreshNum=v=>v==null||!Number.isFinite(Number(v))?null:Number(v);
const refreshClamp=v=>Math.max(0,Math.min(100,v));
const refreshComponents=d=>{const m=d?.m2_official||d?.m2,matched=d?.matched_period;return{
 finance:m?.mom_pct!=null&&m?.yoy_pct!=null?refreshClamp(50+Number(m.mom_pct)*8+Number(m.yoy_pct)*1.5):null,
 sentiment:d?.kb_sentiment?.score_0_100==null?null:Number(d.kb_sentiment.score_0_100),
 demand:matched?.changes?.trade_count_pct!=null&&matched?.changes?.under15_share_pp!=null?refreshClamp(50+Number(matched.changes.trade_count_pct)*.35+Number(matched.changes.under15_share_pp)*1.5):null,
 value:d?.kb_value?.score_0_100==null?null:Number(d.kb_value.score_0_100),
 supply:d?.kb_sentiment?.jeonse_score_0_100==null?null:Number(d.kb_sentiment.jeonse_score_0_100)
}};
function refreshTrack(state,key,label,signature,value,checkedAt,countable=true){
 const now=Date.now(),sig=refreshSig(signature),prev=state.items[key],changed=Boolean(prev&&prev.sig!==sig);
 const changedAt=changed?now:(prev&&prev.sig===sig?Number(prev.changedAt||0):0);
 const from=changed?prev.value:(prev?.from??null),to=value;
 const active=Boolean(changedAt&&now-changedAt<REFRESH_CHANGE_TTL);
 state.items[key]={sig,value,from,changedAt,checkedAt:checkedAt||null,label,countable};
 return{key,label,value,from,changedAt,active,changed,checkedAt:refreshStamp(checkedAt),countable,initialized:Boolean(prev)};
}
function decorateRefreshPanel({key,host,anchor,record,checkedAt,warning='',note=true}){
 if(!host||!anchor)return;
 host.querySelectorAll('.panel-refresh-dot,.panel-refresh-note,.panel-refresh-chip-v135,.panel-refresh-change-v135').forEach(x=>x.remove());
 host.classList.toggle('has-fresh-change-v135',Boolean(record?.active&&!warning));
 const chip=document.createElement('span');chip.className='panel-refresh-chip-v135';
 const stamp=refreshShortFmt(refreshStamp(checkedAt)||record?.checkedAt);
 if(warning){chip.classList.add('warning');chip.textContent=stamp+' · 원천 확인'}
 else if(record?.active){chip.classList.add('changed');chip.textContent=stamp+' · 갱신됨'}
 else{chip.textContent=stamp+' · 변경 없음'}
 anchor.insertAdjacentElement('afterend',chip);
 if(note&&record?.active&&record.from!=null&&record.value!=null&&String(record.from)!==String(record.value)){
   const detail=document.createElement('span');detail.className='panel-refresh-change-v135';detail.textContent=String(record.from)+' → '+String(record.value);chip.insertAdjacentElement('afterend',detail);
 }
}
function decorateFactorRefresh(card,record,checkedAt){
 if(!card||card.closest('#judgmentEvidenceDrawer'))return;
 card.querySelectorAll('.factor-refresh-v135,.factor-change-v135').forEach(x=>x.remove());
 card.classList.toggle('has-fresh-change-v135',Boolean(record?.active));
 const head=card.querySelector('.factor-card-head-v134'),score=card.querySelector('.factor-score-v134');
 const chip=document.createElement('span');chip.className='factor-refresh-v135'+(record?.active?' changed':'');
 chip.textContent=record?.active?refreshShortFmt(refreshStamp(checkedAt))+' 갱신':refreshShortFmt(refreshStamp(checkedAt))+' 확인 · 변경 없음';
 if(head)head.insertAdjacentElement('afterend',chip);
 const a=refreshNum(record?.from),b=refreshNum(record?.value);
 if(record?.active&&score){
   const change=document.createElement('div');change.className='factor-change-v135';
   if(a!=null&&b!=null&&Math.round(a)!==Math.round(b)){const delta=Math.round(b)-Math.round(a);change.innerHTML='<span>이전 '+Math.round(a)+'</span><i>→</i><b>'+Math.round(b)+'</b><em>'+(delta>0?'+':'')+delta+'</em>'}
   else change.textContent='입력 데이터 갱신';
   score.insertAdjacentElement('afterend',change);
 }
}
async function initRefreshCalendar(){
 const [mi,market,master,forecast,extensions,hist,backtest,research]=await Promise.all([
   refreshJson('market_indicators.json'),refreshJson('buy_watchlist_market.json'),refreshJson('buy_watchlist_master.json'),
   refreshJson('regime_forecast.json'),refreshJson('market_extensions.json'),refreshJson('kb_watchlist_history.json'),
   refreshJson('final_backtest.json'),refreshJson('turning_signal_research.json')
 ]);
 const src=mi?.refresh_run?.sources||{},delayed=Object.entries(src).filter(([,v])=>v!=='connected').map(([k])=>({molit:'국토부',ecos:'ECOS',kb_sentiment:'KB',watchlist_detail:'단지상세'}[k]||k));
 const listingFallback=market&&String(market.listing_refresh_status||'')!=='connected';
 const dailyRev=mi?.refresh_run?.attempted_at||mi?.updated_at;
 const kbRev=master?.kb_collected_at||master?.generated_at;
 const watchRev=refreshMax(kbRev,market?.molit_trade_collected_at,market?.kb_detail_collected_at,String(market?.listing_refresh_status)==='connected'?market?.listing_collected_at:null)?.toISOString();
 const forecastRev=forecast?.generated_at;
 const extensionRev=extensions?.generated_at;
 const monthlyRev=refreshMax(backtest?.generated_at,research?.generated_at)?.toISOString();
 const healthRev=refreshMax(dailyRev,market?.listing_refresh_attempted_at,hist?.generated_at,forecastRev,extensionRev,monthlyRev)?.toISOString();
 const statuses=mi?.data_status||{},critical=Object.entries(statuses).filter(([k,v])=>v!=='connected'&&!['watchlist_detail_refresh'].includes(k)).map(([k])=>k);
 const state=refreshReadState(),records=[],components=refreshComponents(mi),m=mi?.m2_official||mi?.m2||{},sent=mi?.kb_sentiment||{},matched=mi?.matched_period||{},val=mi?.kb_value||{};

 const factorDefs={
  finance:{label:'금융',value:components.finance,sig:{score:components.finance,m2:[m.period,m.mom_pct,m.yoy_pct],mortgage:[mi?.mortgage_rate_official?.period,mi?.mortgage_rate_official?.rate_pct],base:[mi?.base_rate_official?.latest?.date,mi?.base_rate_official?.latest?.rate_pct]}},
  sentiment:{label:'심리',value:components.sentiment,sig:{score:components.sentiment,buy:[sent.latest?.매수우위?.date,sent.latest?.매수우위?.value],trade:[sent.latest?.매매거래활발?.date,sent.latest?.매매거래활발?.value]}},
  demand:{label:'거래',value:components.demand,sig:{score:components.demand,period:matched.current?.period,total:matched.current?.total,under15:matched.current?.under15_share,changes:matched.changes}},
  value:{label:'가격',value:components.value,sig:{score:components.value,period:val.period,pir:[val.components?.pir?.period,val.components?.pir?.value,val.components?.pir?.score_0_100],rent:[val.components?.rent_ratio?.period,val.components?.rent_ratio?.value_pct,val.components?.rent_ratio?.score_0_100],trend:[val.components?.trend_gap?.period,val.components?.trend_gap?.value_pct,val.components?.trend_gap?.score_0_100]}},
  supply:{label:'전세',value:components.supply,sig:{score:components.supply,supply:[sent.latest?.전세수급?.date,sent.latest?.전세수급?.value],activity:[sent.latest?.전세거래활발?.date,sent.latest?.전세거래활발?.value]}}
 };
 for(const [key,d] of Object.entries(factorDefs)){const rec=refreshTrack(state,'factor.'+key,d.label,d.sig,d.value,dailyRev,true);records.push(rec);decorateFactorRefresh(document.querySelector('[data-score-key="'+key+'"]'),rec,dailyRev)}

 const weights={finance:25,sentiment:20,demand:20,value:20,supply:15},avail=Object.keys(components).filter(k=>components[k]!=null),covered=avail.reduce((a,k)=>a+weights[k],0),condition=covered?Math.round(avail.reduce((a,k)=>a+components[k]*weights[k],0)/covered):null;
 const overviewRec=refreshTrack(state,'panel.overview','현재 국면',{condition,factors:components,weekly:[mi?.kb_weekly_sale_index?.latest?.date,mi?.kb_weekly_sale_index?.latest?.change_pct,mi?.kb_weekly_rent_index?.latest?.change_pct]},condition,dailyRev,false);
 const forecastSig={research:forecast?.latest_research_month,cert:forecast?.latest_certified_backtest_month,h:(forecast?.horizons||[]).map(x=>[x.period,x.weights])};
 const forecastValue=(forecast?.horizons||[])[0]?.weights?.consolidation==null?null:Number((forecast.horizons||[])[0].weights.consolidation).toFixed(1);
 const forecastRec=refreshTrack(state,'panel.forecast','전망',forecastSig,forecastValue,forecastRev,true);
 const contextSig={breadth:extensions?.current?.breadth,aff:extensions?.current?.affordability,temp:extensions?.current?.temperature};
 const contextValue=extensions?.current?.breadth?.seoul_25?.up_share_pct??null;
 const contextRec=refreshTrack(state,'panel.context','보조신호',contextSig,contextValue,extensionRev,true);
 const watchItems=(market?.items||[]).map(x=>[x.complex_id,x.area_id,x.sale_listing_count,x.sale_listing_week_delta,x.avg_ask_manwon,x.recent_trade_manwon,x.recent_trade_date]);
 const watchRec=refreshTrack(state,'panel.watchlist','관심단지',{items:watchItems,kb:kbRev},(market?.items||[]).length,watchRev,true);
 const boundarySig=(master?.items||[]).map(x=>[x.complex_id,(x.types||[]).map(t=>[t.area_id,t.general_price_manwon])]);
 const boundaryRec=refreshTrack(state,'panel.boundary','15억 경계',boundarySig,kbRev?refreshFmt(refreshStamp(kbRev)):null,kbRev,false);
 const healthRec=refreshTrack(state,'panel.health','검증상태',{statuses,cert:backtest?.certified_through,research:research?.latest_month||research?.as_of},critical.length,healthRev,false);
 records.push(forecastRec,contextRec,watchRec);

 refreshWriteState(state);
 const countable=records.filter(x=>x.countable),changed=countable.filter(x=>x.active),unchanged=countable.length-changed.length,warningCount=critical.length;
 const set=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v};
 set('refreshChangedCount',changed.length?'실제 변경 '+changed.length+'개':'실제 변경 없음');
 set('refreshUnchangedCount','변경 없음 '+unchanged+'개');
 const wc=document.getElementById('refreshWarningCount');if(wc){wc.hidden=!warningCount;wc.textContent='원천 확인 '+warningCount+'건'}
 const changedEl=document.getElementById('refreshChangedCount');if(changedEl)changedEl.classList.toggle('changed',changed.length>0);
 const dailyDue=refreshDailyDueState(dailyRev);
 if(dailyDue.overdue){
   set('refreshDailyLast','마지막 '+refreshCalendarStamp(refreshStamp(dailyRev))+' 확인 · 오늘 07:05 예정분 미반영');
   set('refreshDailyNext','오늘 갱신 지연/미실행 확인 필요 · 다음 정규 '+refreshCalendarSchedule(refreshNextDaily()));
 }else{
   set('refreshDailyLast','✓ '+refreshCalendarStamp(refreshStamp(dailyRev))+' 갱신 완료 · '+(changed.length?'변경 '+changed.length+'건':'변경 없음'));
   set('refreshDailyNext','다음 갱신 '+refreshCalendarSchedule(refreshNextDaily()));
 }
 set('refreshWeeklyLast','KB 시세 · '+refreshCalendarStamp(refreshStamp(kbRev))+' 기준'+(listingFallback?' · 매물 원천은 마지막 정상값 유지':' · 확인 완료'));
 set('refreshWeeklyNext','다음 점검 '+refreshCalendarSchedule(refreshNextWeekly()));
 set('refreshMonthlyLast','연구엔진 · '+refreshCalendarStamp(refreshStamp(monthlyRev))+' 검증'+(backtest?.certified_through?' · 인증 '+String(backtest.certified_through).slice(0,4)+'.'+String(backtest.certified_through).slice(4):''));
 set('refreshMonthlyNext','다음 검증 '+refreshCalendarSchedule(refreshNextMonthly()));
 const hs=document.getElementById('refreshHealthSummary');if(hs){hs.classList.toggle('warning',Boolean(warningCount));hs.textContent=warningCount?'원천 확인 필요 · 문제가 있는 원천만 마지막 정상값을 유지합니다.':'정상 · 핵심 원천이 확인됐고 실제 값 변화만 갱신 표시합니다.'}
 const ss=document.getElementById('refreshSummaryStatus'),sm=document.getElementById('refreshSummaryMeta');
 if(ss){const dailyDue=refreshDailyDueState(dailyRev),warn=Boolean(warningCount)||dailyDue.overdue;ss.classList.toggle('warning',warn);ss.classList.remove('changed');ss.textContent=dailyDue.overdue?'오늘 갱신 미반영':warningCount?'원천 확인 '+warningCount+'건':'정상'}
 if(sm){const dailyDue=refreshDailyDueState(dailyRev),names=changed.slice(0,4).map(x=>x.label);sm.textContent=dailyDue.overdue?'오늘 07:05 예정분이 아직 반영되지 않았습니다 · 마지막 '+refreshShortFmt(refreshStamp(dailyRev)):refreshShortFmt(refreshStamp(dailyRev))+' 확인 완료 · '+(names.length?names.join(' · ')+' 갱신'+(changed.length>4?' 외 '+(changed.length-4)+'개':''):'주요 지표 값 변화 없음')}
}
initRefreshCalendar();

/* dashboard refinement v133 — infographic details + semantic notification revisions */
(function(){
 const fmt1=v=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toFixed(1);
 const signed1=(v,s='')=>v==null||!Number.isFinite(Number(v))?'—':(Number(v)>0?'+':'')+Number(v).toFixed(1)+s;
 const metric=(label,value,note='')=>'<div class="score-metric-v133"><span>'+label+'</span><b>'+value+'</b>'+(note?'<small>'+note+'</small>':'')+'</div>';
 const verdict=(v)=>v>=65?'우호적':v>=45?'중립권':v>=30?'부담':'부담 큼';
 window.__legacyScoreDetailUnused=function(k){
   const d=window.__marketIndicators,c=window.__conditionComponents||{};if(!d||c[k]==null)return;
   const w={finance:25,sentiment:20,demand:20,value:20,supply:15};
   const t={finance:'금융여건',sentiment:'시장심리',demand:'실수요·거래',value:'가격·밸류',supply:'공급·전세'};
   const m=d.m2_official||d.m2||{},x=d.matched_period||{},s=d.kb_sentiment||{},v=d.kb_value||{},score=Math.round(Number(c[k])),band=status(score),mort=d.mortgage_rate_official||{};
   const blocks={
    finance:[metric('M2 전월비',signed1(m.mom_pct,'%'),'유동성 단기 변화'),metric('M2 전년비',signed1(m.yoy_pct,'%'),'유동성 장기 변화'),metric('주담대',d.mortgage_rate_official?.rate_pct==null?'—':fmt1(d.mortgage_rate_official.rate_pct)+'%','신규취급액 기준')],
    sentiment:[metric('매수우위',fmt1(s.latest?.매수우위?.value),'KB 서울'),metric('거래활발',fmt1(s.latest?.매매거래활발?.value),'KB 서울'),metric('심리점수',fmt1(s.score_0_100),'100점 환산')],
    demand:[metric('동일기간 거래',signed1(x.changes?.trade_count_pct,'%'),'전월 같은 계약일'),metric('≤15억 비중',x.current?.under15_share==null?'—':fmt1(x.current.under15_share)+'%','현재 동일기간'),metric('비중 변화',signed1(x.changes?.under15_share_pp,'%p'),'전월 대비')],
    value:[metric('PIR',v.components?.pir?.value==null?'—':fmt1(v.components.pir.value)+'배','소득 대비 가격 · 40%'),metric('전세가율',v.components?.rent_ratio?.value_pct==null?'—':fmt1(v.components.rent_ratio.value_pct)+'%','전세가치 지지력 · 30%'),metric('장기추세 괴리',v.components?.trend_gap?.value_pct==null?'—':signed1(v.components.trend_gap.value_pct,'%'),'60개월 로그추세 대비 · 30%')],
    supply:[metric('전세수급',fmt1(s.latest?.전세수급?.value),'KB 서울'),metric('전세거래',fmt1(s.latest?.전세거래활발?.value),'KB 서울'),metric('전세점수',fmt1(s.jeonse_score_0_100),'100점 환산')]
   };
   const formula={finance:'M2의 전월·전년 변화와 주담대 금리 수준을 함께 반영',sentiment:'KB 매수우위·매매거래활발 지수를 동일 기준으로 환산',demand:'당월과 전월의 동일 계약일 구간 거래량·가격대 비중 비교',value:'KB 서울 PIR 40% + 전세가율 30% + 60개월 장기추세 괴리 30%를 각 시점 역사 백분위로 합성',supply:'KB 전세수급·전세거래활발 지표를 결합'}[k];
   const body=document.getElementById('scoreExplainBody'),p=document.getElementById('scoreExplanation');if(!body||!p)return;
   setText('scoreExplainTitle',t[k]);setText('scoreExplainWeight','전체 점수 가중치 '+w[k]+'%');
   body.innerHTML='<div class="score-infographic"><div class="score-hero-v133"><div class="score-ring-v133" style="--score:'+Math.max(0,Math.min(100,score))+'"><b>'+score+'<small>/100</small></b></div><div class="score-hero-copy-v133"><strong>'+verdict(score)+'</strong><p>현재 수치를 먼저 보여주고, 아래에서 무엇이 이 점수를 만들었는지 바로 비교합니다.</p></div></div><div class="score-metrics-v133">'+blocks[k].join('')+'</div><div class="score-formula-v133"><b>산정 기준</b> · '+formula+'</div></div>';
   p.hidden=false;p.style.display='block';document.querySelectorAll('.score-component[data-score-key]').forEach(card=>{const on=card.dataset.scoreKey===k;card.setAttribute('aria-expanded',on?'true':'false');card.classList.toggle('active',on)});p.scrollIntoView({behavior:'smooth',block:'center'});
 };


})();


/* v134 factor detail renderer — one stable responsive panel */
(function(){
 const fmt1=v=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toFixed(1);
 const signed1=(v,s='')=>v==null||!Number.isFinite(Number(v))?'—':(Number(v)>0?'+':'')+Number(v).toFixed(1)+s;
 const metric=(label,value,note='')=>'<div class="factor-detail-metric-v134"><span>'+label+'</span><b>'+value+'</b>'+(note?'<small>'+note+'</small>':'')+'</div>';
 const status=v=>scoreBand(v);
 const desc={
  finance:'금리와 통화량을 묶어 자금 조달 환경을 봅니다.',
  sentiment:'KB 매수심리와 거래심리를 함께 봅니다.',
  demand:'실제 계약 건수와 가격대별 수요 이동을 봅니다.',
  value:'서울 집값을 소득·전세가치·장기 가격추세의 세 축으로 함께 봅니다.',
  supply:'전세수급과 전세거래 흐름으로 주거 수요 압력을 봅니다.'
 };
 window.showScoreDetail=function(k){
   const d=window.__marketIndicators,c=window.__conditionComponents||{};if(!d||c[k]==null)return;
   const p0=document.getElementById('scoreExplanation'),active=document.querySelector('.score-component[data-score-key="'+k+'"].active');
   if(p0&&!p0.hidden&&active){window.hideScoreDetail?.();return;}
   const weights={finance:25,sentiment:20,demand:20,value:20,supply:15};
   const title={finance:'금융여건',sentiment:'시장심리',demand:'실수요·거래',value:'가격·밸류',supply:'공급·전세'};
   const m=d.m2_official||d.m2||{},x=d.matched_period||{},s=d.kb_sentiment||{},v=d.kb_value||{},mort=d.mortgage_rate_official||{},score=Math.round(Number(c[k])),band=status(score);
   const blocks={
    finance:[
      metric('M2 전월비',signed1(m.mom_pct,'%'),m.mom_change_pp==null?'전월 변화 대기':'직전월보다 '+signed1(m.mom_change_pp,'%p')),
      metric('M2 전년비',signed1(m.yoy_pct,'%'),m.yoy_change_pp==null?'전월 변화 대기':'직전월보다 '+signed1(m.yoy_change_pp,'%p')),
      metric('주담대 금리',mort.rate_pct==null?'—':fmt1(mort.rate_pct)+'%',mort.change_pp==null?'전월 변화 대기':'직전월보다 '+signed1(mort.change_pp,'%p'))
    ],
    sentiment:[
      metric('매수우위',fmt1(s.latest?.매수우위?.value),(s.changes?.매수우위==null?'전주 변화 대기':'전주 '+signed1(s.changes.매수우위,''))),
      metric('거래활발',fmt1(s.latest?.매매거래활발?.value),(s.changes?.매매거래활발==null?'전주 변화 대기':'전주 '+signed1(s.changes.매매거래활발,''))),
      metric('심리점수',fmt1(s.score_0_100),(s.score_change==null?'직전 변화 대기':'전주 '+signed1(s.score_change,'')+'점'))
    ],
    demand:[
      metric('동일기간 거래',signed1(x.changes?.trade_count_pct,'%'),'전월 같은 계약일'),
      metric('15억 이하',x.current?.under15_share==null?'—':fmt1(x.current.under15_share)+'%','현재 비중'),
      metric('비중 변화',signed1(x.changes?.under15_share_pp,'%p'),'전월 대비')
    ],
    value:[
      metric('PIR',v.components?.pir?.value==null?'—':fmt1(v.components.pir.value)+'배','소득 대비 가격 · 점수 '+fmt1(v.components?.pir?.score_0_100)),
      metric('전세가율',v.components?.rent_ratio?.value_pct==null?'—':fmt1(v.components.rent_ratio.value_pct)+'%','전세가치 지지력 · 점수 '+fmt1(v.components?.rent_ratio?.score_0_100)),
      metric('장기추세 괴리',v.components?.trend_gap?.value_pct==null?'—':signed1(v.components.trend_gap.value_pct,'%'),'60개월 로그추세 대비 · 점수 '+fmt1(v.components?.trend_gap?.score_0_100))
    ],
    supply:[
      metric('전세수급',fmt1(s.latest?.전세수급?.value),(s.changes?.전세수급==null?'100=균형':'전주 '+signed1(s.changes.전세수급,'')+' · 100=균형')),
      metric('전세거래',fmt1(s.latest?.전세거래활발?.value),(s.changes?.전세거래활발==null?'전주 변화 대기':'전주 '+signed1(s.changes.전세거래활발,''))),
      metric('전세점수',fmt1(s.jeonse_score_0_100),(s.jeonse_score_change==null?'100점 환산':'전주 '+signed1(s.jeonse_score_change,'')+'점'))
    ]
   };
   const method={
    finance:'M2 전월·전년 변화와 주담대 금리 수준을 함께 반영',
    sentiment:'KB 매수우위·매매거래활발 지수를 동일 기준으로 환산',
    demand:'당월과 전월의 동일 계약일 구간 거래량·가격대 비중 비교',
    value:'PIR 40% + 전세가율 30% + 60개월 장기추세 괴리 30% · 각 지표는 해당 시점까지의 역사 백분위로 환산',
    supply:'KB 전세수급·전세거래활발 지표를 결합'
   };
   const p=document.getElementById('scoreExplanation'),body=document.getElementById('scoreExplainBody');if(!p||!body)return;
   p.classList.add('factor-detail-shell-v134');
   setText('scoreExplainTitle',title[k]);
   setText('scoreExplainWeight','전체 점수 가중치 '+weights[k]+'%');
   body.innerHTML='<div class="factor-detail-v134"><div class="factor-detail-hero-v134"><div class="factor-detail-score-v134"><span>현재 점수</span><strong>'+score+'<small>/100</small></strong><div class="factor-detail-progress-v134"><i style="width:'+Math.max(0,Math.min(100,score))+'%"></i></div></div><div class="factor-detail-copy-v134"><strong>'+band.label+' <small>('+band.range+'점)</small></strong><p><b>'+score+'점은 '+band.label+'입니다.</b> '+band.comment+' · '+desc[k]+'</p><div class="score-band-scale-v140"><i></i><i></i><i></i><i></i><i></i><u style="left:'+Math.max(0,Math.min(100,score))+'%"></u></div><small class="score-band-labels-v140">매우제약 · 제약 · 중립 · 개선 · 우호</small></div></div><div class="factor-detail-metrics-v134">'+blocks[k].join('')+'</div><div class="factor-detail-method-v134"><b>산정 기준</b><span>'+method[k]+'</span></div></div>';
   p.hidden=false;p.style.display='block';
   document.querySelectorAll('.score-component[data-score-key]').forEach(card=>{const on=card.dataset.scoreKey===k;card.setAttribute('aria-expanded',on?'true':'false');card.classList.toggle('active',on)});
   p.scrollIntoView({behavior:'smooth',block:'nearest'});
 };
})();

const brandHome=document.getElementById('brandHome');if(brandHome)brandHome.addEventListener('click',e=>{e.preventDefault();window.location.reload()});


/* v197 manual five-factor API refresh */
(function(){
 const OWNER='jagama90',REPO='kb-price-monitor',WORKFLOW='parallel-market-refresh.yml';
 const TOKEN_KEY='kbpm.github.actions.token.session.v1';
 const PENDING_KEY='kbpm.manual.refresh.pending.v1';
 const btn=document.getElementById('manualRefreshButton');
 const host=document.getElementById('manualFactorRefresh');
 const statusEl=document.getElementById('manualRefreshStatus');
 if(!btn||!host||!statusEl)return;
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 const api=(path,token,opts={})=>fetch('https://api.github.com'+path,{
   ...opts,
   headers:{
     Accept:'application/vnd.github+json',
     'X-GitHub-Api-Version':'2022-11-28',
     ...(token?{Authorization:'Bearer '+token}:{}),
     ...(opts.headers||{})
   },
   cache:'no-store'
 });
 const setState=(text,state='')=>{
   statusEl.textContent=text;
   host.classList.remove('running','success','error');
   if(state)host.classList.add(state);
 };
 function getToken(){
   let token='';
   try{token=sessionStorage.getItem(TOKEN_KEY)||''}catch{}
   if(token)return token;
   token=(window.prompt(
     '수동 갱신을 실행하려면 GitHub fine-grained PAT가 필요합니다.\n\n'+
     '저장소: jagama90/kb-price-monitor\n권한: Actions · Read and write\n\n'+
     '토큰은 이 브라우저 탭의 sessionStorage에만 보관됩니다.'
   )||'').trim();
   if(token){try{sessionStorage.setItem(TOKEN_KEY,token)}catch{}}
   return token;
 }
 async function currentRevision(){
   try{
     const d=await fetch('market_indicators.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null);
     return d?.refresh_run?.attempted_at||d?.updated_at||null;
   }catch{return null}
 }
 async function findRun(token,dispatchedAt){
   const r=await api('/repos/'+OWNER+'/'+REPO+'/actions/workflows/'+WORKFLOW+'/runs?event=workflow_dispatch&branch=main&per_page=8',token);
   if(!r.ok)throw Error('워크플로우 상태 조회 실패 ('+r.status+')');
   const data=await r.json(),cut=dispatchedAt-15000;
   return (data.workflow_runs||[]).find(x=>new Date(x.created_at).getTime()>=cut)||null;
 }
 async function waitRun(token,pending){
   let run=pending.runId?{id:pending.runId}:null;
   for(let i=0;i<180;i++){
     if(!run?.id){
       run=await findRun(token,pending.dispatchedAt);
       if(run?.id){
         pending.runId=run.id;
         try{sessionStorage.setItem(PENDING_KEY,JSON.stringify(pending))}catch{}
       }
     }else{
       const r=await api('/repos/'+OWNER+'/'+REPO+'/actions/runs/'+run.id,token);
       if(!r.ok)throw Error('실행 상태 조회 실패 ('+r.status+')');
       run=await r.json();
     }
     if(run?.id){
       if(run.status==='completed'){
         if(run.conclusion!=='success')throw Error('API 갱신 실행이 '+(run.conclusion||'실패')+'로 종료됐습니다.');
         return run;
       }
       setState('원천 API 갱신 중 · '+(run.status==='queued'?'대기 중':'수집·검증 실행 중'),'running');
     }else{
       setState('갱신 요청 접수 · 실행 시작을 확인하는 중','running');
     }
     await sleep(8000);
   }
   throw Error('API 갱신 실행 확인 시간이 초과됐습니다.');
 }
 async function waitProduction(beforeRevision){
   setState('API 수집 완료 · 검증/배포 반영을 확인하는 중','running');
   for(let i=0;i<120;i++){
     try{
       const [m,j]=await Promise.all([
         fetch('market_indicators.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null),
         fetch('market_judgment.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null)
       ]);
       const rev=m?.refresh_run?.attempted_at||m?.updated_at||null;
       const consistent=Boolean(m&&j&&j.as_of===m.updated_at);
       if(rev&&rev!==beforeRevision&&consistent){
         setState('최신 데이터 반영 완료 · 화면을 다시 불러옵니다.','success');
         try{sessionStorage.removeItem(PENDING_KEY)}catch{}
         await sleep(1200);
         location.reload();
         return;
       }
     }catch{}
     await sleep(10000);
   }
   throw Error('갱신은 완료됐지만 Pages 반영 확인 시간이 초과됐습니다. 잠시 후 새로고침해 주세요.');
 }
 async function runManualRefresh(resume=false){
   if(btn.disabled)return;
   const token=getToken();
   if(!token){setState('토큰 입력이 취소되어 갱신하지 않았습니다.');return}
   btn.disabled=true;
   btn.textContent='↻ 갱신 중';
   try{
     let pending=null;
     try{pending=JSON.parse(sessionStorage.getItem(PENDING_KEY)||'null')}catch{}
     if(!resume||!pending){
       const beforeRevision=await currentRevision();
       const dispatchedAt=Date.now();
       setState('GitHub Actions에 API 갱신을 요청하는 중','running');
       const r=await api('/repos/'+OWNER+'/'+REPO+'/actions/workflows/'+WORKFLOW+'/dispatches',token,{
         method:'POST',
         headers:{'Content-Type':'application/json'},
         body:JSON.stringify({ref:'main',inputs:{dry_run:'false'}})
       });
       if(r.status===401||r.status===403){
         try{sessionStorage.removeItem(TOKEN_KEY)}catch{}
         throw Error('GitHub 토큰 권한을 확인해 주세요. Actions Read and write 권한이 필요합니다.');
       }
       if(r.status!==204)throw Error('갱신 요청 실패 ('+r.status+')');
       pending={beforeRevision,dispatchedAt,runId:null};
       try{sessionStorage.setItem(PENDING_KEY,JSON.stringify(pending))}catch{}
     }
     await waitRun(token,pending);
     await waitProduction(pending.beforeRevision);
   }catch(e){
     console.error('manual-refresh',e);
     setState(e?.message||'수동 갱신 중 오류가 발생했습니다.','error');
     try{sessionStorage.removeItem(PENDING_KEY)}catch{}
     btn.disabled=false;
     btn.textContent='↻ 다시 시도';
   }
 }
 btn.addEventListener('click',()=>runManualRefresh(false));
 try{
   const p=JSON.parse(sessionStorage.getItem(PENDING_KEY)||'null');
   const token=sessionStorage.getItem(TOKEN_KEY)||'';
   if(p&&token&&Date.now()-Number(p.dispatchedAt||0)<40*60*1000){
     setTimeout(()=>runManualRefresh(true),400);
   }else if(p){
     sessionStorage.removeItem(PENDING_KEY);
   }
 }catch{}
})();
