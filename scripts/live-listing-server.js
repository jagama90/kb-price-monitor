'use strict';
const http=require('http');
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
async function prime(cid){primed=false;await page.goto('https://fin.land.naver.com/complexes/'+cid,{waitUntil:'commit',timeout:25000});primed=true}
function price(v){
 if(typeof v==='number')return v;
 const s=String(v||'').replace(/,/g,'');const m=s.match(/(\d+)억\s*(\d+)?/);if(m)return +m[1]*10000+(+(m[2]||0));
 const n=s.match(/\d+/);return n?+n[0]:null;
}
function walk(o,out=[]){if(Array.isArray(o))o.forEach(x=>walk(x,out));else if(o&&typeof o==='object'){if(o.articleNo||o.atclNo)out.push(o);Object.values(o).forEach(x=>walk(x,out))}return out}
async function query(cid,area){
 await ensure();if(!primed)await prime(cid);
 const r=await page.evaluate(async a=>{const res=await fetch(a.api,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({complexNumber:a.cid,tradeTypes:['A1'],size:30,userChannelType:'MOBILE',articleSortType:'PRICE_ASC',lastInfo:[]})});return {status:res.status,text:await res.text()}},{api:API,cid});
 if(r.status!==200)throw new Error('Naver HTTP '+r.status);
 const data=JSON.parse(r.text),all=walk(data),near=all.filter(x=>{const a=Number(x.area1||x.spc1||x.supplyArea||x.articleArea||0);return !area||!a||Math.abs(a-area)<=2});
 const arr=near.map(x=>({x,p:price(x.dealOrWarrantPrc||x.price||x.priceText||x.formattedPrice)})).filter(v=>v.p!=null).sort((a,b)=>a.p-b.p);
 return {ok:true,complexNo:cid,area,listingCount:near.length,lowest:arr[0]?{priceManwon:arr[0].p,articleNo:arr[0].x.articleNo||arr[0].x.atclNo}:null};
}
http.createServer(async(req,res)=>{
 Object.entries(cors).forEach(([k,v])=>res.setHeader(k,v));res.setHeader('Content-Type','application/json');
 if(req.method==='OPTIONS'){res.statusCode=204;return res.end()}
 try{const u=new URL(req.url,'http://127.0.0.1');if(u.pathname!='/live-listing')throw new Error('not found');res.end(JSON.stringify(await query(u.searchParams.get('complexNo')||'9330',Number(u.searchParams.get('area')||0))))}
 catch(e){res.statusCode=502;res.end(JSON.stringify({ok:false,error:String(e.message||e)}))}
}).listen(17330,'127.0.0.1',()=>console.log('KB live listing helper: http://127.0.0.1:17330'));
