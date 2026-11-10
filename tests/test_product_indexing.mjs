import test from'node:test';import assert from'node:assert/strict';import{view,canonicalProduct,observedDays}from'../worker/canonical-product.mjs';
const now=Date.parse('2026-10-30T12:00:00Z'),offer={id:'bauzaar:1',title:'Food',merchant:'A',merchant_id:'bauzaar',available:true,price:12,weight_kg:2,quantity:{verified:true},checked_at:'2026-10-30T11:00:00Z',url:'https://shop.test/a'},p={id:'p-1',slug:'food-test',name:'Food',brand:'Brand',format:'2 kg',offers:[offer],history:[],indexable:false};
const history=Array.from({length:30},(_,i)=>({day:new Date(now-i*86400000).toISOString().slice(0,10),low:10,high:12,sum:11,count:1}));
function env(product,local=false,priceTracking=false){return{PRICE_TRACKING_ENABLED:priceTracking?'true':'false',ASSETS:{fetch:async r=>{const path=new URL(r.url).pathname;if(path.startsWith('/data/canonical-products/'))return Response.json({[product.slug]:product});if(path.startsWith('/img/p/'))return new Response(null,{status:local?200:404});if(path==='/prodotto')return new Response('<html><head><title>Old</title><meta name="robots" content="noindex,follow"><meta name="description" content="Old"><meta property="og:type" content="website"><meta property="og:image" content="/assets/social-home.png"></head><body><main></main></body></html>');return new Response(null,{status:404})}}}}
test('indexing requires distinct comparable shops or thirty actual observed dates',()=>{
 assert.equal(view(p,null,now).indexable,false);assert.equal(view({...p,history},null,now).indexable,true);assert.equal(view({...p,history:history.slice(0,29)},null,now).indexable,false);
 assert.equal(view({...p,offers:[offer,{...offer,id:'a:2'}]},null,now).indexable,false);
 assert.equal(view({...p,offers:[offer,{...offer,id:'b:1',merchant_id:'b'}]},null,now).indexable,true);
 assert.equal(observedDays([...history,...history],now),30);assert.equal(observedDays([{...history[0],day:'2026-02-30'}],now),0);
});
test('Product schema only on indexable canonical views; prices match visible offers',async()=>{
 for(const [product,expected]of [[p,false],[{...p,history,indexable:true},true]]){const response=await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+p.slug),env(product),now),html=await response.text();assert.equal(html.includes('"@type":"Product"'),expected);assert.equal(response.headers.get('X-Robots-Tag'),expected?'index, follow':'noindex, follow');if(expected){assert(html.includes('"lowPrice":12'));assert(html.includes('12,00'));}}
 const response=await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+p.slug+'?quantity=2'),env({...p,history,indexable:true}),now);assert(!(await response.text()).includes('"@type":"Product"'));
});
test('local og image is used only for a real local asset on an indexable page',async()=>{
 const product={...p,history,indexable:true,image_local:'/img/p/'+'a'.repeat(24)+'-400.webp'};
 for(const exists of [false,true]){const response=await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+p.slug),env(product,exists),now);const html=await response.text();assert.equal(html.includes('content="https://offerte4zampe.it/img/p/'),exists);assert(html.includes('property="og:type" content="product"'));}
});
