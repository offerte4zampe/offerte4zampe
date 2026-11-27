import test from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';const require=createRequire(import.meta.url),{normalize,orderShipping,scenarios,add}=require('../site/assets/basket.js');
const now=Date.parse('2026-10-20T12:00:00Z'),rules={checked_at:'2026-10-20',merchants:{a:{fee:6.9,free_above:59,boundary_unknown:59,max_shipping_weight_kg:35},b:{fee:5.9,free_from:39.9},c:{conflict:true}}},offer=(id,merchant_id='a',extra={})=>({id,merchant_id,merchant:merchant_id,price:30,available:true,title:id,brand:'Brand',weight_kg:2,shipping_weight_kg:12,checked_at:'2026-10-20T10:00:00Z',...extra});
test('order threshold and shipping are applied once across different products',()=>{const lines=[{offer:offer('a'),quantity:1},{offer:offer('b'),quantity:1}];assert.equal(orderShipping(lines,rules,'standard',now).total,60);assert.equal(orderShipping([{offer:offer('a'),quantity:1}],rules,'standard',now).total,36.9);assert.equal(orderShipping(lines.map(x=>({...x,offer:{...x.offer,merchant_id:'b',price:20}})),rules,'standard',now).total,40)});
test('incomplete, mixed, stale, conflicting or overweight orders never get totals',()=>{const lines=[{offer:offer('a'),quantity:1},{offer:offer('b'),quantity:2}];assert.equal(orderShipping(lines,rules,'standard',now).total,undefined);for(const bad of [{merchant_id:'b'},{shipping_weight_kg:null},{available:false},{checked_at:'2020-01-01'},{price:NaN},{shipping_weight_checked_at:'2020-01-01'}])assert.equal(orderShipping([{offer:offer('a'),quantity:1},{offer:offer('b','a',bad),quantity:1}],rules,'standard',now).total,undefined);assert.equal(orderShipping([{offer:offer('a','c'),quantity:1}],rules,'standard',now).total,undefined);assert.equal(orderShipping([{offer:offer('a','a',{price:59}),quantity:1}],rules,'standard',now).total,undefined)});
test('compare complete identical-format baskets, never partial assortments or similar recipes',()=>{const offers=[offer('a1','a',{gtin:'4006381333931'}),offer('a2','a',{gtin:'9780201379624'}),offer('b1','b',{gtin:'04006381333931',price:20}),offer('b2','b',{gtin:'9780201379624',weight_kg:3,price:1})];const result=scenarios([{id:'a1',quantity:1},{id:'a2',quantity:1}],offers,rules,'standard',now);assert.equal(result.find(s=>s.id==='a').total,60);assert.equal(result.find(s=>s.id==='b').total,undefined);assert.equal(result.find(s=>s.id==='b').missing.length,1);assert.equal(result[0].id,'a')});
test('missing original ID and invalid saved data cannot produce a misleading total',()=>{assert.deepEqual(normalize([{id:'<script>',quantity:1},{id:'a',quantity:-1},{id:'a',quantity:2},{id:'a',quantity:3}]),[{id:'a',quantity:2}]);assert.equal(scenarios([{id:'removed',quantity:1}],[offer('other')],rules,'standard',now)[0].total,undefined)});
test('adding a product saves only ID and quantity, never prices or affiliate URLs',()=>{const o=offer('a');const result=add([],o,[o]);assert.deepEqual(result.items,[{id:'a',quantity:1}]);assert.deepEqual(add(result.items,o,[o]).items,[{id:'a',quantity:2}])});
test('order subtotal uses cents and exact inclusive free-shipping threshold',()=>{assert.equal(orderShipping([{offer:offer('a','b',{price:19.95}),quantity:2}],rules,'standard',now).total,39.9)});
test('shipping weight is not rounded down across the surcharge boundary',()=>{assert.equal(orderShipping([{offer:offer('a','a',{price:60,shipping_weight_kg:35.004}),quantity:1}],rules,'standard',now).total,undefined)});

test('unverified feed variants cannot enter a cart or yield a total from saved rows',()=>{
 const o=offer('uncertain','a',{quantity_verified:false});
 assert.deepEqual(add([],o,[o]).items,[]);
 assert.equal(orderShipping([{offer:o,quantity:1}],rules,'standard',now).total,undefined);
 assert.equal(scenarios([{id:o.id,quantity:1}],[o],rules,'standard',now)[0].total,undefined);
});

test('canonical unknown pack blocks add, saved-list resolution and virtual order totals',()=>{
 const o=offer('nested','a',{quantity:{verified:false}}),saved=[{id:o.id,quantity:1}];
 assert.equal(add([],o,[o]).items.length,0);
 assert.equal(orderShipping([{offer:o,quantity:1}],rules,'standard',now).total,undefined);
 assert.equal(scenarios(saved,[o],rules,'standard',now)[0].total,undefined);
 const contradictory={...o,quantity_verified:true};
 assert.equal(add([],contradictory,[contradictory]).items.length,0);
 assert.equal(orderShipping([{offer:contradictory,quantity:1}],rules,'standard',now).total,undefined);
});
