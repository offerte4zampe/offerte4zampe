
import test from 'node:test';
import assert from 'node:assert/strict';
import {approvedAmazonPrice, amazonPick, amazonText} from '../worker/telegram-amazon.mjs';

const now = Date.parse('2026-11-09T12:00:00Z');
const official = {source:'creators_api',currency:'EUR',amount_cents:1345,shipping_cents:0,observed_at:'2026-11-09T11:45:00Z'};
const env = {AMAZON_OFFICIAL_PRICE_FEED_ENABLED:'true'};
const entry = {asin:'B0002AR15U',title:'KONG Classic S',note:'Il classico gioco da mordere per cani di taglia adatta.',reviewed_at:'2026-11-07T12:00:00Z',editorial_reviewed:true,price:official};
const esc = s => String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');

test('official verified fresh price gets EUR, shipping and timestamp',()=>{
 const p=amazonPick(entry,now,env);
 assert.equal(p.price.amount_cents,1345);
 const msg=amazonText(p,'https://www.amazon.it/dp/B0002AR15U?tag=example-21',esc);
 assert.equal(msg.method,'sendMessage');
 assert.match(msg.body.text,/Prezzo Amazon: 13,45/);
 assert.match(msg.body.text,/Spedizione: 0,00/);
 assert.match(msg.body.text,/Rilevato:/);
 assert.match(msg.body.text,/Prezzo e disponibilità possono cambiare/);
 assert.match(msg.body.text,/#pubblicità/);
});

test('default disabled, stale, wrong source, missing amount and future price never display',()=>{
 assert.equal(amazonPick(entry,now,{}).price,null);
 const changes=[
  {source:'third_party'}, {source:'manual'}, {currency:'USD'},
  {amount_cents:0},{amount_cents:14.50},{observed_at:'2026-11-09T09:40:00Z'},
  {observed_at:'2026-11-09T12:30:00Z'}, {shipping_cents:-1}
 ];
 for(const change of changes){
  const p=amazonPick({...entry,price:{...official,...change}},now,env);
  assert.equal(p.price,null,JSON.stringify(change));
  const msg=amazonText(p,'https://www.amazon.it/dp/B0002AR15U?tag=example-21',esc);
  assert.doesNotMatch(msg.body.text,/Prezzo Amazon:/);
 }
});

test('foreign partner prices on the editorial entry are ignored',()=>{
 const p=amazonPick({...entry,partner_price_eur:99,price:{source:'bauzaar',amount_cents:9900,currency:'EUR',observed_at:official.observed_at}},now,env);
 assert.equal(p.price,null);
});
