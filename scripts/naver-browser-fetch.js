const readline=require('readline');
const {chromium}=require('playwright-core');
const API='https://fin.land.naver.com/front-api/v1/complex/article/list';
let browser,page,primed=false;
const send=o=>process.stdout.write(JSON.stringify(o)+'\n');
async function start(){
  if(browser)return;
  browser=await chromium.launch({channel:process.env.NAVER_BROWSER_CHANNEL||'chrome',headless:false});
  page=await (await browser.newContext({locale:'ko-KR'})).newPage();
}
async function fetchPages(req){
  await start();
  if(!primed){
    await page.goto('https://fin.land.naver.com/complexes/'+req.complexNo,{waitUntil:'commit',timeout:25000});
    primed=true;
  }
  const pages=[]; let lastInfo=[],seed='';
  for(let i=0;i<Math.max(1,req.maxPages||1);i++){
    const out=await page.evaluate(async a=>{
      const res=await fetch(a.api,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',
        body:JSON.stringify({complexNumber:String(a.complexNo),tradeTypes:['A1'],size:30,userChannelType:'MOBILE',
          articleSortType:'PRICE_ASC',lastInfo:a.lastInfo||[],...(a.seed?{seed:a.seed}:{})})});
      return {status:res.status,text:await res.text()};
    },{api:API,complexNo:req.complexNo,lastInfo,seed});
    if(out.status===429)return {id:req.id,blocked:true,error:'TOO_MANY_REQUESTS'};
    if(out.status!==200)return {id:req.id,error:'HTTP '+out.status,pages};
    pages.push(out.text);
    let j;try{j=JSON.parse(out.text)}catch{break}
    const result=j&&j.result;if(!result||!result.hasNextPage)break;
    lastInfo=result.lastInfo||[];seed=result.seed||'';
    await page.waitForTimeout(500);
  }
  return {id:req.id,complexNo:req.complexNo,pages};
}
const rl=readline.createInterface({input:process.stdin});
let q=Promise.resolve();
rl.on('line',line=>{if(!line.trim())return;const req=JSON.parse(line);q=q.then(async()=>send(await fetchPages(req))).catch(e=>send({id:req.id,error:String(e)}));});
rl.on('close',async()=>{try{await q}catch{};try{if(browser)await browser.close()}catch{}});
start().then(()=>send({ready:true})).catch(e=>send({ready:false,error:String(e)}));