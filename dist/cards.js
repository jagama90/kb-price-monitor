'use strict';
function togglePanel(id,open){const el=document.getElementById(id);if(!el)return;el.hidden=!open;if(open)setTimeout(()=>el.scrollIntoView({behavior:'smooth',block:'start'}),20)}
document.addEventListener('DOMContentLoaded',()=>{
 const rate=document.getElementById('rateCard'),m2=document.getElementById('m2Card'),fed=document.getElementById('fedCard');
 if(rate)rate.onclick=()=>{togglePanel('rateDetail',true);if(typeof renderRateDetail==='function')renderRateDetail()};
 if(m2)m2.onclick=()=>{togglePanel('macroDetail',true);if(typeof showMacro==='function')showMacro('m2')};
 if(fed)fed.onclick=()=>{togglePanel('macroDetail',true);if(typeof showMacro==='function')showMacro('fed')};
 const cr=document.getElementById('closeRate'),cm=document.getElementById('closeMacro');if(cr)cr.onclick=()=>togglePanel('rateDetail',false);if(cm)cm.onclick=()=>togglePanel('macroDetail',false);
});