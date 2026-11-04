import test from 'node:test';import assert from 'node:assert/strict';import{createRequire}from'node:module';import fs from'node:fs/promises';import{gunzipSync}from'node:zlib';
const require=createRequire(import.meta.url),meta=require('../site/assets/product-metadata.js');
test('duplicate adjacent quantities disappear without conflating different formats',()=>{assert.equal(meta.name('Cibo 15 kg · 15kg'),'Cibo 15 kg');assert.equal(meta.name('Cibo 2 kg / 4 kg'),'Cibo 2 kg / 4 kg')});
test('fifty real product titles preserve complete normalized source identity',async()=>{
 const model=JSON.parse(gunzipSync(await fs.readFile(new URL('../site/data/product-catalog.json.gz',import.meta.url))));
 const products=model.products.filter(p=>p.active_offer_count).sort((a,b)=>b.name.length-a.name.length).slice(0,50);assert.equal(products.length,50);
 for(const p of products){const title=meta.title(p.name,p.brand,p.format);assert(title.includes(meta.name(p.name)),title);assert(title.endsWith(' | Prezzi e offerte'));if(!/^(?:Unità di vendita|Formato da verificare)$/i.test(p.format))assert(title.includes(meta.name(p.format)));}
});
test('description uses the lowest visible available offer and its unit price',()=>{
 const rows=[{available:true,price:29.89,unit_price:1.99,unit_price_unit:'kg'},{available:true,price:35},{available:false,price:1}];
 assert.match(meta.description(rows,3),/^Confronta 3 negozi: da 29,89/);assert.match(meta.description(rows,1),/^Prezzo rilevato: 29,89/);assert(!meta.description(rows,1).includes('1 negozio'));assert(meta.description(rows,3).includes('/kg'));
});

test('decimal comma and point are the same format in title and adjacent name',()=>{assert.equal(meta.name('Cibo 1.5Kg 1,5 kg'),'Cibo 1,5 kg');assert.equal(meta.title('Monge Adult Pollo 1.5Kg','Monge','1,5 kg'),'Monge Adult Pollo 1,5 kg | Prezzi e offerte');assert(meta.title('Cibo 2 kg / 4 kg','','4 kg').includes('2 kg / 4 kg'));});

test('title preserves taste, texture, size and excludes quantity placeholders',()=>{
 for(const name of ['Natural Trainer Flowpack Adult (4x85 g) Salmone','Royal Canin Cat Adult Sterilised in Salsa 85gr','Petup Pettorina doppia regolazione taglia 5-25 mm rosso'])assert(meta.title(name).includes(meta.name(name)));
 assert(meta.title('Natural Trainer Flowpack Adult (4x85 g) Salmone','Natural Trainer','340 g').length>65);
 for(const format of ['Unità di vendita','Formato da verificare'])assert.equal(meta.title('Trixie Gioco','Trixie',format),'Trixie Gioco | Prezzi e offerte');
 assert.equal((meta.title('Royal Canin Sterilised in Salsa 85gr','Royal Canin','85 g').match(/85 g/g)||[]).length,1);
});
