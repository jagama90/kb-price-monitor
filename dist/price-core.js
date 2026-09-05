(function (root) {
  'use strict';
  const positive = n => typeof n === 'number' && Number.isFinite(n) && n > 0;
  function validateSnapshot(data) {
    if (data.schema_version !== 2 || !Array.isArray(data.items)) throw new Error('평형별 자료 형식이 아닙니다.');
    const ids = new Set();
    for (const row of data.items) {
      const id = `${row.complex_id}/${row.area_id}`;
      if (!Number.isInteger(row.complex_id) || row.complex_id <= 0 || !Number.isInteger(row.area_id) || row.area_id <= 0 || ids.has(id)) throw new Error('평형 식별자가 올바르지 않습니다.');
      if (!positive(row.supply_pyeong) || !positive(row.supply_m2)) throw new Error('공급면적이 누락되었습니다.');
      if (row.general_price_manwon !== null && (!positive(row.general_price_manwon) || row.price_status !== 'kb_general')) throw new Error('일반가가 아닌 가격이 포함되었습니다.');
      ids.add(id);
    }
    if (data.items.length !== data.type_count) throw new Error('평형 건수가 일치하지 않습니다.');
    if (data.complex_count !== new Set(data.items.map(r=>r.complex_id)).size ||
        data.priced_count !== data.items.filter(r=>r.general_price_manwon!==null).length) throw new Error('집계 건수가 일치하지 않습니다.');
    if (!Array.isArray(data.errors) || data.errors.length || data.successful_complex_count !== data.target_complex_count ||
        !Array.isArray(data.empty_complex_ids) || data.complex_count+data.empty_complex_ids.length !== data.successful_complex_count) throw new Error('수집이 완료되지 않은 자료입니다.');
    return data;
  }
  function matches(row, f) {
    if (f.districts && !f.districts.has(row.district)) return false;
    if (f.q && !`${row.name} ${row.district} ${row.dong}`.toLowerCase().includes(f.q)) return false;
    // Compare the real KB-reported supply area; never intersect an invented interval.
    if (f.areaMin !== null && row.supply_pyeong < f.areaMin) return false;
    if (f.areaMax !== null && row.supply_pyeong > f.areaMax) return false;
    if ((row.households || 0) < f.households) return false;
    return !f.budgetOnly || (row.price_status === 'kb_general' && positive(row.general_price_manwon) && row.general_price_manwon <= f.budget);
  }
  function sortValue(row, key, budget) {
    const values = {name:row.name,district:`${row.district} ${row.dong}`,households:row.households,
      area:row.supply_pyeong,exclusive:row.exclusive_pyeong,price:row.general_price_manwon,
      collected:row.collected_at,budget:row.general_price_manwon === null ? null : row.general_price_manwon-budget};
    return values[key] ?? null;
  }
  function compareRows(a, b, sort, budget) {
    const av=sortValue(a,sort.key,budget),bv=sortValue(b,sort.key,budget);
    // Missing prices/areas always stay at the bottom, including descending order.
    if (av === null && bv !== null) return 1;
    if (bv === null && av !== null) return -1;
    const cmp=av === null ? 0 : typeof av === 'string' ? av.localeCompare(bv,'ko') : av-bv;
    return (sort.direction === 'asc' ? cmp : -cmp) || a.complex_id-b.complex_id || a.area_id-b.area_id;
  }
  function csvCell(value) {
    let s=String(value ?? '');
    if (/^[=+@\-\t\r]/.test(s)) s="'"+s;
    return '"'+s.replace(/"/g,'""')+'"';
  }
  function toCSV(rows) {
    const header=['단지명','자치구','동','단지총세대수','평형세대수','평형타입','공급평','전용평','공급㎡','전용㎡','KB일반가만원','시세상태','시세기준일(미제공시공란)','조회시각','단지ID','평형ID','KB링크'];
    return [header,...rows.map(r=>[r.name,r.district,r.dong,r.households,r.type_households,r.type_label,
      r.supply_pyeong,r.exclusive_pyeong,r.supply_m2,r.exclusive_m2,r.general_price_manwon,
      r.price_status,r.price_date,r.collected_at,r.complex_id,r.area_id,`https://kbland.kr/c/${r.complex_id}`])]
      .map(cells=>cells.map(csvCell).join(',')).join('\r\n');
  }
  // Bound the entire group's span, not adjacent gaps (prevents chain merging).
  function groupSimilar(rows, tolerance=2) {
    const groups=[];
    for (const row of [...rows].sort((a,b)=>a.complex_id-b.complex_id || a.supply_pyeong-b.supply_pyeong || a.area_id-b.area_id)) {
      let g=groups[groups.length-1];
      const ex=positive(row.exclusive_pyeong);
      if (!g || g.complex_id!==row.complex_id || !ex || !g.hasExclusive ||
          row.supply_pyeong-g.supply_pyeong>tolerance+1e-8 ||
          Math.max(g.exMax,row.exclusive_pyeong)-Math.min(g.exMin,row.exclusive_pyeong)>tolerance+1e-8) {
        g={...row,members:[],hasExclusive:ex,exMin:row.exclusive_pyeong,exMax:row.exclusive_pyeong};groups.push(g);
      }
      g.members.push(row);
      g.exMin=Math.min(g.exMin,row.exclusive_pyeong);g.exMax=Math.max(g.exMax,row.exclusive_pyeong);
      g.exclusive_pyeong=g.exMin;
      if (row.general_price_manwon!==null) g.general_price_manwon=g.general_price_manwon===null?row.general_price_manwon:Math.min(g.general_price_manwon,row.general_price_manwon);
    }
    return groups;
  }
  const api={validateSnapshot,matches,compareRows,toCSV,groupSimilar};
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  else root.KBPriceCore=api;
})(globalThis);
