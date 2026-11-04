import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {ASSET_SECURITY_POLICY,reportSecurityHeaders} from '../worker/security-headers.mjs';
import {canonicalProduct} from '../worker/canonical-product.mjs';

function globalAssetPolicy(source){
 const lines=source.split(/\r?\n/),start=lines.findIndex(line=>line.trim()==='/*');
 assert.notEqual(start,-1,'the global asset policy block must exist');
 const entries=[];
 for(const line of lines.slice(start+1)){
  if(line.trim()&&!/^[ \t]/.test(line))break;
  const match=line.match(/^[ \t]+([\w-]+):[ \t]*(.+)$/);
  if(match)entries.push([match[1],match[2]]);
 }
 return Object.fromEntries(entries);
}
test('diagnostic reference exactly matches the existing global static asset policy',()=>{
 const source=fs.readFileSync(new URL('../site/_headers',import.meta.url),'utf8');
 assert.deepEqual(ASSET_SECURITY_POLICY,globalAssetPolicy(source));
});
test('fingerprinted asset cache blocks do not change the global diagnostic policy',()=>{
 const source=fs.readFileSync(new URL('../site/_headers',import.meta.url),'utf8');
 const built=source+'\n/assets/*\n  Cache-Control: public, max-age=31536000, immutable\n  X-Frame-Options: SAMEORIGIN\n';
 assert.deepEqual(ASSET_SECURITY_POLICY,globalAssetPolicy(built));
 assert(!Object.hasOwn(globalAssetPolicy(built),'Cache-Control'));
});
test('report-only emits fixed missing names without browser restrictions or user data',async()=>{
 const logs=[];const original=new Response('body',{headers:{'Set-Cookie':'private=session','X-Custom':'secret','Cache-Control':'no-store'}});
 const result=reportSecurityHeaders(original,{log:event=>logs.push(event)});
 assert.deepEqual(logs,[{event:'security_headers_report_only',missing_headers:Object.keys(ASSET_SECURITY_POLICY)}]);
 assert.equal(result.headers.get('X-O4Z-Security-Mode'),'report-only');
 for(const name of Object.keys(ASSET_SECURITY_POLICY))assert.equal(result.headers.get(name),null);
 assert.equal(result.headers.get('Set-Cookie'),'private=session');assert.equal(result.headers.get('X-Custom'),'secret');
 assert.equal(result.headers.get('Cache-Control'),'no-store');assert.equal(await result.text(),'body');
 assert(!JSON.stringify(logs).includes('private'));assert(!JSON.stringify(logs).includes('secret'));
});
test('existing policy is preserved exactly, including a stricter or different value',()=>{
 const logs=[];const original=new Response(null,{headers:{...ASSET_SECURITY_POLICY,'Strict-Transport-Security':'max-age=31536000; includeSubDomains','Content-Security-Policy':"default-src 'self'"}});
 const result=reportSecurityHeaders(original,{log:event=>logs.push(event)});
 assert.deepEqual(logs,[]);
 for(const [name,value] of original.headers)assert.equal(result.headers.get(name),value);
 assert.equal(result.headers.get('Content-Security-Policy'),"default-src 'self'");
});
test('immutable redirects and method metadata survive diagnostic wrapping',async()=>{
 const redirect=reportSecurityHeaders(Response.redirect('https://offerte4zampe.it/prodotto/new-product',301),{log:()=>{}});
 assert.equal(redirect.status,301);assert.equal(redirect.headers.get('Location'),'https://offerte4zampe.it/prodotto/new-product');
 const error=reportSecurityHeaders(new Response('method',{status:405,statusText:'Not Allowed',headers:{Allow:'GET, HEAD','Cache-Control':'no-store'}}),{log:()=>{}});
 assert.equal(error.status,405);assert.equal(error.statusText,'Not Allowed');assert.equal(error.headers.get('Allow'),'GET, HEAD');assert.equal(await error.text(),'method');
});
test('logging failure cannot break response delivery',async()=>{
 const result=reportSecurityHeaders(new Response('ok'),{log:()=>{throw Error('log unavailable')}});
 assert.equal(await result.text(),'ok');
});

const product={id:'p-fixture',slug:'fixture-product',name:'Fixture',brand:'Brand',format:'1 kg',offers:[],history:[]};
const template='<html><head><title>Old</title><meta name="description" content="Old"><meta name="robots" content="noindex,follow"><link rel="canonical" href="https://offerte4zampe.it/prodotto"></head><body><a class="skip" href="#main">Vai al contenuto</a><main id="main">Old</main></body></html>';
function fixture(p=product){return {ASSETS:{fetch:async request=>{
 const path=new URL(request.url).pathname;
 if(path.startsWith('/data/canonical-products/'))return Response.json({[p.slug]:p});
 if(path==='/data/shipping-rules.json')return Response.json({merchants:{}});
 if(path==='/prodotto')return new Response(template,{headers:{'Content-Type':'text/html'}});
 return new Response('missing',{status:404});
}}};}
test('real canonical handler reports 200/400/404/405/301 and keeps query skip links on current page',async()=>{
 const logs=[],original=console.info;console.info=event=>logs.push(event);
 try{
  const base='https://offerte4zampe.it/prodotto/fixture-product';
  const cases=[
   [new Request(base),fixture(),200],
   [new Request(base+'?quantity=0'),fixture(),400],
   [new Request('https://offerte4zampe.it/prodotto/missing'),fixture(),404],
   [new Request(base,{method:'POST'}),fixture(),405],
   [new Request(base),fixture({...product,redirect_slug:'fixture-new'}),301],
  ];
  for(const [request,env,status] of cases){
   const response=await canonicalProduct(request,env);assert.equal(response.status,status);
   assert.equal(response.headers.get('X-O4Z-Security-Mode'),'report-only');
   for(const name of Object.keys(ASSET_SECURITY_POLICY))assert.equal(response.headers.get(name),null);
   if(status===405)assert.equal(response.headers.get('Allow'),'GET, HEAD');
   if(status===301)assert.equal(response.headers.get('Location'),'https://offerte4zampe.it/prodotto/fixture-new');
   if(status===200){const html=await response.text();assert(html.includes('href="/prodotto/fixture-product#main"'));assert.equal(response.headers.get('Cache-Control'),'no-store');}
  }
  const response=await canonicalProduct(new Request(base+'?quantity=2&territory=special&note=%22test%22'),fixture());
  const html=await response.text();const encoded=html.match(/class="skip" href="([^"]+)"/)[1];
  const resolved=new URL(encoded.replaceAll('&amp;','&'),new URL('/',base));
  assert.equal(resolved.href,base+'?quantity=2&territory=special&note=%22test%22#main');
  assert.equal(response.headers.get('X-Robots-Tag'),'noindex, follow');
  assert(html.includes('rel="canonical" href="'+base+'"'));
  const head=await canonicalProduct(new Request(base,{method:'HEAD'}),fixture());assert.equal(head.body,null);
  assert.equal(logs.length,7);
  for(const event of logs)assert.deepEqual(Object.keys(event),['event','missing_headers']);
  assert(!JSON.stringify(logs).includes('note'));assert(!JSON.stringify(logs).includes('fixture'));
 }finally{console.info=original;}
});
