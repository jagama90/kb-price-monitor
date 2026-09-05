'use strict';
const $=s=>document.querySelector(s),core=globalThis.KBPriceCore,pageSize=50;
let ready=false,rows=[],filtered=[],page=1,districts=[],selectedDistricts=new Set(),sortState={key:'price',direction:'asc'};
let displayed=[],expanded=new Set();
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=n=>n===null||n===undefined?'—':Number(n).toLocaleString('ko-KR',{maximumFractionDigits:2});
function won(n) {
  if (n===null || n===undefined) return '—';
  const e=Math.floor(n/10000),m=n-e*10000;
  return `${e?e+'억':''}${m?' '+num(m)+'만':''} 원`.trim();
}
const date=s=>s?new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric'}).format(new Date(s)):'—';
function filters() {
  const bound=id=>$(id).value.trim()===''?null:Number($(id).value);
  return {q:$('#searchInput').value.trim().toLowerCase(),districts:selectedDistricts,
    areaMin:bound('#areaMin'),areaMax:bound('#areaMax'),households:Number($('#householdFilter').value),
    budget:Number($('#budgetInput').value)*10000,budgetOnly:$('#budgetToggle').getAttribute('aria-pressed')==='true'};
}
function validFilters(f) {
  if ([f.areaMin,f.areaMax].some(v=>v!==null&&(!Number.isFinite(v)||v<=0))) return '평수는 0보다 큰 숫자로 입력해 주세요.';
  if (f.areaMin!==null&&f.areaMax!==null&&f.areaMin>f.areaMax) return '최소 평수가 최대 평수보다 큽니다.';
  if (!Number.isFinite(f.budget)||f.budget<=0) return '예산은 0보다 큰 숫자로 입력해 주세요.';
  return '';
}
function apply() {
  if (!ready) return;
  const f=filters(),error=validFilters(f);
  $('#filterError').textContent=error;$('#filterError').hidden=!error;
  filtered=error?[]:rows.filter(r=>core.matches(r,f)).sort((a,b)=>core.compareRows(a,b,sortState,f.budget));
  displayed=($('#groupToggle').checked?core.groupSimilar(filtered,Number($('#groupTolerance').value)):filtered).sort((a,b)=>core.compareRows(a,b,sortState,f.budget));
  expanded.clear();
  page=1;render();
}
function render() {
  const f=filters(),pages=Math.max(1,Math.ceil(displayed.length/pageSize));page=Math.min(page,pages);
  const out=displayed.slice((page-1)*pageSize,page*pageSize);
  const rowHTML=r=>{
    const p=r.general_price_manwon,ok=p!==null&&p<=f.budget;
    const state=p===null?(r.price_status==='ai_excluded'?'AI시세 제외':'일반가 없음'):ok?'예산 이하':'예산 초과';
    return `<tr><td>${escapeHTML(r.name)}<small>${escapeHTML(r.type_label)}평형</small></td>
      <td>${escapeHTML(r.district)}<small>${escapeHTML(r.dong)}</small></td>
      <td><strong>${num(r.households)}세대</strong><small>이 평형 ${num(r.type_households)}세대</small></td>
      <td><strong>${num(r.supply_pyeong)}평</strong><small>${num(r.supply_m2)}㎡</small></td>
      <td>${num(r.exclusive_pyeong)}평<small>${num(r.exclusive_m2)}㎡</small></td>
      <td><strong>${won(p)}</strong>${p===null?`<small>${state}</small>`:''}</td>
      <td><span class="chip ${ok?'ok':'over'}">${state}</span></td>
      <td title="${escapeHTML(r.collected_at)}">${date(r.collected_at)}</td>
      <td><a class="link" href="https://kbland.kr/c/${r.complex_id}" target="_blank" rel="noopener">KB에서 보기 ↗</a><small>KB에서 ${escapeHTML(r.type_label)}평형 선택</small></td></tr>`;
  };
  const range=(members,key,format=num)=>{
    const values=members.map(r=>r[key]).filter(v=>typeof v==='number'&&Number.isFinite(v));
    if (!values.length) return '—';
    const lo=Math.min(...values),hi=Math.max(...values);
    return lo===hi?format(lo):`${format(lo)} ~ ${format(hi)}`;
  };
  $('#priceBody').innerHTML=out.map(r=>{
    const m=r.members;
    if (!m || m.length===1) return rowHTML(m?m[0]:r);
    const key=`${r.complex_id}/${r.area_id}`,open=expanded.has(key),priced=m.filter(x=>x.general_price_manwon!==null),under=priced.filter(x=>x.general_price_manwon<=f.budget).length;
    const state=under===m.length?'모두 예산 이하':under?'일부 예산 이하':priced.length===m.length?'모두 예산 초과':priced.length?'일부 일반가 없음':'일반가 없음';
    return `<tr class="group-row"><td><button class="group-expand" data-group="${key}" aria-expanded="${open}" aria-label="${escapeHTML(r.name)} ${m.length}개 타입 ${open?'접기':'펼치기'}">${open?'▾':'▸'} ${escapeHTML(r.name)}<small>${range(m,'supply_pyeong')}평 · ${m.length}개 타입</small></button></td>
      <td>${escapeHTML(r.district)}<small>${escapeHTML(r.dong)}</small></td>
      <td><strong>${num(r.households)}세대</strong><small>묶음 ${num(m.reduce((n,x)=>n+(x.type_households||0),0))}세대</small></td>
      <td><strong>${range(m,'supply_pyeong')}평</strong><small>${range(m,'supply_m2')}㎡</small></td>
      <td>${range(m,'exclusive_pyeong')}평<small>${range(m,'exclusive_m2')}㎡</small></td>
      <td><strong>${range(m,'general_price_manwon',won)}</strong><small>${priced.length<m.length?`일반가 없는 타입 ${m.length-priced.length}개`:'타입별 일반가'}</small></td>
      <td><span class="chip ${under===m.length?'ok':'over'}">${state}</span></td>
      <td>${[...new Set(m.map(x=>date(x.collected_at)))].join(' · ')}</td>
      <td><button class="group-expand link" data-group="${key}" aria-expanded="${open}">${open?'타입 접기':'타입별 보기'} ${open?'▴':'▾'}</button></td></tr>`+
      (open?m.map(x=>rowHTML(x).replace('<tr>','<tr class="type-detail">')).join(''):'');
  }).join('');
  $('#emptyState').hidden=out.length>0;
  $('#resultCount').textContent=`${new Set(filtered.map(r=>r.complex_id)).size.toLocaleString()}개 단지 · ${filtered.length.toLocaleString()}개 평형`;
  if ($('#groupToggle').checked) $('#resultCount').textContent+=` → ${displayed.length.toLocaleString()}개 묶음`;
  $('#pageInfo').textContent=`${page} / ${pages.toLocaleString()}`;
  $('#prevPage').disabled=page<=1;$('#nextPage').disabled=page>=pages;
  $('#exportBtn').disabled=!!validFilters(f)||!filtered.length;
  document.querySelectorAll('.sort-btn').forEach(btn=>{
    const active=btn.dataset.sort===sortState.key;
    btn.classList.toggle('active',active);
    btn.querySelector('i').textContent=active?(sortState.direction==='asc'?'↑':'↓'):'↕';
    btn.closest('th').setAttribute('aria-sort',active?(sortState.direction==='asc'?'ascending':'descending'):'none');
  });
}
function updateDistricts() {
  const all=$('#districtMenu [data-all]');
  all.checked=selectedDistricts.size===districts.length;all.indeterminate=selectedDistricts.size>0&&!all.checked;
  $('#districtTrigger span').textContent=all.checked?'전체 자치구':selectedDistricts.size===0?'자치구 선택':selectedDistricts.size<=2?[...selectedDistricts].join(', '):`${selectedDistricts.size}개 자치구 선택`;
}
function populate(meta) {
  districts=meta.districts||[...new Set(rows.map(r=>r.district))].sort((a,b)=>a.localeCompare(b,'ko'));
  selectedDistricts=new Set(districts);
  const menu=$('#districtMenu');
  menu.innerHTML='<label class="district-all"><input type="checkbox" data-all checked> 전체 선택</label>'+districts.map(d=>`<label><input type="checkbox" value="${escapeHTML(d)}" checked> ${escapeHTML(d)}</label>`).join('');
  menu.addEventListener('change',e=>{
    if (e.target.hasAttribute('data-all')) {
      selectedDistricts=e.target.checked?new Set(districts):new Set();
      menu.querySelectorAll('input:not([data-all])').forEach(input=>input.checked=e.target.checked);
    } else e.target.checked?selectedDistricts.add(e.target.value):selectedDistricts.delete(e.target.value);
    updateDistricts();apply();
  });
}
function stats(meta) {
  $('#countStat').textContent=num(meta.complex_count);
  $('#underStat').textContent=num(rows.filter(r=>r.general_price_manwon!==null&&r.general_price_manwon<=150000).length);
  $('#avgStat').textContent=num(meta.priced_count);
  $('#minStat').textContent=date(meta.collected_at);$('#minName').textContent='한국시간 · 조회 완료';
  $('#coverageNote').textContent=`서울 ${meta.district_count}개 구 · ${num(meta.successful_complex_count)}/${num(meta.target_complex_count)}개 단지 조회 · 평형 자료 없음 ${num(meta.empty_complex_ids.length)}개 단지. 단지 목록 기준 ${date(meta.catalog_collected_at)}.`;
}
['searchInput','areaMin','areaMax','householdFilter','budgetInput'].forEach(id=>$('#'+id).addEventListener(id==='householdFilter'?'change':'input',apply));
$('#districtTrigger').onclick=()=>{const open=$('#districtMenu').hidden;$('#districtMenu').hidden=!open;$('#districtTrigger').setAttribute('aria-expanded',String(open));};
function closeDistricts() {$('#districtMenu').hidden=true;$('#districtTrigger').setAttribute('aria-expanded','false');}
document.addEventListener('click',e=>{if(!$('#districtFilter').contains(e.target))closeDistricts();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('#districtMenu').hidden){closeDistricts();$('#districtTrigger').focus();}});
document.querySelectorAll('.sort-btn').forEach(btn=>btn.onclick=()=>{const key=btn.dataset.sort;sortState=sortState.key===key?{key,direction:sortState.direction==='asc'?'desc':'asc'}:{key,direction:['price','households'].includes(key)?'desc':'asc'};apply();});
$('#budgetToggle').onclick=e=>{e.currentTarget.setAttribute('aria-pressed',String(e.currentTarget.getAttribute('aria-pressed')!=='true'));apply();};
function changePage(delta) {page+=delta;render();document.querySelector('.table-head').scrollIntoView({behavior:'smooth',block:'start'});}
$('#prevPage').onclick=()=>{if(page>1)changePage(-1);};$('#nextPage').onclick=()=>{if(page*pageSize<displayed.length)changePage(1);};
$('#groupToggle').onchange=()=>{$('#groupTolerance').disabled=!$('#groupToggle').checked;apply();};
$('#groupTolerance').onchange=apply;
$('#priceBody').addEventListener('click',e=>{const btn=e.target.closest('[data-group]');if(!btn)return;const key=btn.dataset.group;expanded.has(key)?expanded.delete(key):expanded.add(key);render();document.querySelector(`[data-group="${key}"]`).focus();});
$('#exportBtn').onclick=()=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob(['\uFEFF'+core.toCSV(filtered)],{type:'text/csv;charset=utf-8'}));a.href=url;a.download='서울_KB_평형별시세.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
async function fetchSupabase(config) {
  const headers={apikey:config.supabaseAnonKey,Authorization:`Bearer ${config.supabaseAnonKey}`};
  const latest=await fetch(`${config.supabaseUrl}/rest/v1/kb_collections?select=*&status=eq.published&order=collected_at.desc&limit=1`,{headers,cache:'no-store'});
  if(!latest.ok) throw new Error('수집 메타데이터 조회 실패');
  const collections=await latest.json();
  if(!collections.length) throw new Error('게시된 수집 자료 없음');
  const items=[];
  for(let offset=0;;offset+=1000) {
    const response=await fetch(`${config.supabaseUrl}/rest/v1/kb_current_prices?select=*&order=district.asc,name.asc,supply_pyeong.asc&offset=${offset}&limit=1000`,{headers,cache:'no-store'});
    if(!response.ok) throw new Error('평형별 시세 조회 실패');
    const batch=await response.json();items.push(...batch);
    if(batch.length<1000) break;
  }
  const c=collections[0];
  return {schema_version:2,source:'KB부동산 mpriByType',scope:c.scope,
    collected_at:c.collected_at,catalog_collected_at:c.catalog_collected_at,
    target_complex_count:c.target_complex_count,successful_complex_count:c.successful_complex_count,
    complex_count:new Set(items.map(r=>r.complex_id)).size,type_count:items.length,
    priced_count:items.filter(r=>r.general_price_manwon!==null).length,
    district_count:new Set(items.map(r=>r.district)).size,
    districts:[...new Set(items.map(r=>r.district))].sort((a,b)=>a.localeCompare(b,'ko')),
    empty_complex_ids:Array(c.empty_complex_count||0).fill(null),errors:[],items};
}
function loadData() {
  const config=globalThis.KB_PRICE_CONFIG;
  if(config && config.supabaseAnonKey && !config.supabaseAnonKey.startsWith('REPLACE_')) return fetchSupabase(config);
  return fetch('seoul_types.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('조회 실패');return r.json();});
}
loadData().then(core.validateSnapshot).then(data=>{rows=data.items;populate(data);stats(data);ready=true;apply();}).catch(()=>{
  $('#resultCount').textContent='평형별 자료를 불러오지 못했습니다';
  $('#filterError').hidden=false;$('#filterError').textContent='자료를 다시 확인해 주세요. 단지 최저가로 대신 표시하지 않습니다.';
  $('#exportBtn').disabled=true;
});
