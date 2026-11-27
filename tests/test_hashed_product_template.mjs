import test from'node:test';import assert from'node:assert/strict';import{canonicalProduct}from'../worker/canonical-product.mjs';
for (const prefix of ['assets/', '/assets/']) test(`canonical product strips fingerprinted legacy client: ${prefix}`,async()=>{
 const p={id:'p',slug:'food-test',name:'Food',brand:'Brand',format:'2 kg',offers:[],history:[]};
 const env={ASSETS:{fetch:async r=>{const path=new URL(r.url).pathname;if(path.startsWith('/data/canonical-products/'))return Response.json({[p.slug]:p});if(path==='/prodotto')return new Response('<html><head><title>Old</title><meta name="robots" content="noindex,follow"></head><body><main></main><script src="' + prefix + 'base.aaaaaaaaaaaa.js" defer></script><script src="' + prefix + 'product.bbbbbbbbbbbb.js?v=1" defer></script></body></html>');return new Response(null,{status:404})}}};
 const response=await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/food-test'),env),html=await response.text();assert(!html.includes('product.bbbbbbbbbbbb.js'));assert(html.includes('base.aaaaaaaaaaaa.js'));
});

