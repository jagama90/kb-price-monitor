'use strict';
const http=require('http');
const fs=require('fs');
const path=require('path');
const ROOT=path.resolve(__dirname,'../dist');
const {chromium}=require('playwright-core');
const API='https://fin.land.naver.com/front-api/v1/complex/article/list';
let browser,page,primed=false;
const cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET,OPTIONS','Access-Control-Allow-Headers':'Content-Type'};
async function ensure(){
 if(browser)return;
 browser=await chromium.launch({channel:process.env.NAVER_BROWSER_CHANNEL||'chrome',headless:false});
 const ctx=await browser.newContext({locale:'ko-KR'});
 page=await ctx.newPage();
 await page.route('**/*',route=>{
  if(primed&&route.request().isNavigationRequest()&&route.request().frame()===page.mainFrame())return route.abort('aborted');
  return route.continue();
 });
}
async function resolveComplex(name){
 await ensure();primed=false;
 await page.goto('https://fin.land.naver.com/map?search='+encodeURIComponent(name),{waitUntil:'commit',timeout:25000});
 await page.waitForTimeout(1800);
 const found=await page.evaluate(n=>{
  const links=[...document.querySelectorAll('a[href*="/complexes/"]')].map(a=>({href:a.href,text:(a.textContent||'').trim()}));
  const exact=links.find(x=>x.text.includes(n))||links[0];
  const m=exact&&exact.href.match(/\/complexes\/(\d+)/);return m?m[1]:'';
 },name).catch(()=> '');
 if(!found)throw new Error('단지 검색 실패: '+name);
 return found;
}
async function prime(cid){primed=false;await page.goto('https://fin.land.naver.com/complexes/'+cid,{waitUntil:'commit',timeout:25000});primed=true}
function price(v){
 if(typeof v==='number')return v;
 const s=String(v||'').replace(/,/g,'');const m=s.match(/(\d+)억\s*(\d+)?/);if(m)return +m[1]*10000+(+(m[2]||0));
 const n=s.match(/\d+/);return n?+n[0]:null;
}
function walk(o,out=[]){if(Array.isArray(o))o.forEach(x=>walk(x,out));else if(o&&typeof o==='object'){if(o.articleNo||o.atclNo)out.push(o);Object.values(o).forEach(x=>walk(x,out))}return out}
async function query(cid,area,name){
 await ensure();if(name)cid=await resolveComplex(name);if(!primed)await prime(cid);
 const r=await page.evaluate(async a=>{const res=await fetch(a.api,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({complexNumber:a.cid,tradeTypes:['A1'],size:30,userChannelType:'MOBILE',articleSortType:'PRICE_ASC',lastInfo:[]})});return {status:res.status,text:await res.text()}},{api:API,cid});
 if(r.status!==200)throw new Error('Naver HTTP '+r.status);
 const data=JSON.parse(r.text),all=walk(data),near=all.filter(x=>{const a=Number(x.area1||x.spc1||x.supplyArea||x.articleArea||0);return !area||!a||Math.abs(a-area)<=2});
 const arr=near.map(x=>({x,p:price(x.dealOrWarrantPrc||x.price||x.priceText||x.formattedPrice)})).filter(v=>v.p!=null).sort((a,b)=>a.p-b.p);
 return {ok:true,complexNo:cid,area,listingCount:near.length,lowest:arr[0]?{priceManwon:arr[0].p,articleNo:arr[0].x.articleNo||arr[0].x.atclNo}:null};
}
http.createServer(async(req,res)=>{
 const u=new URL(req.url,'http://127.0.0.1');
 if(u.pathname==='/live-listing'){
  Object.entries(cors).forEach(([k,v])=>res.setHeader(k,v));res.setHeader('Content-Type','application/json');
  if(req.method==='OPTIONS'){res.statusCode=204;return res.end()}
  try{return res.end(JSON.stringify(await query(u.searchParams.get('complexNo')||'',Number(u.searchParams.get('area')||0),u.searchParams.get('name')||'')))}
  catch(e){res.statusCode=502;return res.end(JSON.stringify({ok:false,error:String(e.message||e)}))}
 }
 const rel=u.pathname==='/'?'index.html':decodeURIComponent(u.pathname.slice(1));
 const file=path.resolve(ROOT,rel);
 if(!file.startsWith(ROOT)||!fs.existsSync(file)||fs.statSync(file).isDirectory()){res.statusCode=404;return res.end('Not found')}
 const ext=path.extname(file);const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
 res.setHeader('Content-Type',types[ext]||'application/octet-stream');fs.createReadStream(file).pipe(res);
}).listen(17330,'127.0.0.1',()=>console.log('KB live monitor: http://127.0.0.1:17330'));
