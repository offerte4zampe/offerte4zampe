import test from 'node:test';import assert from 'node:assert/strict';
import {canonicalProduct,view,content,slugForOffer,historySummary} from '../worker/canonical-product.mjs';
import worker from '../worker/index.mjs';
const now=Date.parse('2026-10-28T12:00:00Z');
const a={id:'a:1',merchant_id:'a',merchant:'Shop A',title:'Brand Adult 2 kg',price:20,available:true,gtin:'4006381333931',weight_kg:2,shipping_weight_kg:2,checked_at:'2026-10-28T11:00:00Z',url:'https://shop.test/a',quantity:{verified:true},unit_price:10,unit_price_unit:'kg'};
const b={...a,id:'b:1',merchant_id:'b',merchant:'Shop B',price:18,url:'https://shop.test/b'};
const product={id:'p-00000000000000000001',slug:'brand-adult-2-kg-4006381333931',name:'Brand Adult 2 kg',brand:'Brand',format:'2 kg',gtin:'4006381333931',image:'https://images.test/food.jpg',indexable:true,offers:[a,b],history:[]};
const rules={checked_at:'2026-10-28',merchants:{a:{fee:1},b:{fee:8}}};
const template='<html><head><title>Old</title><meta name="description" content="Old"><meta name="robots" content="noindex,follow"><link rel="canonical" href="https://offerte4zampe.it/prodotto"></head><body><main id="main">Old</main><script src="assets/product.js?v=1" defer></script></body></html>';
function env(p=product){return {ASSETS:{fetch:async req=>{const path=new URL(req.url).pathname;if(path.startsWith('/data/canonical-products/'))return Response.json({[p.slug]:p});if(path.startsWith('/data/canonical-routes/'))return Response.json({'a:1':p.slug});if(path==='/data/shipping-rules.json')return Response.json(rules);if(path==='/prodotto')return new Response(template,{headers:{'Content-Type':'text/html'}});return new Response('missing',{status:404})}}}}
test('canonical HTML contains actual prices, totals and Product schema without client rendering',async()=>{
 const r=await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+product.slug),env(),now);const html=await r.text();assert.equal(r.status,200);
 assert(html.includes('Shop A'));assert(html.includes('Shop B'));assert(html.includes('21,00'));assert(html.includes('26,00'));assert(html.includes('AggregateOffer'));assert(html.includes('index,follow'));assert(!html.includes('assets/product.js'));assert(html.includes('<base href="/">'));
 assert(html.indexOf('Shop A')<html.indexOf('Shop B'),'total includes shipping, not just product price');
});
test('unknown shipping never becomes zero or wins a total badge',()=>{const v=view(product,{checked_at:'2026-10-28',merchants:{a:{fee:1}}},now);assert.equal(v.quotes.get('b:1').total,undefined);assert.equal(v.rows[0].id,'a:1');assert.equal(v.best,21)});
test('single-store page describes an offer, never claims a multi-shop comparison',()=>{
 const p={...product,offers:[a],indexable:false};const v=view(p,rules,now),c=content(p,v);assert(c.body.includes('non è un confronto tra negozi'));assert.equal(v.indexable,false);
});
test('expired observations disappear from current offers and structured prices',()=>{
 const p={...product,offers:[{...a,checked_at:'2026-10-01'}]};const c=content(p,view(p,rules,now));assert(!c.schema.offers);assert(!c.body.includes('20,00'));
});
test('legacy offer identifiers redirect to the canonical product and unknown slugs return 404',async()=>{
 const e=env();assert.equal(await slugForOffer(e,'https://offerte4zampe.it','a:1'),product.slug);
 const old=await worker.fetch(new Request('https://offerte4zampe.it/prodotto.html?id=a%3A1'),e);assert.equal(old.status,301);assert.equal(old.headers.get('Location'),'https://offerte4zampe.it/prodotto/'+product.slug);
 const missing=await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/missing-product'),e,now);assert.equal(missing.status,404);
});
test('hostile titles are escaped in HTML and JSON-LD',async()=>{
 const p={...product,name:'</script><img onerror="bad">'};const r=await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+p.slug),env(p),now);const html=await r.text();assert(!html.includes('<img onerror="bad">'));assert(html.includes('\\u003c/script>'));
});

test('historical mean uses only real observed counts; missing days are not invented',()=>{
 const rows=[{day:'2026-10-27',low:10,high:20,sum:30,count:2},{day:'2026-10-25',low:30,high:30,sum:30,count:1}];
 const s=historySummary(rows,30,now);assert.equal(s.rows.length,2);assert.equal(s.low,10);assert.equal(s.high,30);assert.equal(s.mean,20);
});

test('merged brand-line legacy slugs redirect only to validated canonical paths',async()=>{
 const p={...product,redirect_slug:'new-product-4006381333931'};
 const r=await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+p.slug),env(p),now);
 assert.equal(r.status,301);assert.equal(r.headers.get('Location'),'https://offerte4zampe.it/prodotto/'+p.redirect_slug);
 const hostile={...product,redirect_slug:'https://evil.test/'};
 assert.equal((await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+hostile.slug),env(hostile),now)).status,200);
});

test('name based matches are disclosed and carry no invented confidence percentage',()=>{
 const p={...product,matching_method:'name_characteristics',gtin:'',indexable:false};const c=content(p,view(p,rules,now));assert(c.body.includes('Abbinamento per nome e caratteristiche'));assert(!c.schema.gtin13);assert(!c.body.includes('99%'));
});

test('rendered observations are absolute and HTML must revalidate',async()=>{const r=await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+product.slug),env(),now);const html=await r.text();assert(html.includes('<time datetime="2026-10-28T11:00:00Z">'));assert(!/\d+ ore? fa/.test(html));assert.equal(r.headers.get('Cache-Control'),'no-store');assert.equal(r.headers.get('Cloudflare-CDN-Cache-Control'),'no-store');});

test('indexable product uses verified local image in Open Graph metadata',async()=>{
 const p={...product,image_local:'/img/p/0123456789abcdef01234567-400.webp'};
 const socialTemplate=template.replace('</head>','<meta property="og:type" content="website"><meta property="og:image" content="https://offerte4zampe.it/assets/social-home.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:type" content="image/png"><meta property="og:image:alt" content="Generic"><meta name="twitter:image" content="https://offerte4zampe.it/assets/social-home.png"></head>');
 const e=env(p),original=e.ASSETS.fetch;
 e.ASSETS.fetch=async request=>{const path=new URL(request.url).pathname;if(path==='/prodotto')return new Response(socialTemplate,{headers:{'Content-Type':'text/html'}});if(path===p.image_local)return new Response(null,{status:200});return original(request)};
 const html=await (await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+p.slug),e,now)).text();
 assert.match(html,/property="og:type" content="product"/);
 assert.match(html,/property="og:image" content="https:\/\/offerte4zampe.it\/img\/p\/0123456789abcdef01234567-400.webp"/);
 assert.match(html,/property="og:image:type" content="image\/webp"/);
 assert.match(html,/property="og:image:alt" content="Brand Adult 2 kg"/);
 assert.match(html,/name="twitter:image" content="https:\/\/offerte4zampe.it\/img\/p\/0123456789abcdef01234567-400.webp"/);
 const single={...p,offers:[a]};const noindex=await (await canonicalProduct(new Request('https://offerte4zampe.it/prodotto/'+p.slug),env(single),now)).text();
 assert(!noindex.includes('property="og:type" content="product"'));
});

test('preview recalculation remains on its origin while canonical metadata points to production',async()=>{
 const origin='https://preview.example.workers.dev',path='/prodotto/'+product.slug;
 const metaTemplate=template.replace('</head>','<meta property="og:url" content="old"></head>');
 const e=env(),fetch=e.ASSETS.fetch;
 e.ASSETS.fetch=async request=>new URL(request.url).pathname==='/prodotto'?new Response(metaTemplate):fetch(request);
 const request=new Request(origin+path),html=await(await canonicalProduct(request,e,now)).text();
 const form=html.match(/<form\b[^>]*class="panel canonical-controls"[^>]*>/)?.[0];
 assert(form);assert.match(form,/method="get"/);
 const action=form.match(/action="([^"]+)"/)?.[1];assert.equal(action,path);
 const submission=new URL(action,request.url);submission.search=new URLSearchParams({quantity:'2',territory:'special'});
 assert.equal(submission.origin,origin);assert.equal(submission.pathname,path);
 const response=await canonicalProduct(new Request(submission),e,now),recalculated=await response.text();
 assert.equal(response.status,200);assert.match(recalculated,/<option value="2" selected>/);
 assert.match(recalculated,/<option value="special" selected>/);
 const production='https://offerte4zampe.it'+path;
 assert(html.includes('<link rel="canonical" href="'+production+'">'));
 assert(html.includes('<meta property="og:url" content="'+production+'">'));
});
