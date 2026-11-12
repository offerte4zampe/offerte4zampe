// Render actual canonical Worker pages; no external merchants or production requests.
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import worker from '../worker/index.mjs';
const root=path.resolve(import.meta.dirname,'../site');
const selection=JSON.parse(await fs.readFile(path.resolve(import.meta.dirname,'../automation/amazon-sitestripe-selection.json')));
const output=path.resolve('browser-reports/sitestripe');await fs.mkdir(output,{recursive:true});
const env={PRICE_TRACKING_ENABLED:'false',AMAZON_LINKS_ENABLED:'true',ASSETS:{fetch:async req=>{
 let name=decodeURIComponent(new URL(req.url).pathname);if(name==='/')name='/index.html';if(name==='/prodotto')name='/prodotto.html';
 let file=path.resolve(root,'.'+name);if(!path.extname(file))file+='.html';if(!file.startsWith(root+path.sep))return new Response(null,{status:403});
 try{const bytes=await fs.readFile(file);const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.webp':'image/webp'};return new Response(req.method==='HEAD'?null:bytes,{headers:{'Content-Type':types[path.extname(file)]||'application/octet-stream'}})}catch{return new Response(null,{status:404})}
}}};
const server=http.createServer(async(req,res)=>{try{const r=await worker.fetch(new Request('http://127.0.0.1:'+server.address().port+req.url),env,{waitUntil(){}});res.writeHead(r.status,Object.fromEntries(r.headers));res.end(Buffer.from(await r.arrayBuffer()))}catch(e){res.writeHead(500);res.end(String(e))}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const origin='http://127.0.0.1:'+server.address().port;
let browser;const results=[];
try{
 const driver=path.join(process.env.PUPPETEER_ROOT,'node_modules/puppeteer-core');const pkg=JSON.parse(await fs.readFile(path.join(driver,'package.json')));const {default:puppeteer}=await import(pathToFileURL(path.join(driver,pkg.main)));
 browser=await puppeteer.launch({headless:true,executablePath:process.env.CHROME_PATH,args:['--no-sandbox','--disable-dev-shm-usage']});
 for(const viewport of [{width:393,height:852,isMobile:true},{width:1365,height:900}]){
  const page=await browser.newPage();await page.setViewport(viewport);const errors=[];page.on('pageerror',e=>errors.push(String(e)));await page.setRequestInterception(true);page.on('request',r=>r.url().startsWith(origin)?r.continue():r.abort());
  for(const product of selection.products){
   const route=new URL(product.url).pathname;const response=await page.goto(origin+route,{waitUntil:'networkidle0'});assert.equal(response.status(),200,route);
   const actual=await page.$$eval('[data-amazon-verified] a',nodes=>nodes.map(a=>({url:a.href,rel:a.rel,label:a.textContent,tracking:a.dataset.amazonAffiliate})));
   if(product.publication_ready){assert.equal(actual.length,1);assert.equal(actual[0].url,product.sitestripe_url);assert.match(actual[0].rel,/sponsored/);assert.equal(actual[0].tracking,'verified');assert.match(actual[0].label,/Verifica prezzo/);
    assert(await page.$eval('[data-amazon-verified]',e=>e.textContent.includes('In qualità di Affiliato Amazon')));
    assert.equal(await page.$eval('main',e=>!!e.querySelector('[data-history-offer]')),false);
    await page.screenshot({path:path.join(output,product.selection_number+'-'+viewport.width+'.png'),fullPage:true});
   }else assert.equal(actual.length,0,'Excluded selection '+product.selection_number);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);assert(overflow<=1,'Overflow '+route);
   results.push({number:product.selection_number,width:viewport.width,status:response.status(),amazon:actual.length,overflow});
  }
  assert.deepEqual(errors,[]);await page.close();
 }
 await fs.writeFile(path.join(output,'results.json'),JSON.stringify({scope:'local actual Worker, no external merchant navigation',results},null,2));console.log(JSON.stringify({pages:results.length,approved:selection.products.filter(p=>p.publication_ready).length,passed:true}));
}finally{await browser?.close();await new Promise(r=>server.close(r))}
